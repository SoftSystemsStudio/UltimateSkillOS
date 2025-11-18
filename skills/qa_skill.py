"""
Question Answering Skill using LLM (OpenAI, Anthropic, etc.)
Securely reads API keys from environment variables.
"""
import os
from typing import Optional, Dict, Any
from skill_engine.base import BaseSkill


class QASkill(BaseSkill):
    """
    A general question-answering skill that uses an LLM to answer queries.
    Supports OpenAI, Anthropic, Google, and local LLM endpoints.
    """
    
    name = "question_answering"
    description = "Answers general questions using a large language model (LLM)."
    keywords = ["question", "answer", "what", "how", "why", "explain", "tell me"]
    
    def __init__(self):
        super().__init__()
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4")
        self._client = None
    
    def _get_client(self):
        """
        Lazy-load the LLM client based on the provider.
        API keys are read from environment variables.
        """
        if self._client is not None:
            return self._client
        
        if self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError(
                        "OPENAI_API_KEY not found in environment variables. "
                        "Please add it to your .env file."
                    )
                self._client = OpenAI(api_key=api_key)
                return self._client
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Run: pip install openai"
                )
        
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError(
                        "ANTHROPIC_API_KEY not found in environment variables. "
                        "Please add it to your .env file."
                    )
                self._client = Anthropic(api_key=api_key)
                return self._client
            except ImportError:
                raise ImportError(
                    "Anthropic package not installed. Run: pip install anthropic"
                )
        
        elif self.provider == "local":
            # For local LLMs (Ollama, LM Studio, etc.)
            endpoint = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:11434")
            self._client = {"endpoint": endpoint, "type": "local"}
            return self._client
        
        else:
            raise ValueError(
                f"Unsupported LLM provider: {self.provider}. "
                f"Supported providers: openai, anthropic, local"
            )
    
    def _run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the QA skill to answer a question using an LLM.
        
        Args:
            params: Dictionary containing 'query' key with the user's question
        
        Returns:
            dict with 'final_answer' key containing the LLM response
        """
        # Extract query from params (handle both direct string and dict)
        if isinstance(params, str):
            query = params
        else:
            query = params.get("query", "") or params.get("input", "")
        
        if not query:
            return {"final_answer": "No query provided", "error": "Missing query parameter"}
        
        try:
            client = self._get_client()
            
            # Call the appropriate LLM based on provider
            if self.provider == "openai":
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI assistant. Provide clear, accurate, and concise answers."
                        },
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                answer = response.choices[0].message.content
            
            elif self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model or "claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[
                        {
                            "role": "user",
                            "content": query
                        }
                    ]
                )
                answer = response.content[0].text
            
            elif self.provider == "local":
                # For local LLMs, use requests library
                import requests
                endpoint = client["endpoint"]
                response = requests.post(
                    f"{endpoint}/api/generate",
                    json={
                        "model": self.model or "llama2",
                        "prompt": query,
                        "stream": False
                    }
                )
                response.raise_for_status()
                answer = response.json().get("response", "No response from local LLM")
            
            else:
                answer = "Error: Unsupported LLM provider"
            
            return {
                "final_answer": answer,
                "provider": self.provider,
                "model": self.model
            }
        
        except Exception as e:
            # Return error information for debugging
            self.log.error(f"Error calling LLM: {str(e)}")
            return {
                "final_answer": f"Error calling LLM: {str(e)}",
                "error": str(e),
                "provider": self.provider
            }


# Register the skill (auto-discovered by SkillEngine)
__all__ = ["QASkill"]
