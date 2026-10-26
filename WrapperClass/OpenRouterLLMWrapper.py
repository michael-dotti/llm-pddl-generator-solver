import os
from openai import OpenAI

class OpenRouterLLMWrapper:
    def __init__(self, model_name: str = "qwen/qwen-2.5-72b-instruct"):
        self.model_name = model_name
        # OpenRouter usa le API compatibili con OpenAI, ma cambia il base_url e l'API key
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def query(self, prompt: str, end_when_error=False, max_retry=3, est_margin=200) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            extra_headers={
                "HTTP-Referer": "https://github.com/AI-Planning/l2p", # Consigliato da OpenRouter per le classifiche
                "X-Title": "L2P Domain Generator"
            }
        )
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
            temperature=0.0,
            extra_headers={
                "HTTP-Referer": "https://github.com/AI-Planning/l2p",
                "X-Title": "L2P Domain Generator"
            }
        )
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
            
        return response.choices[0].message.content

    def reset_tokens(self):
        """Metodo richiesto internamente da l2p per azzerare i contatori."""
        self.prompt_tokens = 0
        self.completion_tokens = 0