"""
Chatbot Agent
Handles natural language queries about product data.
"""

import logging
from typing import Dict, Any
from core.monkdb_client import MonkDBClient
from core.ollama_client import OllamaClient
import pandas as pd

logger = logging.getLogger(__name__)


class ChatbotAgent:
    """
    Agent for interactive chat-based queries.
    """

    def __init__(self, db_client: MonkDBClient, ollama_client: OllamaClient):
        """
        Initialize chatbot agent.

        Args:
            db_client: MonkDB client instance
            ollama_client: Ollama client instance
        """
        self.db = db_client
        self.ollama = ollama_client
        self.conversation_history = []

        logger.info("✅ Chatbot Agent initialized")

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process user query and return answer with data.

        Args:
            user_query: User's natural language question

        Returns:
            Dictionary with answer and data
        """
        logger.info(f"💬 Processing query: {user_query}")

        try:
            # Determine query intent and fetch relevant data
            data_context = self._fetch_relevant_data(user_query)

            # Generate AI answer
            answer = self.ollama.answer_question(user_query, data_context)

            return {
                "query": user_query,
                "answer": answer,
                "data_context": data_context,
                "status": "success"
            }

        except Exception as e:
            logger.error(f"❌ Error processing query: {e}")
            return {
                "query": user_query,
                "answer": f"I encountered an error: {str(e)}",
                "status": "error"
            }

    def _fetch_relevant_data(self, query: str) -> str:
        """Fetch relevant data based on query intent."""
        query_lower = query.lower()

        # Brand-related queries
        if 'brand' in query_lower:
            df = self.db.query_top_brands(limit=20)
            return f"Top Brands Data:\n{df.to_string()}"

        # Price-related queries
        elif 'price' in query_lower or 'expensive' in query_lower or 'cheap' in query_lower:
            query_sql = f"""
            SELECT brand, title, price, rating 
            FROM {self.db.schema}.products 
            WHERE price > 0 
            ORDER BY price DESC 
            LIMIT 20
            """
            df = self.db.execute_query(query_sql)
            return f"Price Data:\n{df.to_string()}"

        # Rating-related queries
        elif 'rating' in query_lower or 'rated' in query_lower:
            query_sql = f"""
            SELECT brand, title, rating, rating_total, price
            FROM {self.db.schema}.products 
            WHERE rating > 0 
            ORDER BY rating DESC 
            LIMIT 20
            """
            df = self.db.execute_query(query_sql)
            return f"Rating Data:\n{df.to_string()}"

        # Discount-related queries
        elif 'discount' in query_lower:
            query_sql = f"""
            SELECT brand, title, price, mrp, discount_percent
            FROM {self.db.schema}.products 
            WHERE discount_percent > 0 
            ORDER BY discount_percent DESC 
            LIMIT 20
            """
            df = self.db.execute_query(query_sql)
            return f"Discount Data:\n{df.to_string()}"

        # Default: summary stats
        else:
            stats = self.db.get_summary_stats()
            return f"Summary Statistics:\n{stats}"
