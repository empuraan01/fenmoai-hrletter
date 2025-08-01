from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from src.document_processor import PDFParser, IntelligentTextChunker
from src.embeddings import EmbeddingManager, VectorStore
from src.data import EmployeeManager
from .gemini_client import GeminiClient
from config import settings

class RAGEngine:
    
    def __init__(self, 
                 vector_store: VectorStore = None,
                 employee_manager: EmployeeManager = None,
                 gemini_client: GeminiClient = None):
        self.logger = logging.getLogger(__name__)
        
        self.pdf_parser = PDFParser()
        self.text_chunker = IntelligentTextChunker()
        self.vector_store = vector_store or VectorStore()
        self.employee_manager = employee_manager or EmployeeManager(vector_store=self.vector_store)
        self.gemini_client = gemini_client or GeminiClient()
        
        self.logger.info("RAG Engine initialized successfully")
    
    def process_and_store_documents(self, document_paths: List[str] = None) -> Dict[str, Any]:
        
        if document_paths is None:
            assets_path = Path(settings.assets_path)
            document_paths = [
                str(assets_path / "HR Leave Policy.pdf"),
                str(assets_path / "HR Travel Policy.pdf"),
                str(assets_path / "HR Offer Letter.pdf")
            ]
        
        processing_summary = {
            'processed_documents': [],
            'total_chunks': 0,
            'errors': []
        }
        
        try:
            all_chunks = []
            
            for doc_path in document_paths:
                doc_path = Path(doc_path)
                if not doc_path.exists():
                    error_msg = f"Document not found: {doc_path}"
                    self.logger.error(error_msg)
                    processing_summary['errors'].append(error_msg)
                    continue
                
                try:
                    self.logger.info(f"Processing document: {doc_path.name}")
                    
                    parsed_doc = self.pdf_parser.parse_pdf(str(doc_path))
                    
                    chunks = self.text_chunker.chunk_document(parsed_doc)
                    
                    all_chunks.extend(chunks)
                    
                    processing_summary['processed_documents'].append({
                        'filename': doc_path.name,
                        'chunks_count': len(chunks),
                        'document_type': parsed_doc.metadata.document_type,
                        'pages': parsed_doc.metadata.page_count
                    })
                    
                    self.logger.info(f"Generated {len(chunks)} chunks from {doc_path.name}")
                    
                except Exception as e:
                    error_msg = f"Error processing {doc_path.name}: {str(e)}"
                    self.logger.error(error_msg)
                    processing_summary['errors'].append(error_msg)
                    continue
            
            if all_chunks:
                chunks_added = self.vector_store.add_chunks(all_chunks)
                processing_summary['total_chunks'] = chunks_added
                self.logger.info(f"Successfully stored {chunks_added} chunks in vector database")
            else:
                self.logger.warning("No chunks to store in vector database")
            
            return processing_summary
            
        except Exception as e:
            self.logger.error(f"Error in document processing pipeline: {str(e)}")
            processing_summary['errors'].append(str(e))
            return processing_summary
    
    def generate_offer_letter(self, employee_name: str) -> Dict[str, Any]:
        
        try:
            self.logger.info(f"Generating offer letter for: {employee_name}")
            
            employee_context = self.employee_manager.get_employee_context(employee_name)
            self.logger.info(f"Retrieved employee context for {employee_name}")
            
            relevant_policies = self.vector_store.get_relevant_policies(employee_context)
            
            policy_context = self._build_policy_context(relevant_policies)
            
            template_context = self._get_template_context()
            

            self.logger.info(f"About to call Gemini API for {employee_name} - policies: {len(relevant_policies)}, template: {bool(template_context)}")
            
            try:
                offer_letter_content = self.gemini_client.generate_offer_letter(
                    employee_context=employee_context,
                    policy_context=policy_context,
                    template_context=template_context
                )
                self.logger.info(f"Gemini API call completed for {employee_name}")
                
            except Exception as gemini_error:
                self.logger.error(f"Gemini API call failed for {employee_name}: {str(gemini_error)}")
                raise gemini_error
            
            result = {
                'employee_name': employee_name,
                'offer_letter': offer_letter_content,
                'employee_context': employee_context,
                'relevant_policies': relevant_policies,
                'generation_metadata': {
                    'policies_used': len(relevant_policies),
                    'total_policy_chunks': sum(len(policies) for policies in relevant_policies.values()),
                    'template_used': bool(template_context)
                }
            }
            
            self.logger.info(f"Successfully generated offer letter for {employee_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating offer letter for {employee_name}: {str(e)}")
            raise
    
    def _build_policy_context(self, relevant_policies: Dict[str, List[Dict]]) -> str:
        
        if not relevant_policies:
            return "No specific policies found."
        
        context_parts = []
        
        for policy_type, policies in relevant_policies.items():
            if policies:
                context_parts.append(f"\n**{policy_type.upper().replace('_', ' ')}:**")
                
                for i, policy in enumerate(policies, 1):
                    similarity_score = policy.get('similarity', 0.0)
                    context_parts.append(
                        f"\n{i}. (Relevance: {similarity_score:.2f})\n{policy['content'][:500]}..."
                    )
        
        return "\n".join(context_parts)
    
    def _get_template_context(self) -> str:
        
        try:
            template_results = self.vector_store.similarity_search(
                query="offer letter employment agreement position salary compensation",
                n_results=2,
                document_types=['offer_template'],
                    min_similarity=0.0
            )
            
            if template_results:
                template_content = []
                for result in template_results:
                    template_content.append(result['content'])
                
                return "\n\n".join(template_content)
            else:
                self.logger.warning("No template found, using default structure")
                return self._get_default_template_structure()
                
        except Exception as e:
            self.logger.warning(f"Could not retrieve template context: {str(e)}")
            return self._get_default_template_structure()
    
    def _get_default_template_structure(self) -> str:
        
        return """
        STANDARD OFFER LETTER STRUCTURE:
        
        1. Company Header and Date
        2. Employee Address
        3. Subject Line
        4. Formal Greeting
        5. Position Details:
           - Job Title
           - Department
           - Reporting Manager
           - Start Date
        6. Compensation Package:
           - Base Salary
           - Allowances
        7. Terms and Conditions
        8. HR Policies Reference
        9. Acceptance Instructions
        10. Closing and Signature Block
        """
    
    def search_policies(self, query: str, document_types: List[str] = None) -> List[Dict[str, Any]]:
        
        try:
            search_queries = [query]
            
            import re
            query_lower = query.lower()
            
            band_match = re.search(r'L[1-5]', query.upper())
            specific_band = band_match.group() if band_match else None
            
            is_senior_query = any(term in query_lower for term in ['senior', 'executive', 'lead'])
            
            if 'leave' in query_lower:
                search_queries.extend([
                    "leave entitlement matrix band earned sick casual",
                    "leave policy days allocation band-wise",
                    "WFH eligibility days per week bands"
                ])
                if specific_band:
                    search_queries.append(f"{specific_band} leave days entitlement")
                if is_senior_query:
                    search_queries.extend(["L3 L4 L5 leave policy", "senior leave entitlement"])
            
            if 'travel' in query_lower:
                search_queries.extend([
                    "travel allowance per diem hotel flight band matrix",
                    "travel policy domestic international bands",
                    "travel approval required manager VP bands"
                ])
                if specific_band:
                    search_queries.append(f"{specific_band} travel allowance per diem")
                if is_senior_query:
                    search_queries.extend(["L3 L4 L5 travel policy", "senior travel allowance"])
            
            if specific_band:
                search_queries.extend([
                    f"{specific_band} policy entitlements",
                    f"band {specific_band} matrix table"
                ])
            elif is_senior_query:
                search_queries.extend([
                    "L3 L4 L5 policy matrix",
                    "senior staff policies entitlements"
                ])
            
            all_results = []
            seen_content = set()
            
            for search_query in search_queries:
                results = self.vector_store.similarity_search(
                    query=search_query,
                    n_results=5,
                    document_types=document_types,
                    min_similarity=0.05
                )
                
                for result in results:
                    content_key = result['content'][:100]
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        all_results.append(result)
            
            all_results.sort(key=lambda x: x['similarity'], reverse=True)
            final_results = all_results[:10]
            
            self.logger.info(f"Enhanced search found {len(final_results)} results for query: '{query}' using {len(search_queries)} search strategies")
            return final_results
            
        except Exception as e:
            self.logger.error(f"Error searching policies: {str(e)}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        
        try:
            vector_stats = self.vector_store.get_collection_stats()
            
            employee_count = len(self.employee_manager.list_all_employees())
            
            gemini_status = self.gemini_client.test_connection()
            
            embedding_info = self.vector_store.embedding_manager.get_model_info()
            
            status = {
                'vector_store': vector_stats,
                'employee_count': employee_count,
                'gemini_connected': gemini_status,
                'embedding_model': embedding_info,
                'system_ready': all([
                    vector_stats.get('total_documents', 0) > 0,
                    employee_count > 0,
                    gemini_status
                ])
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {str(e)}")
            return {'error': str(e)}
    
    def reset_vector_store(self):
        
        try:
            self.vector_store.clear_collection()
            self.logger.info("Vector store reset successfully")
        except Exception as e:
            self.logger.error(f"Error resetting vector store: {str(e)}")
            raise
    
    def batch_generate_offers(self, employee_names: List[str]) -> Dict[str, Any]:
        
        results = {
            'successful': {},
            'failed': {},
            'summary': {
                'total': len(employee_names),
                'successful': 0,
                'failed': 0
            }
        }
        
        for employee_name in employee_names:
            try:
                offer_result = self.generate_offer_letter(employee_name)
                results['successful'][employee_name] = offer_result
                results['summary']['successful'] += 1
                
            except Exception as e:
                results['failed'][employee_name] = str(e)
                results['summary']['failed'] += 1
                self.logger.error(f"Failed to generate offer for {employee_name}: {str(e)}")
        
        return results 