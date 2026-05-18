# backend/app/retrievers/document_retriever.py
"""
Document retrieval using FAISS for RAG queries.
"""
import os
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

from app.ingestion import DocumentMetadata

load_dotenv()


class DocumentRetriever:
    """
    Retrieves relevant document chunks using FAISS similarity search.
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self._index_cache = {}
        self._chunks_cache = {}
    
    def _load_index(self, doc_id: str) -> tuple[faiss.Index, List[str]]:
        """Load FAISS index and chunks for a document"""
        if doc_id in self._index_cache:
            return self._index_cache[doc_id], self._chunks_cache[doc_id]
        
        metadata = DocumentMetadata.get(doc_id)
        if not metadata:
            raise ValueError(f"Document {doc_id} not found")
        
        # Load FAISS index
        index = faiss.read_index(metadata["index_path"])
        
        # Load chunks
        chunks_text = Path(metadata["chunks_path"]).read_text(encoding="utf-8")
        chunks = chunks_text.split("\n---CHUNK---\n")
        
        # Cache
        self._index_cache[doc_id] = index
        self._chunks_cache[doc_id] = chunks
        
        return index, chunks
    
    def retrieve(
        self,
        query: str,
        doc_ids: List[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve most relevant chunks across one or more documents.
        
        Args:
            query: User question
            doc_ids: List of document IDs to search (None = all documents)
            top_k: Number of chunks to return per document
        
        Returns:
            List of dicts with keys: doc_id, chunk_text, score, filename
        """
        if doc_ids is None:
            # Search all documents
            all_docs = DocumentMetadata.list_all()
            doc_ids = [doc["doc_id"] for doc in all_docs]
        
        if not doc_ids:
            return []
        
        # Embed query
        query_embedding = self.embeddings.embed_query(query)
        query_vector = np.array([query_embedding], dtype="float32")
        
        results = []
        
        for doc_id in doc_ids:
            try:
                index, chunks = self._load_index(doc_id)
                metadata = DocumentMetadata.get(doc_id)
                
                # Search
                k = min(top_k, len(chunks))
                distances, indices = index.search(query_vector, k)
                
                # Build results
                for i, idx in enumerate(indices[0]):
                    if idx < len(chunks):
                        results.append({
                            "doc_id": doc_id,
                            "filename": metadata["filename"],
                            "chunk_text": chunks[idx],
                            "score": float(distances[0][i]),
                            "rank": i + 1
                        })
            
            except Exception as e:
                print(f"Error retrieving from {doc_id}: {e}")
                continue
        
        # Sort by score (lower is better for L2 distance)
        results.sort(key=lambda x: x["score"])
        
        return results[:top_k * len(doc_ids)]
    
    def get_context(
        self,
        query: str,
        doc_ids: List[str] = None,
        top_k: int = 5
    ) -> str:
        """
        Get formatted context string for RAG.
        
        Returns a string with retrieved chunks and sources.
        """
        results = self.retrieve(query, doc_ids, top_k)
        
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}: {result['filename']}]\n{result['chunk_text']}\n"
            )
        
        return "\n".join(context_parts)


# Singleton instance
_retriever = None


def get_document_retriever() -> DocumentRetriever:
    """Get or create document retriever instance"""
    global _retriever
    if _retriever is None:
        _retriever = DocumentRetriever()
    return _retriever

# Made with Bob
