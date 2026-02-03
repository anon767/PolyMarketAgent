import requests
import time
from typing import List, Dict, Optional
from .base import AIProvider


class ChatGPTProvider(AIProvider):
    """ChatGPT provider implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_name(self) -> str:
        return "ChatGPT (GPT-4o-mini)"
    
    def chat(self, messages: List[Dict[str, str]], tools: List[Dict], 
             retry_count: int = 0, max_retries: int = 5) -> Optional[Dict]:
        """
        Send messages to ChatGPT and get response with exponential backoff retry.
        
        Args:
            messages: List of message dicts with role and content
            tools: List of tool definitions
            retry_count: Current retry attempt
            max_retries: Maximum number of retries
        
        Returns:
            Response dict from OpenAI API, or None if error
        """
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto"
                },
                timeout=60
            )
            
            if response.ok:
                return response.json()
            elif response.status_code == 429 and retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Rate limited. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self.chat(messages, tools, retry_count + 1, max_retries)
            elif response.status_code >= 500 and retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Server error. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self.chat(messages, tools, retry_count + 1, max_retries)
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Error: {e}. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self.chat(messages, tools, retry_count + 1, max_retries)
            else:
                print(f"Error calling ChatGPT: {e}")
                return None
