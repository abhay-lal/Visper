"""
RAG Service for Vectara Integration

This module provides a service class for integrating Vectara search capabilities
with the Gemini Multimodal Live API for Retrieval-Augmented Generation (RAG).
"""

import os
import requests
from typing import List, Dict, Any
import json


class VectaraRAGService:
    """Service class for handling Vectara search and RAG operations."""
    
    def __init__(self, customer_id: str, corpus_id: str, api_key: str):
        """
        Initialize the Vectara RAG service.
        
        Args:
            customer_id: Vectara customer ID
            corpus_id: Vectara corpus ID
            api_key: Vectara API key
        """
        self.customer_id = customer_id
        self.corpus_id = corpus_id
        self.api_key = api_key
        self.base_url = "https://api.vectara.io/v1/query"
    
    def search(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search Vectara for relevant documents.
        
        Args:
            query: Search query string
            num_results: Number of results to return (default: 3)
            
        Returns:
            List of dictionaries containing search results
        """
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        payload = {
            "query": [
                {
                    "query": query,
                    "num_results": num_results,
                    "corpus_key": [
                        {
                            "customer_id": self.customer_id,
                            "corpus_id": self.corpus_id
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return self._parse_search_results(response.json())
        except Exception as e:
            print(f"Vectara search error: {e}")
            return []
    
    def _parse_search_results(self, response: Dict) -> List[Dict[str, Any]]:
        """
        Parse Vectara search results into a clean format.
        
        Args:
            response: Raw response from Vectara API
            
        Returns:
            List of parsed search results
        """
        results = []
        if "responseSet" in response and response["responseSet"]:
            for result in response["responseSet"][0]["response"]:
                results.append({
                    "text": result["text"],
                    "score": result["score"],
                    "metadata": result.get("metadata", {}),
                    "document_id": result.get("documentIndex", "")
                })
        return results
    
    def build_context_prompt(self, query: str, retrieved_docs: List[Dict]) -> str:
        """
        Build a context-rich prompt for Gemini.
        
        Args:
            query: Original user query
            retrieved_docs: Retrieved documents from Vectara
            
        Returns:
            Enhanced prompt with context
        """
        if not retrieved_docs:
            return query
        
        context = "Based on the following information:\n\n"
        for i, doc in enumerate(retrieved_docs, 1):
            context += f"Source {i} (Score: {doc['score']:.3f}):\n{doc['text']}\n\n"
        
        context += f"Please answer this question: {query}\n\n"
        context += "If the information above doesn't contain enough details to answer the question, please say so and provide what you can based on your general knowledge."
        
        return context
    
    def get_context_summary(self, retrieved_docs: List[Dict]) -> str:
        """
        Get a summary of retrieved context for display purposes.
        
        Args:
            retrieved_docs: Retrieved documents from Vectara
            
        Returns:
            Summary string of retrieved context
        """
        if not retrieved_docs:
            return "No relevant context found."
        
        summary = f"Retrieved {len(retrieved_docs)} relevant documents:\n"
        for i, doc in enumerate(retrieved_docs, 1):
            summary += f"  {i}. Score: {doc['score']:.3f} - {doc['text'][:100]}...\n"
        
        return summary
