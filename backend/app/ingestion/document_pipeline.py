# backend/app/ingestion/document_pipeline.py
"""
Document ingestion pipeline for PDF, DOCX, PPTX, and TXT files.

Handles:
- Document upload and validation
- Text extraction
- Chunking
- Embedding generation
- FAISS indexing
- Metadata persistence
"""
import os
import uuid
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import faiss
import numpy as np
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    TextLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Constants
DOCUMENTS_DIR = Path(__file__).parent.parent.parent / "documents"
DOCUMENTS_DIR.mkdir(exist_ok=True)

FAISS_INDEX_DIR = Path(__file__).parent.parent.parent / "faiss_indices"
FAISS_INDEX_DIR.mkdir(exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
MAX_FILE_SIZE_MB = 50


class DocumentMetadata:
    """In-memory document metadata registry"""
    _documents: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, doc_id: str, metadata: Dict[str, Any]):
        cls._documents[doc_id] = metadata
    
    @classmethod
    def get(cls, doc_id: str) -> Dict[str, Any]:
        return cls._documents.get(doc_id)
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return list(cls._documents.values())
    
    @classmethod
    def delete(cls, doc_id: str):
        cls._documents.pop(doc_id, None)


class DocumentPipeline:
    """
    Pipeline for processing and indexing documents.
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def validate_file(self, filename: str, file_size: int) -> None:
        """Validate file extension and size"""
        ext = Path(filename).suffix.lower()
        
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {ext}. "
                f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
        
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(
                f"File too large: {file_size / (1024*1024):.1f}MB. "
                f"Max: {MAX_FILE_SIZE_MB}MB"
            )
    
    def save_document(self, file_content: bytes, filename: str) -> tuple[str, str]:
        """
        Save uploaded document to disk.
        
        Returns:
            (doc_id, file_path)
        """
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        ext = Path(filename).suffix.lower()
        file_path = DOCUMENTS_DIR / f"{doc_id}{ext}"
        
        file_path.write_bytes(file_content)
        
        return doc_id, str(file_path)
    
    def load_document(self, file_path: str) -> List[Any]:
        """
        Load document using appropriate loader based on extension.
        """
        ext = Path(file_path).suffix.lower()
        
        loaders = {
            ".pdf": PyMuPDFLoader,
            ".docx": Docx2txtLoader,
            ".pptx": UnstructuredPowerPointLoader,
            ".txt": TextLoader,
        }
        
        loader_class = loaders.get(ext)
        if not loader_class:
            raise ValueError(f"No loader for extension: {ext}")
        
        loader = loader_class(file_path)
        return loader.load()
    
    def process_document(
        self,
        doc_id: str,
        file_path: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Complete document processing pipeline.
        
        Steps:
        1. Load document
        2. Split into chunks
        3. Generate embeddings
        4. Create FAISS index
        5. Save index and metadata
        
        Returns:
            Document metadata dict
        """
        # Load and split
        documents = self.load_document(file_path)
        chunks = self.text_splitter.split_documents(documents)
        
        if not chunks:
            raise ValueError("No text extracted from document")
        
        # Extract text from chunks
        texts = [chunk.page_content for chunk in chunks]
        
        # Generate embeddings
        embeddings_list = self.embeddings.embed_documents(texts)
        embeddings_array = np.array(embeddings_list, dtype="float32")
        
        # Create FAISS index
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        # Save FAISS index
        index_path = FAISS_INDEX_DIR / f"{doc_id}.faiss"
        faiss.write_index(index, str(index_path))
        
        # Save chunks metadata
        chunks_path = FAISS_INDEX_DIR / f"{doc_id}_chunks.txt"
        chunks_path.write_text("\n---CHUNK---\n".join(texts), encoding="utf-8")
        
        # Build metadata
        metadata = {
            "doc_id": doc_id,
            "filename": filename,
            "file_path": file_path,
            "index_path": str(index_path),
            "chunks_path": str(chunks_path),
            "num_chunks": len(chunks),
            "num_pages": len(documents),
            "file_type": Path(filename).suffix.lower(),
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        
        # Register metadata
        DocumentMetadata.register(doc_id, metadata)
        
        return metadata
    
    def delete_document(self, doc_id: str) -> None:
        """Delete document and its index"""
        metadata = DocumentMetadata.get(doc_id)
        if not metadata:
            return
        
        # Delete files
        try:
            Path(metadata["file_path"]).unlink(missing_ok=True)
            Path(metadata["index_path"]).unlink(missing_ok=True)
            Path(metadata["chunks_path"]).unlink(missing_ok=True)
        except Exception as e:
            print(f"Error deleting files for {doc_id}: {e}")
        
        # Remove from registry
        DocumentMetadata.delete(doc_id)


# Singleton instance
_pipeline = None


def get_document_pipeline() -> DocumentPipeline:
    """Get or create document pipeline instance"""
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentPipeline()
    return _pipeline

# Made with Bob
