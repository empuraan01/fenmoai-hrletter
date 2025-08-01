import pdfplumber
import PyPDF2
from typing import List, Dict, Any
from pathlib import Path
import logging
from dataclasses import dataclass

@dataclass
class DocumentMetadata:
    filename: str
    page_count: int
    file_size: int
    document_type: str

@dataclass
class ParsedDocument:
    content: str
    metadata: DocumentMetadata
    pages: List[str]

class PDFParser:
    """Enhanced PDF parser using pdfplumber for better text extraction"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_pdf(self, file_path: str) -> ParsedDocument:
        """
        Parse PDF and extract text with metadata, including enhanced table processing
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ParsedDocument with content and metadata
        """
        file_path = Path(file_path)
        
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = []
                full_content = ""
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    
                    tables = page.extract_tables()
                    enhanced_page_text = page_text if page_text else ""
                    
                    if tables:
                        for table_idx, table in enumerate(tables):
                            enhanced_page_text += f"\n\n=== TABLE {table_idx + 1} ON PAGE {page_num} ===\n"
                            enhanced_page_text += self._format_table_for_search(table)
                            enhanced_page_text += "\n=== END TABLE ===\n"
                    
                    if enhanced_page_text:
                        pages.append(enhanced_page_text.strip())
                        full_content += f"\n--- Page {page_num} ---\n{enhanced_page_text.strip()}\n"
                
                metadata = DocumentMetadata(
                    filename=file_path.name,
                    page_count=len(pdf.pages),
                    file_size=file_path.stat().st_size,
                    document_type=self._determine_document_type(file_path.name)
                )
                
                self.logger.info(f"Successfully parsed {file_path.name}: {len(pages)} pages")
                
                return ParsedDocument(
                    content=full_content.strip(),
                    metadata=metadata,
                    pages=pages
                )
                
        except Exception as e:
            self.logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise
    
    def _format_table_for_search(self, table) -> str:
        """Format table data to be more searchable"""
        if not table or len(table) < 2:
            return ""
        
        formatted_lines = []
        headers = table[0] if table[0] else []
        

        clean_headers = [self._clean_cell(cell) for cell in headers]
        formatted_lines.append("HEADERS: " + " | ".join(clean_headers))
        
        for row_idx, row in enumerate(table[1:], 1):
            if not row:
                continue
                
            clean_row = [self._clean_cell(cell) for cell in row]
            
            if len(clean_row) >= len(clean_headers):
                row_pairs = []
                for header, value in zip(clean_headers, clean_row):
                    if header and value:
                        row_pairs.append(f"{header}: {value}")
                
                formatted_lines.append(f"ROW {row_idx}: " + " | ".join(clean_row))
                formatted_lines.append(f"ROW {row_idx} DETAILS: " + " | ".join(row_pairs))
        
        return "\n".join(formatted_lines)
    
    def _clean_cell(self, cell) -> str:
        """Clean individual table cell content"""
        if not cell:
            return ""
        
        cleaned = str(cell).replace('\n', ' ').replace('\r', ' ')
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()
    
    def _determine_document_type(self, filename: str) -> str:
        """Determine document type based on filename"""
        filename_lower = filename.lower()
        
        if "leave" in filename_lower or "policy" in filename_lower:
            return "hr_policy"
        elif "travel" in filename_lower:
            return "travel_policy"  
        elif "offer" in filename_lower:
            return "offer_template"
        else:
            return "unknown"
    
    def parse_multiple_pdfs(self, file_paths: List[str]) -> List[ParsedDocument]:
        """Parse multiple PDF files"""
        documents = []
        
        for file_path in file_paths:
            try:
                doc = self.parse_pdf(file_path)
                documents.append(doc)
            except Exception as e:
                self.logger.error(f"Failed to parse {file_path}: {str(e)}")
                continue
                
        return documents