import json
import time
from openai import OpenAI
from src.config import OPENAI_API_KEY, OPENAI_MODEL

class BaseAgent:
    """Base class for cognitive agents interacting with OpenAI APIs."""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.client = None
        self.model = OPENAI_MODEL
        
        # Initialize OpenAI client if API key is present
        if OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                print(f"[ERROR] Failed to initialize OpenAI client for {self.name}: {e}")
                
    def is_available(self) -> bool:
        """Returns True if the OpenAI client is initialized and key is present."""
        return self.client is not None

    def call_llm(self, system_prompt: str, user_prompt: str, json_mode: bool = True, max_retries: int = 3) -> str:
        """Sends a request to the OpenAI API with retry logic and optional JSON mode."""
        if not self.is_available():
            raise ValueError(f"OpenAI API Key is missing. Agent '{self.name}' cannot execute cognitive LLM actions.")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2, # Low temperature for analytical consistency
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                return content
            except Exception as e:
                print(f"[WARNING] Agent '{self.name}' LLM call failed (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt) # Exponential backoff
                else:
                    raise e
                    
    def parse_json_response(self, response_text: str) -> dict:
        """Helper to safely parse JSON responses from the LLM."""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse JSON response for agent '{self.name}': {e}")
            print(f"Raw Response: {response_text}")
            # Fallback structure or re-raise
            raise e
