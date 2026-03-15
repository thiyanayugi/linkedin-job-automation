"""
Resume Parser Module

Extracts plain text from PDF resume files using PyPDF2 and pdfplumber,
with automatic fallback between engines for maximum compatibility.
"""

import os
from typing import Optional
import PyPDF2
import pdfplumber
from utils import setup_logger, retry_on_failure

logger = setup_logger(__name__)


class ResumeParser:
    """
    Parse and extract text from a PDF resume file.
    
    Supports two extraction backends (PyPDF2 and pdfplumber) and selects
    the most suitable one automatically via the 'auto' mode.
    """
    
    def __init__(self, resume_path: str):
        """
        Initialize the resume parser.
        
        Args:
            resume_path: Path to the PDF resume file
        """
        self.resume_path = resume_path
        self.resume_text = None
        
        if not os.path.exists(resume_path):
            raise FileNotFoundError(f"Resume file not found: {resume_path}")
        
        logger.info(f"Initialized ResumeParser with file: {resume_path}")
    
    @retry_on_failure(max_retries=2)
    def extract_text_pypdf2(self) -> str:
        """
        Extract text from the PDF using the PyPDF2 library.
        
        Opens the file in binary mode, iterates over all pages, and
        concatenates the extracted text. May produce less accurate results
        than pdfplumber for PDFs with complex layouts or embedded fonts.
        
        Returns:
            Concatenated plain text from all pages, stripped of leading/
            trailing whitespace.
            
        Raises:
            Exception: If PyPDF2 cannot read or decode the PDF.
        """
        try:
            text = ""
            with open(self.resume_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                logger.info(f"Extracting text from {num_pages} pages using PyPDF2")
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
            
            return text.strip()
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise
    
    @retry_on_failure(max_retries=2)
    def extract_text_pdfplumber(self) -> str:
        """
        Extract text from the PDF using the pdfplumber library.
        
        pdfplumber provides higher fidelity extraction than PyPDF2 for PDFs
        with tables, columns, and non-standard fonts. Appends a newline after
        each page's text to preserve paragraph boundaries.
        
        Returns:
            Concatenated plain text from all pages, stripped of leading/
            trailing whitespace.
            
        Raises:
            Exception: If pdfplumber cannot open or parse the PDF.
        """
        try:
            text = ""
            with pdfplumber.open(self.resume_path) as pdf:
                num_pages = len(pdf.pages)
                
                logger.info(f"Extracting text from {num_pages} pages using pdfplumber")
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {str(e)}")
            raise
    
    def extract_text(self, method: str = "auto") -> str:
        """
        Extract text from PDF using specified method with automatic fallback.
        
        The 'auto' method attempts pdfplumber first (more accurate for complex PDFs
        with tables and formatting), then falls back to PyPDF2 if pdfplumber fails
        or produces insufficient text.
        
        Args:
            method: Extraction method - 'pypdf2', 'pdfplumber', or 'auto' (recommended)
        
        Returns:
            Extracted text from PDF
            
        Raises:
            Exception: If all extraction methods fail
        """
        if method == "auto":
            # Try pdfplumber first (more accurate), fallback to PyPDF2
            try:
                logger.info("Attempting text extraction with pdfplumber")
                text = self.extract_text_pdfplumber()
                if text and len(text) > 100:  # Sanity check
                    self.resume_text = text
                    logger.info(f"Successfully extracted {len(text)} characters")
                    return text
            except Exception as e:
                logger.warning(f"pdfplumber failed, trying PyPDF2: {str(e)}")
            
            # Fallback to PyPDF2
            try:
                logger.info("Attempting text extraction with PyPDF2")
                text = self.extract_text_pypdf2()
                self.resume_text = text
                logger.info(f"Successfully extracted {len(text)} characters")
                return text
            except Exception as e:
                logger.error(f"All extraction methods failed: {str(e)}")
                raise
        
        elif method == "pypdf2":
            text = self.extract_text_pypdf2()
            self.resume_text = text
            return text
        
        elif method == "pdfplumber":
            text = self.extract_text_pdfplumber()
            self.resume_text = text
            return text
        
        else:
            raise ValueError(f"Invalid extraction method: {method}")
    
    def get_resume_text(self) -> Optional[str]:
        """
        Return cached resume text, extracting it first if necessary.
        
        Calls extract_text() with the default 'auto' method on the first
        invocation and caches the result in self.resume_text for subsequent
        calls.
        
        Returns:
            Extracted resume text string, or None if extraction failed.
        """
        if self.resume_text is None:
            self.extract_text()
        return self.resume_text
    
    def get_resume_summary(self, max_chars: int = 200) -> str:
        """
        Return a short preview of the extracted resume text.
        
        Useful for logging or quick sanity-checks without printing the
        entire resume. Appends '...' when the text is truncated.
        
        Args:
            max_chars: Maximum number of characters to include in the preview.
        
        Returns:
            Truncated resume text string (empty string if no text available).
        """
        text = self.get_resume_text()
        if not text:
            return ""
        
        summary = text[:max_chars]
        if len(text) > max_chars:
            summary += "..."
        
        return summary


def main():
    """Test the resume parser."""
    import sys
    from dotenv import load_dotenv
    
    load_dotenv()
    
    resume_path = os.getenv("RESUME_PATH", "data/resume.pdf")
    
    if not os.path.exists(resume_path):
        print(f"❌ Resume file not found: {resume_path}")
        print("Please add your resume PDF to the data/ folder")
        sys.exit(1)
    
    try:
        parser = ResumeParser(resume_path)
        text = parser.extract_text()
        
        print("\n" + "="*80)
        print("RESUME EXTRACTION TEST")
        print("="*80)
        print(f"\n📄 File: {resume_path}")
        print(f"📊 Extracted {len(text)} characters")
        print(f"\n📝 First 500 characters:\n")
        print(text[:500])
        print("\n" + "="*80)
        print("✅ Resume extraction successful!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
