# Classe che si occupa dell'inizializzazione del LLM (menu a scelta per utenti + collegamento all'LLM)

import questionary
from config import (
    PROVIDERS_NAME,
    GEMINI_MODELS,
    OPENROUTER_MODELS,
    LOCAL_MODELS,
    UNIFIED_LLM_PROVIDERS,
    NVIDIA_MODELS,
    termina_programma
)

# Importo le classi wrapper per utilizzare gli llm in cloud che normalmente non sono compatibili con l2p
from WrapperClass.openrouter_wrapper import OpenRouterLLMWrapper
from WrapperClass.nvidia_wrapper import NvidiaNimLLMWrapper
from l2p import UnifiedLLM

def initialize_llm():
    """
    Gestisce l'interfaccia interattiva per la scelta del provider e del modello LLM,
    effettua la validazione e restituisce l'istanza dell'LLM inizializzata.
    """
    # ==========================================
    # 1. SELEZIONE DEL PROVIDER
    # ==========================================
    provider_choice = questionary.select(
        "Da quale provider vuoi recuperare l'LLM?",
        choices=PROVIDERS_NAME,
        instruction=""
    ).ask()

    if provider_choice == "Google AI Studio":
        model_choices = GEMINI_MODELS
    elif provider_choice == "OpenRouter":
        model_choices = OPENROUTER_MODELS
    elif provider_choice == "Locale (Ollama)":
        model_choices = LOCAL_MODELS
    elif provider_choice == "Nvidia NIM":
        model_choices = NVIDIA_MODELS
    else:
        termina_programma(f"Hai selezionato un provider non valido: {provider_choice}\nIl Programma Termina...")

    # ==========================================
    # 2. SELEZIONE DEL MODELLO SPECIFICO
    # ==========================================
    response = questionary.select(
        f"Quale modello vuoi utilizzare da {provider_choice}?",
        choices=model_choices,
        instruction=""
    ).ask()

    # ==========================================
    # 3. VALIDAZIONE E INIZIALIZZAZIONE
    # ==========================================

    if response in OPENROUTER_MODELS:
        # Wrapper personalizzato per OpenRouter
        llm = OpenRouterLLMWrapper(model_name=response)
        provider = "OpenRouter"
    elif response in NVIDIA_MODELS:
        # Wrapper personalizzato per NVIDIA NIM
        llm = NvidiaNimLLMWrapper(model_name=response)
        provider = "Nvidia"
    elif response in UNIFIED_LLM_PROVIDERS:
        # Modelli nativi l2p (Gemini ed Ollama)
        llm = UnifiedLLM(
            provider=UNIFIED_LLM_PROVIDERS[response],
            model=response,
            config_path="my_llm.yaml"
        )
        provider = UNIFIED_LLM_PROVIDERS[response]
    else:
        termina_programma(f"Hai selezionato un LLM non supportato: {response}\nIl Programma Termina...")

    print(f"\n[OK] LLM inizializzato con successo: {response} (Provider: {provider})\n")
    return llm