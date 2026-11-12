import os
from openai import OpenAI

class NvidiaNimLLMWrapper:
    def __init__(self, model_name: str = "mistralai/mistral-large-4-1t-a52b"):
        self.model_name = model_name
        # NVIDIA NIM utilizza un endpoint compatibile con OpenAI
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def query(self, prompt: str, end_when_error=False, max_retry=3, est_margin=200) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
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
            temperature=0.0
        )
        if response.usage:
            self.prompt_tokens += response.usage.prompt_tokens
            self.completion_tokens += response.usage.completion_tokens
            
        return response.choices[0].message.content

    def reset_tokens(self):
        """Metodo richiesto internamente da l2p per azzerare i contatori."""
        self.prompt_tokens = 0
        self.completion_tokens = 0