"""Apache Tika service for document processing and extraction."""

import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

import sys
sys.path.append('..')
from config import settings


class TikaService:
    """Tika service for document processing, OCR, and metadata extraction."""
    
    # Supported content types
    SUPPORTED_TYPES = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt": "text/plain",
        "html": "text/html",
        "xml": "application/xml",
        "json": "application/json",
        "csv": "text/csv",
        "rtf": "application/rtf",
        "odt": "application/vnd.oasis.opendocument.text",
        "ods": "application/vnd.oasis.opendocument.spreadsheet",
        "png": "image/png",
        "jpg": "image/jpeg",
        "gif": "image/gif",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "wav": "audio/wav",
        "zip": "application/zip",
        "tar": "application/x-tar",
        "gz": "application/gzip"
    }
    
    def __init__(self):
        self.server_url = settings.TIKA_SERVER
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self):
        """Initialize HTTP session and test connection."""
        self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.get(f"{self.server_url}/tika") as resp:
                if resp.status == 200:
                    print(f"Tika connected: {self.server_url}")
                else:
                    print(f"Tika connection warning: status {resp.status}")
        except Exception as e:
            print(f"Tika connection error: {e}")
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            print("Tika disconnected")
    
    # ==================== TEXT EXTRACTION ====================
    
    async def extract_text(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """Extract plain text from a document."""
        headers = {
            "Accept": "text/plain"
        }
        if content_type:
            headers["Content-Type"] = content_type
        
        async with self.session.put(
            f"{self.server_url}/tika",
            data=content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Text extraction failed: {resp.status}")
            return await resp.text()
    
    async def extract_text_from_file(
        self,
        file_path: str
    ) -> str:
        """Extract text from a local file."""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Detect content type from extension
        ext = file_path.split('.')[-1].lower()
        content_type = self.SUPPORTED_TYPES.get(ext)
        
        return await self.extract_text(content, content_type)
    
    # ==================== METADATA EXTRACTION ====================
    
    async def extract_metadata(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract metadata from a document."""
        headers = {
            "Accept": "application/json"
        }
        if content_type:
            headers["Content-Type"] = content_type
        
        async with self.session.put(
            f"{self.server_url}/meta",
            data=content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Metadata extraction failed: {resp.status}")
            return await resp.json()
    
    async def extract_metadata_from_file(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """Extract metadata from a local file."""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        ext = file_path.split('.')[-1].lower()
        content_type = self.SUPPORTED_TYPES.get(ext)
        
        return await self.extract_metadata(content, content_type)
    
    # ==================== FULL EXTRACTION ====================
    
    async def extract_all(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract both text and metadata from a document."""
        headers = {
            "Accept": "application/json"
        }
        if content_type:
            headers["Content-Type"] = content_type
        
        async with self.session.put(
            f"{self.server_url}/rmeta/text",
            data=content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Full extraction failed: {resp.status}")
            data = await resp.json()
            
            # Tika returns a list, get first item
            if isinstance(data, list) and len(data) > 0:
                result = data[0]
            else:
                result = data
            
            # Normalize the response
            return {
                "content": result.get("X-TIKA:content", ""),
                "content_type": result.get("Content-Type", ""),
                "metadata": {
                    k: v for k, v in result.items()
                    if not k.startswith("X-TIKA:")
                },
                "tika_metadata": {
                    k: v for k, v in result.items()
                    if k.startswith("X-TIKA:")
                }
            }
    
    async def extract_all_from_file(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """Extract all from a local file."""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        ext = file_path.split('.')[-1].lower()
        content_type = self.SUPPORTED_TYPES.get(ext)
        
        result = await self.extract_all(content, content_type)
        result["file_path"] = file_path
        result["file_extension"] = ext
        
        return result
    
    # ==================== OCR ====================
    
    async def ocr_image(
        self,
        image_content: bytes,
        content_type: str = "image/png"
    ) -> str:
        """Perform OCR on an image."""
        headers = {
            "Accept": "text/plain",
            "Content-Type": content_type,
            "X-Tika-OCRLanguage": "eng"
        }
        
        async with self.session.put(
            f"{self.server_url}/tika",
            data=image_content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"OCR failed: {resp.status}")
            return await resp.text()
    
    async def ocr_pdf(
        self,
        pdf_content: bytes
    ) -> str:
        """Perform OCR on a PDF (for scanned documents)."""
        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/pdf",
            "X-Tika-PDFOcrStrategy": "ocr_only"
        }
        
        async with self.session.put(
            f"{self.server_url}/tika",
            data=pdf_content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"PDF OCR failed: {resp.status}")
            return await resp.text()
    
    # ==================== LANGUAGE DETECTION ====================
    
    async def detect_language(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """Detect the language of a document."""
        headers = {
            "Accept": "text/plain"
        }
        if content_type:
            headers["Content-Type"] = content_type
        
        async with self.session.put(
            f"{self.server_url}/language/stream",
            data=content,
            headers=headers
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Language detection failed: {resp.status}")
            return await resp.text()
    
    # ==================== CONTENT TYPE DETECTION ====================
    
    async def detect_content_type(
        self,
        content: bytes
    ) -> str:
        """Detect the content type of a document."""
        async with self.session.put(
            f"{self.server_url}/detect/stream",
            data=content,
            headers={"Accept": "text/plain"}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Content type detection failed: {resp.status}")
            return await resp.text()
    
    # ==================== BATCH PROCESSING ====================
    
    async def process_batch(
        self,
        files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process multiple files.
        
        files: List of dicts with 'content', 'filename', 'content_type'
        """
        results = []
        for file_info in files:
            try:
                result = await self.extract_all(
                    content=file_info["content"],
                    content_type=file_info.get("content_type")
                )
                result["filename"] = file_info.get("filename", "unknown")
                result["success"] = True
                results.append(result)
            except Exception as e:
                results.append({
                    "filename": file_info.get("filename", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        return results
    
    # ==================== DOCUMENT ANALYSIS ====================
    
    async def analyze_document(
        self,
        content: bytes,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Comprehensive document analysis."""
        # Extract all content and metadata
        extraction = await self.extract_all(content, content_type)
        
        # Detect language
        try:
            language = await self.detect_language(content, content_type)
        except:
            language = "unknown"
        
        # Detect actual content type
        try:
            detected_type = await self.detect_content_type(content)
        except:
            detected_type = content_type or "unknown"
        
        # Calculate statistics
        text_content = extraction.get("content", "")
        word_count = len(text_content.split()) if text_content else 0
        char_count = len(text_content) if text_content else 0
        
        return {
            "content": text_content,
            "metadata": extraction.get("metadata", {}),
            "detected_content_type": detected_type.strip(),
            "language": language.strip(),
            "statistics": {
                "word_count": word_count,
                "character_count": char_count,
                "has_content": bool(text_content.strip())
            },
            "analyzed_at": datetime.utcnow().isoformat()
        }
    
    # ==================== STATS ====================
    
    async def get_supported_types(self) -> List[str]:
        """Get list of supported MIME types."""
        async with self.session.get(
            f"{self.server_url}/mime-types",
            headers={"Accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return list(self.SUPPORTED_TYPES.values())
            return await resp.json()
    
    async def get_parsers(self) -> Dict[str, Any]:
        """Get available parsers."""
        async with self.session.get(
            f"{self.server_url}/parsers",
            headers={"Accept": "application/json"}
        ) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Tika server statistics."""
        return {
            "server_url": self.server_url,
            "supported_extensions": list(self.SUPPORTED_TYPES.keys()),
            "supported_mime_types": await self.get_supported_types()
        }
