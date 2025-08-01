import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
import uuid
from dataclasses import asdict
from src.document_processor import TextChunk
from .embedding_manager import EmbeddingManager
from config import settings

class VectorStore:
    
    
    def __init__(self, collection_name: str = "fenmoai_documents", persist_directory: str = None):
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory or settings.vector_db_path)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.collection = None
        self.embedding_manager = EmbeddingManager()
        
        self._setup_chromadb()
    
    def _setup_chromadb(self):
        
        try:
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "FenmoAI HR documents and policies"}
            )
            
            self.logger.info(f"ChromaDB initialized: {self.collection_name}")
            self.logger.info(f"Collection has {self.collection.count()} documents")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise
    
    def add_chunks(self, chunks: List[TextChunk], batch_size: int = 100) -> int:
        
        if not chunks:
            self.logger.warning("No chunks to add")
            return 0
        
        try:
            added_count = 0
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                
                texts = [chunk.content for chunk in batch_chunks]
                chunk_ids = [chunk.chunk_id or f"chunk_{uuid.uuid4()}" for chunk in batch_chunks]
                
                metadatas = []
                for chunk in batch_chunks:
                    metadata = {
                        "source_document": chunk.source_document,
                        "document_type": chunk.document_type,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "chunking_method": chunk.metadata.get("chunking_method", "unknown")
                    }
                    metadata.update(chunk.metadata)
                    metadatas.append(metadata)
                
                self.logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_chunks)} chunks")
                embeddings = self.embedding_manager.generate_embeddings(texts)
                
                if embeddings.size == 0:
                    self.logger.warning(f"No embeddings generated for batch {i//batch_size + 1}")
                    continue
                
                self.collection.add(
                    documents=texts,
                    embeddings=embeddings.tolist(),
                    metadatas=metadatas,
                    ids=chunk_ids
                )
                
                added_count += len(batch_chunks)
                self.logger.info(f"Added {len(batch_chunks)} chunks to vector store")
            
            self.logger.info(f"Successfully added {added_count} chunks to vector store")
            return added_count
            
        except Exception as e:
            self.logger.error(f"Error adding chunks to vector store: {str(e)}")
            raise
    
    def similarity_search(self, 
                         query: str, 
                         n_results: int = 5,
                         document_types: List[str] = None,
                         min_similarity: float = 0.0) -> List[Dict[str, Any]]:

        try:
            
            query_embedding = self.embedding_manager.generate_query_embedding(query)
            
            
            where_conditions = {}
            if document_types:
                where_conditions["document_type"] = {"$in": document_types}
            
            
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where_conditions if where_conditions else None
            )
            
            
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    
                    # ChromaDB returns squared euclidean distance, convert to similarity
                    # For normalized embeddings, cosine similarity = 1 - (euclidean_distance^2 / 2)
                    # But for simplicity, we'll use inverse distance as similarity
                    similarity = 1 / (1 + distance) if distance >= 0 else 0.0
                    
                    if similarity >= min_similarity:
                        result = {
                            'content': doc,
                            'metadata': metadata,
                            'similarity': similarity,
                            'rank': i + 1
                        }
                        search_results.append(result)
            
            self.logger.info(f"Found {len(search_results)} relevant documents for query")
            return search_results
            
        except Exception as e:
            self.logger.error(f"Error performing similarity search: {str(e)}")
            raise
    
    def get_documents_by_type(self, document_type: str, limit: int = None) -> List[Dict[str, Any]]:
        
        try:
            results = self.collection.get(
                where={"document_type": document_type},
                limit=limit
            )
            
            documents = []
            if results['documents']:
                for doc, metadata in zip(results['documents'], results['metadatas']):
                    documents.append({
                        'content': doc,
                        'metadata': metadata
                    })
            
            self.logger.info(f"Retrieved {len(documents)} documents of type '{document_type}'")
            return documents
            
        except Exception as e:
            self.logger.error(f"Error retrieving documents by type: {str(e)}")
            raise
    
    def get_relevant_policies(self, employee_context: Dict) -> Dict[str, List[Dict]]:
        
        try:
            employee = employee_context['employee']
            salary_band = employee.get('salary_band', 'L1')
            position = employee.get('position', '').lower()
            
            # Updated queries to match actual document content
            policy_queries = {
                'leave_policy': f"leave entitlement {salary_band} earned leave sick leave casual leave",
                'travel_policy': f"travel allowance per diem {salary_band} flight hotel reimbursement", 
                'work_arrangements': f"work from home WFH WFO {salary_band} remote work flexible",
                'infrastructure_support': f"WFH setup grant internet stipend laptop device policy"
            }
            
            relevant_policies = {}
            
            for policy_type, query in policy_queries.items():
                
                results = self.similarity_search(
                    query=query,
                    n_results=3,
                    document_types=['hr_policy', 'travel_policy'],
                    min_similarity=0.05
                )
                
                if results:
                    relevant_policies[policy_type] = results
                    self.logger.info(f"Found {len(results)} relevant {policy_type} documents")
            
            return relevant_policies
            
        except Exception as e:
            self.logger.error(f"Error retrieving relevant policies: {str(e)}")
            return {}
    
    def clear_collection(self):
        
        try:
            
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "FenmoAI HR documents and policies"}
            )
            self.logger.info("Collection cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing collection: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        
        try:
            count = self.collection.count()
            
            all_docs = self.collection.get()
            doc_types = {}
            if all_docs['metadatas']:
                for metadata in all_docs['metadatas']:
                    doc_type = metadata.get('document_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            stats = {
                'total_documents': count,
                'document_types': doc_types,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory)
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {str(e)}")
            return {}
    
    def delete_by_source(self, source_document: str):
        
        try:
            results = self.collection.get(
                where={"source_document": source_document}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                self.logger.info(f"Deleted {len(results['ids'])} chunks from {source_document}")
            else:
                self.logger.info(f"No documents found for source: {source_document}")
                
        except Exception as e:
            self.logger.error(f"Error deleting documents from source: {str(e)}")
            raise 