# backend/app/agents/knowledge_graph_agent.py
"""
Knowledge Graph extraction agent using spaCy and LLM.
"""
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

import spacy
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.models.state import AnalyticsState
from app.retrievers import get_document_retriever

load_dotenv()


class KnowledgeGraphAgent:
    """
    Agent that extracts entities and relationships from documents.
    
    Workflow:
    1. Retrieve relevant document chunks
    2. Extract named entities using spaCy
    3. Use LLM to identify relationships
    4. Build knowledge graph structure
    """
    
    def __init__(self, model: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY", "")
        )
        self.retriever = get_document_retriever()
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model not found. Run: python -m spacy download en_core_web_sm")
            self.nlp = None
    
    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities using spaCy"""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        entities = []
        seen = set()
        
        for ent in doc.ents:
            # Filter relevant entity types
            if ent.label_ in ["PERSON", "ORG", "GPE", "PRODUCT", "EVENT", "LAW"]:
                if ent.text not in seen:
                    entities.append({
                        "text": ent.text,
                        "type": ent.label_
                    })
                    seen.add(ent.text)
        
        return entities
    
    def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Use LLM to extract relationships between entities"""
        
        if not entities or len(entities) < 2:
            return []
        
        entity_list = ", ".join([f"{e['text']} ({e['type']})" for e in entities])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting relationships from text.

Given a text and a list of entities, identify relationships between them.

Return relationships in this format:
- Entity1 | relationship | Entity2

Examples:
- Acme Corp | contracts_with | XYZ Logistics
- John Smith | works_for | Acme Corp
- Product X | manufactured_by | Acme Corp

Only extract relationships that are explicitly stated or strongly implied in the text."""),
            ("human", """Text:
{text}

Entities: {entities}

Extract relationships between these entities. Return one relationship per line.""")
        ])
        
        chain = prompt | self.llm
        
        try:
            response = chain.invoke({
                "text": text[:2000],  # Limit text length
                "entities": entity_list
            })
            
            # Parse relationships
            relationships = []
            for line in response.content.split("\n"):
                line = line.strip()
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) == 3:
                        relationships.append({
                            "source": parts[0].lstrip("- "),
                            "relation": parts[1],
                            "target": parts[2]
                        })
            
            return relationships
            
        except Exception as e:
            print(f"Error extracting relationships: {e}")
            return []
    
    def build_knowledge_graph(self, state: AnalyticsState) -> AnalyticsState:
        """
        Build knowledge graph from documents.
        
        Returns graph structure with nodes and edges.
        """
        question = state["question"]
        doc_ids = state.get("document_ids")
        
        try:
            # Retrieve relevant chunks
            results = self.retriever.retrieve(
                query=question,
                doc_ids=doc_ids,
                top_k=10  # More chunks for better entity coverage
            )
            
            if not results:
                state["knowledge_graph"] = {"nodes": [], "edges": []}
                state["summary"] = "No documents found to extract knowledge graph."
                return state
            
            # Combine text from chunks
            combined_text = "\n\n".join([r["chunk_text"] for r in results])
            
            # Extract entities
            entities = self.extract_entities(combined_text)
            
            if not entities:
                state["knowledge_graph"] = {"nodes": [], "edges": []}
                state["summary"] = "No entities found in the documents."
                return state
            
            # Extract relationships
            relationships = self.extract_relationships(combined_text, entities)
            
            # Build graph structure
            nodes = [
                {
                    "id": ent["text"],
                    "label": ent["text"],
                    "type": ent["type"]
                }
                for ent in entities
            ]
            
            edges = [
                {
                    "source": rel["source"],
                    "target": rel["target"],
                    "relation": rel["relation"]
                }
                for rel in relationships
            ]
            
            state["knowledge_graph"] = {
                "nodes": nodes,
                "edges": edges
            }
            
            # Generate summary
            summary_parts = [
                f"Extracted {len(nodes)} entities and {len(edges)} relationships.",
                f"Entity types: {', '.join(set(n['type'] for n in nodes))}",
            ]
            
            if edges:
                summary_parts.append(
                    f"Key relationships: {', '.join([e['relation'] for e in edges[:3]])}"
                )
            
            state["summary"] = " ".join(summary_parts)
            state["error"] = None
            
        except Exception as e:
            state["knowledge_graph"] = {"nodes": [], "edges": []}
            state["error"] = f"Knowledge graph extraction failed: {str(e)}"
            state["summary"] = "Error extracting knowledge graph."
        
        return state

# Made with Bob
