from typing import List, Dict, Any
from dataclasses import dataclass
import re
from config import settings

@dataclass
class TextChunk:
    content: str
    chunk_id: str
    source_document: str
    document_type: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any]

class IntelligentTextChunker:
    """
    Advanced text chunking with semantic awareness
    """
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.overlap = overlap or settings.chunk_overlap
        
    def chunk_document(self, parsed_doc) -> List[TextChunk]:
        """
        Create intelligent chunks from parsed document
        
        Args:
            parsed_doc: ParsedDocument object
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
            
        if parsed_doc.metadata.document_type == "hr_policy":
            chunks = self._semantic_chunk_policy(parsed_doc)
        else:
            chunks = self._sliding_window_chunk(parsed_doc)
            
        return chunks
    
    def _semantic_chunk_policy(self, parsed_doc) -> List[TextChunk]:
        """
        Semantic chunking for HR policy documents
        Looks for sections, headings, and logical breaks
        """
        chunks = []
        content = parsed_doc.content
        
        section_patterns = [
            r'\n\d+\.\s+[A-Z][^.\n]*\n',  # "1. SECTION TITLE"  
            r'\n[A-Z][A-Z\s]{3,}:\n',      # "SECTION TITLE:"
            r'\n[A-Z][A-Z\s]{3,}\n\n',     # "SECTION TITLE" (standalone)
        ]
        
        sections = self._split_by_patterns(content, section_patterns)
        
        for i, section in enumerate(sections):
            if len(section.strip()) < 50:
                continue
                
            is_table_section = ("=== TABLE" in section and "ROW 1 DETAILS" in section)
            
            if len(section) > self.chunk_size and not is_table_section:
                sub_chunks = self._sliding_window_chunk_text(section)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append(TextChunk(
                        content=sub_chunk,
                        chunk_id=f"{parsed_doc.metadata.filename}_semantic_{i}_{j}",
                        source_document=parsed_doc.metadata.filename,
                        document_type=parsed_doc.metadata.document_type,
                        page_number=0,
                        chunk_index=len(chunks),
                        metadata={"chunking_method": "semantic", "section": i}
                    ))
            else:
                chunks.append(TextChunk(
                    content=section.strip(),
                    chunk_id=f"{parsed_doc.metadata.filename}_semantic_{i}",
                    source_document=parsed_doc.metadata.filename,
                    document_type=parsed_doc.metadata.document_type,
                    page_number=0,
                    chunk_index=len(chunks),
                    metadata={"chunking_method": "semantic", "section": i, "is_table": is_table_section}
                ))
                
        return chunks if chunks else self._sliding_window_chunk(parsed_doc)
    
    def _sliding_window_chunk(self, parsed_doc) -> List[TextChunk]:
        """
        Traditional sliding window chunking with overlap
        """
        chunks = []
        content = parsed_doc.content
        
        text_chunks = self._sliding_window_chunk_text(content)
        
        for i, chunk_text in enumerate(text_chunks):
            chunks.append(TextChunk(
                content=chunk_text,
                chunk_id=f"{parsed_doc.metadata.filename}_window_{i}",
                source_document=parsed_doc.metadata.filename,
                document_type=parsed_doc.metadata.document_type,
                page_number=0,
                chunk_index=i,
                metadata={"chunking_method": "sliding_window"}
            ))
            
        return chunks
    
    def _sliding_window_chunk_text(self, text: str) -> List[str]:
        """Split text using sliding window approach"""
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            return [text]
            
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            chunks.append(chunk_text)
            
            if i + self.chunk_size >= len(words):
                break
                
        return chunks
    
    def _split_by_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Split text by regex patterns"""
        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                sections = []
                last_end = 0
                
                for match in matches:
                    if match.start() > last_end:
                        sections.append(text[last_end:match.start()])
                    sections.append(text[match.start():match.end()])
                    last_end = match.end()
                    
                if last_end < len(text):
                    sections.append(text[last_end:])
                    
                return [s for s in sections if s.strip()]
                
        return [text]