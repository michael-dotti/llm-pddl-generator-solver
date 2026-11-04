import sys # per far terminare prima il programma in caso di errori

# COSTANTI DELL'APPLICAZIONE
MAX_ATTEMPTS = 5
PROVIDERS_NAME = ["Google AI Studio", "OpenRouter", "Locale (Ollama)"]

# Modelli in locale
QWEN_NAME = "qwen2.5-coder:7b"
CODE_LAMA = "codellama:latest"
CODE_GEMMA = "codegemma:latest"
MISTRAL_ORCA = "mistral-openorca:7b"
COGITO = "cogito:8b"
LOCAL_MODELS = [QWEN_NAME, CODE_LAMA, CODE_GEMMA, MISTRAL_ORCA, COGITO]

# Google Ai Studio
GEMINI_3_FLASH  = "gemini-3-flash-preview"
GEMINI_25_LITE  = "gemini-2.5-flash-lite"
GEMINI_31_LITE  = "gemini-3.1-flash-lite"
GEMINI_35_LITE  = "gemini-3.5-flash-lite"
GEMINI_38_FLASH = "gemini-3.8-flash"
GEMINI_MODELS = [GEMINI_3_FLASH, GEMINI_25_LITE, GEMINI_31_LITE, GEMINI_35_LITE, GEMINI_38_FLASH ]


# OpenRouter
NEMOTRON_ULTRA     = "nvidia/nemotron-3-ultra-550b-a55b:free"
GEMMA_4_31B        = "google/gemma-4-31b-it:free"
XING_4_29B         = "xingchen-agi/xing4.0-29b-a4b:free" 
NEMOTRON_LIGHTNING = "nvidia/nemotron-3.5-lightning:free"
OPENROUTER_MODELS  = [NEMOTRON_ULTRA, GEMMA_4_31B, XING_4_29B, NEMOTRON_LIGHTNING]

def termina_programma(message):
    sys.exit(message)

# dizionario per la manutenibilità del codice
PROVIDERS = {
    # LOCALE
    QWEN_NAME: "ollama",
    CODE_LAMA: "ollama",
    CODE_GEMMA: "ollama",
    MISTRAL_ORCA: "ollama",
    COGITO: "ollama",
    # GOOGLE AI STUDIO
    GEMINI_3_FLASH: "gemini",
    GEMINI_25_LITE: "gemini",
    GEMINI_31_LITE: "gemini",
    GEMINI_35_LITE: "gemini",
    GEMINI_38_FLASH: "gemini",
    # OPEN ROUTER
    NEMOTRON_ULTRA: "openrouter",
    GEMMA_4_31B : "openrouter",
    XING_4_29B: "openrouter",
    NEMOTRON_LIGHTNING: "openrouter",
    
}