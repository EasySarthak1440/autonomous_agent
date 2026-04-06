"""
LLM Backend - Integration with Groq API (OpenAI-compatible)
"""

import json
import logging
from typing import Any, Optional
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class LLMBackend:
    """Backend for interfacing with Groq API (OpenAI-compatible)."""
    
    def __init__(
        self,
        model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct",
        api_key: str = "",
        base_url: str = "https://api.groq.com/openai/v1",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 120
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using the LLM.
        """
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        try:
            async with self._get_session().post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error = await response.text()
                    raise Exception(f"LLM API error: {response.status} - {error}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to LLM: {e}")
    
    async def generate_with_structured_output(
        self,
        prompt: str,
        schema: dict,
        system_prompt: Optional[str] = None
    ) -> dict:
        """
        Generate structured output conforming to a schema.
        """
        schema_str = json.dumps(schema)
        full_prompt = f"""{prompt}

Respond with valid JSON only, matching this schema:
{schema_str}

JSON Response:"""
        
        response = await self.generate(full_prompt, system_prompt)
        
        # Parse JSON from response
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise Exception(f"Invalid JSON in LLM response: {response[:200]}")

    async def chat(
        self,
        messages: list[dict],
        **kwargs
    ) -> str:
        """
        Chat with the LLM using message history.
        """
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        try:
            async with self._get_session().post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error = await response.text()
                    raise Exception(f"LLM API error: {response.status} - {error}")
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to connect to LLM: {e}")

    async def check_health(self) -> bool:
        """Check if the LLM API is available."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            async with self._get_session().get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def __del__(self):
        """Cleanup on deletion."""
        if self._session and not self._session.closed:
            try:
                asyncio.get_event_loop().run_until_complete(self._session.close())
            except Exception:
                pass
