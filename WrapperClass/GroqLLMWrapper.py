import os
from openai import OpenAI

class GroqLLMWrapper:
    def __init__(self, model_name: str = "qwen/qwen3.8-27b"):
        self.model_name = model_name
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        # Variabili di servizio per i token (richieste o compatibili con l2p)
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def query(self, prompt: str, end_when_error=False, max_retry=3, est_margin=200) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=8000
        )
        # Registriamo i token se restituiti dall'API
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
            
        return response.choices[0].message.content

    def query_with_system_prompt(self, system_prompt: str, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        # Registriamo i token se restituiti dall'API
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
            
        return response.choices[0].message.content

    def reset_tokens(self):
        """Metodo richiesto internamente da l2p per azzerare il contatore dei token."""
        self.prompt_tokens = 0
        self.completion_tokens = 0