# backend/app/ingestion/__init__.py
from .document_pipeline import DocumentPipeline, DocumentMetadata, get_document_pipeline

__all__ = ["DocumentPipeline", "DocumentMetadata", "get_document_pipeline"]

# Made with Bob
