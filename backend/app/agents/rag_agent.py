# backend/app/agents/rag_agent.py
"""
RAG (Retrieval-Augmented Generation) agent for document queries.
"""
import os
from typing import List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.models.state import AnalyticsState
from app.retrievers import get_document_retriever

load_dotenv()


class RAGAgent:
    """
    Agent that answers questions using retrieved document context.
    
    Workflow:
    1. Retrieve relevant chunks from documents
    2. Build context with sources
    3. Generate answer using LLM
    4. Return answer with citations
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.1):
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.retriever = get_document_retriever()
    
    def answer_question(self, state: AnalyticsState) -> AnalyticsState:
        """
        Answer a question using document RAG.
        
        Retrieves relevant chunks and generates an answer with citations.
        """
        question = state["question"]
        doc_ids = state.get("document_ids")  # Optional: specific documents
        
        # Retrieve relevant chunks
        try:
            results = self.retriever.retrieve(
                query=question,
                doc_ids=doc_ids,
                top_k=5
            )
            
            if not results:
                state["summary"] = "No relevant information found in the uploaded documents."
                state["sources"] = []
                return state
            
            # Build context
            context_parts = []
            sources = []
            
            for i, result in enumerate(results, 1):
                context_parts.append(
                    f"[Source {i}: {result['filename']}]\n{result['chunk_text']}"
                )
                sources.append({
                    "source_id": i,
                    "filename": result['filename'],
                    "doc_id": result['doc_id']
                })
            
            context = "\n\n".join(context_parts)
            
            # Generate answer
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant that answers questions based on provided document context.

RULES:
1. Answer based ONLY on the provided context
2. Cite sources using [Source N] notation
3. If the context doesn't contain the answer, say so
4. Be concise but complete
5. Use bullet points for multiple items"""),
                ("human", """Context from documents:
{context}

Question: {question}

Provide a clear answer with source citations.""")
            ])
            
            chain = prompt | self.llm
            
            response = chain.invoke({
                "context": context,
                "question": question
            })
            
            state["summary"] = response.content
            state["sources"] = sources
            state["error"] = None
            
        except Exception as e:
            state["summary"] = "Error processing document query."
            state["error"] = f"RAG error: {str(e)}"
            state["sources"] = []
        
        return state
    
    def list_documents(self) -> List[dict]:
        """List all available documents"""
        from app.ingestion import DocumentMetadata
        return DocumentMetadata.list_all()

# Made with Bob
