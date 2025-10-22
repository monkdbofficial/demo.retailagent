"""
Ollama Client Module
Production-ready client for Ollama (Mistral) with offline AI reasoning.
"""

import logging
import requests
import json
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Production-grade Ollama client for local LLM inference.
    Optimized for Mistral model running offline.
    """

    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "mistral"):
        """
        Initialize Ollama client.

        Args:
            base_url: Ollama server URL
            model: Model name (default: mistral)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_generate = f"{self.base_url}/api/generate"
        self.api_chat = f"{self.base_url}/api/chat"

        # Verify connection
        if not self.health_check():
            logger.warning(f"⚠️ Ollama server not accessible at {base_url}")

    def health_check(self) -> bool:
        """
        Check if Ollama server is running.

        Returns:
            True if server is accessible, False otherwise
        """
        try:
            response = requests.get(self.base_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ Ollama server is running at {self.base_url}")
                return True
        except Exception as e:
            logger.error(f"❌ Ollama server check failed: {e}")
        return False

    def generate(self, prompt: str, stream: bool = False, 
                 temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Generate text completion using Ollama.

        Args:
            prompt: Input prompt
            stream: Enable streaming
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(
                self.api_generate,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "")
                logger.info(f"✅ Generated {len(text)} characters")
                return text.strip()
            else:
                logger.error(f"❌ Generation failed: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"❌ Generation error: {e}")
            return ""

    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7) -> str:
        """
        Chat with Ollama using conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature

        Returns:
            Assistant's response
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            response = requests.post(
                self.api_chat,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                message = result.get("message", {})
                content = message.get("content", "")
                logger.info(f"✅ Chat response: {len(content)} characters")
                return content.strip()
            else:
                logger.error(f"❌ Chat failed: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"❌ Chat error: {e}")
            return ""

    def generate_insights(self, data_summary: Dict[str, Any]) -> str:
        """
        Generate AI insights from data summary.

        Args:
            data_summary: Dictionary with data statistics

        Returns:
            AI-generated insights
        """
        prompt = f"""You are a data analyst AI. Analyze the following product data summary and provide actionable business insights.

Data Summary:
{json.dumps(data_summary, indent=2)}

Provide:
1. Key findings (3-5 bullet points)
2. Trends and patterns
3. Potential opportunities or concerns
4. Actionable recommendations

Be concise, data-driven, and specific. Use the actual numbers provided.
"""

        return self.generate(prompt, temperature=0.7, max_tokens=1000)

    def generate_summary_card(self, metric_name: str, 
                             metric_value: Any, context: str = "") -> str:
        """
        Generate a one-line insight for a summary card.

        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            context: Additional context

        Returns:
            Short insight text
        """
        prompt = f"""Generate a ONE SHORT SENTENCE (max 15 words) insight about this metric:

Metric: {metric_name}
Value: {metric_value}
Context: {context}

Be specific and actionable. Just return the sentence, nothing else.
"""

        return self.generate(prompt, temperature=0.5, max_tokens=50)

    def answer_question(self, question: str, 
                       data_context: str) -> str:
        """
        Answer a user question based on data context.

        Args:
            question: User's question
            data_context: Relevant data as context

        Returns:
            AI-generated answer
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful data analyst assistant. Answer questions based on the provided data context. Be accurate and cite specific numbers when available only in indian currency format, return only results, no code or process"
            },
            {
                "role": "user",
                "content": f"""Data Context:
{data_context}

Question: {question}

Provide a clear, data-driven answer, results should be only in INR"""
            }
        ]

        return self.chat(messages, temperature=0.6)

    def generate_report_summary(self, insights: Dict[str, Any]) -> str:
        """
        Generate executive summary for PDF report.

        Args:
            insights: Dictionary with all insights

        Returns:
            Executive summary text
        """
        prompt = f"""Create an executive summary for a product analytics report.

Key Insights:
{json.dumps(insights, indent=2)}

Generate a professional 2-paragraph executive summary that:
1. Highlights the most important findings
2. Provides clear business implications

Keep it concise and business-focused.
"""

        return self.generate(prompt, temperature=0.6, max_tokens=500)

    def suggest_actions(self, low_performers: List[Dict]) -> List[str]:
        """
        Suggest actions based on low-performing products.

        Args:
            low_performers: List of low-performing product data

        Returns:
            List of action suggestions
        """
        prompt = f"""Based on these low-performing products, suggest 3 specific actions:

Products:
{json.dumps(low_performers[:5], indent=2)}

Provide exactly 3 actionable recommendations. Format as:
1. [Action]
2. [Action]
3. [Action]
"""

        response = self.generate(prompt, temperature=0.7, max_tokens=300)

        # Parse into list
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        actions = [line for line in lines if line[0].isdigit()]

        return actions[:3] if actions else ["Review product pricing", "Improve product descriptions", "Enhance customer engagement"]
