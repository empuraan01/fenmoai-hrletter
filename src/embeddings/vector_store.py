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
    
    def band_specific_search(self, query: str, band: str, n_results: int = 10, 
                           document_types: List[str] = None, min_similarity: float = 0.0) -> List[Dict[str, Any]]:
        """Enhanced search that prioritizes content specific to a particular band"""
        try:
            
            initial_results = self.similarity_search(
                query=query,
                n_results=n_results * 2,  
                document_types=document_types,
                min_similarity=min_similarity
            )
            
            band_specific = []
            general_content = []
            
            for result in initial_results:
                content = result['content'].upper()
                
                if band.upper() in content:
                    band_context_score = self._calculate_band_context_score(result['content'], band)
                    result['band_context_score'] = band_context_score
                    
                    if band_context_score > 0.3:  
                        result['similarity'] += 0.4
                        result['band_specific'] = True
                        result['priority'] = 'high'
                        band_specific.append(result)
                    else:
                        result['similarity'] += 0.2
                        result['band_specific'] = True  
                        result['priority'] = 'medium'
                        band_specific.append(result)
                else:
                    result['band_specific'] = False
                    result['priority'] = 'low'
                    general_content.append(result)
            
            final_results = band_specific + general_content
            
            final_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return final_results[:n_results]
            
        except Exception as e:
            self.logger.error(f"Error performing band-specific search: {str(e)}")
            return self.similarity_search(query, n_results, document_types, min_similarity)
    
    def _calculate_band_context_score(self, content: str, band: str) -> float:
        """Calculate how contextually relevant content is to a specific band"""
        content_lower = content.lower()
        band_lower = band.lower()
        score = 0.0
        
        band_patterns = [
            f"{band_lower} employees",
            f"{band_lower} band",
            f"for {band_lower}",
            f"{band_lower} level",
            f"{band_lower} staff",
            f"{band_lower}:",
            f"level {band_lower}",
            f"band {band_lower}"
        ]
        
        for pattern in band_patterns:
            if pattern in content_lower:
                score += 0.3
        
        table_patterns = [
            "matrix", "table", "entitlement", "policy summary"
        ]
        
        for pattern in table_patterns:
            if pattern in content_lower and band_lower in content_lower:
                score += 0.1
        
        other_bands = [f"l{i}" for i in range(1, 6) if f"l{i}" != band_lower]
        other_band_mentions = sum(1 for band_ref in other_bands if band_ref in content_lower)
        
        if other_band_mentions > 2:
            score *= 0.5  
        
        return min(score, 1.0)  
    
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
            
            # Enhanced queries using the improved band-specific search
            policy_queries = {
                'leave_policy': f"leave entitlement {salary_band} earned leave sick leave casual leave matrix",
                'travel_policy': f"travel allowance per diem {salary_band} flight hotel reimbursement matrix", 
                'work_arrangements': f"work from home WFH WFO {salary_band} remote work flexible eligibility",
                'infrastructure_support': f"WFH setup grant internet stipend laptop device policy {salary_band}"
            }
            
            relevant_policies = {}
            
            for policy_type, query in policy_queries.items():
                
                # Use the enhanced band-specific search for better results
                results = self.band_specific_search(
                    query=query,
                    band=salary_band,
                    n_results=4,  # Get more results for offer letters
                    document_types=['hr_policy', 'travel_policy'],
                    min_similarity=0.05
                )
                
                if results:
                    relevant_policies[policy_type] = results
                    self.logger.info(f"Found {len(results)} relevant {policy_type} documents for {salary_band}")
            
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