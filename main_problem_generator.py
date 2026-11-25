import time 
import questionary 
from datetime import datetime 
from dotenv import load_dotenv 
from pathlib import Path

# Classe per generare i componenti del problema
from l2p.problem_builder import ProblemBuilder


from llm_factory import initialize_llm
from prompt_manager import get_problem_prompts


load_dotenv()

from config import (
    MAX_ATTEMPTS, 
    termina_programma
)


# ==========================================
# 1. SELEZIONE A DUE PASSI (CARTELLA -> FILE)
# ==========================================

# -------------------------------------------------------------
# ESTRAZIONE AUTOMATICA DEL NOME DEL PROBLEM PDDL
# -------------------------------------------------------------

# -------------------------------------------------------------
# SCELTA MODALITÀ DI NAMING DEL FILE PDDL DI SALVATAGGIO
# -------------------------------------------------------------

# ==========================================
# 2. INIZIALIZZAZIONE DELL'LLM 
# ==========================================
llm = initialize_llm()

# ==========================================
# 3. CARICAMENTO / GENERAZIONE DEI PROMPT
# ==========================================
custom_objects_prompt, custom_initial_states_prompt, custom_goal_state_prompt, custom_revise_prompt = get_problem_prompts(
    selected_folder=selected_folder,
    current_domain_file_name=current_domain_file_name
)

prompts = (custom_objects_prompt, custom_initial_states_prompt, custom_goal_state_prompt, custom_revise_prompt)


# ============================================================
# 4. GENERAZIONE INIZIALE DEI COMPONENT DEL FILE DOMAIN.PDDL
# ============================================================
start_time = time.time()

end_time = time.time()



# =======================================================
# 5. RISULTATO FINALE
# =======================================================