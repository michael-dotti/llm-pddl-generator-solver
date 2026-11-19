# Fasi sviluppo main_pipeline_solver: 
# 1) versione 0.1: l'utente può selezionare un domain.pddl e problem.pddl tra quelli esistenti
# 2) versione 0.5 :l'utente può dare in pasto a un planner i domain.pddl e problem.pddl scelti per risolvere il problema
# 3) versione 1 : il sistema chiederà se selezionare un domain.pddl e/o problem.pddl esistenti o se generarli al momento

import time 
import questionary 
from datetime import datetime 
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from config import (
    MAX_ATTEMPTS, 
    termina_programma
)

from llm_factory import initialize_llm
from prompt_manager import get_domain_prompts
from pipeline_executor import run_domain_pipeline

def _select_pddl_file(target_dir: Path, file_type: str) -> Path:
    """Funzione helper privata per gestire la scansione e la scelta del file tramite questionary."""

    # verifico che la cartella esista
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"La cartella '{target_dir}' non esiste o non è una directory.")

    files = [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pddl']

    if not files:
        raise ValueError(f"Nessun file .pddl trovato nella cartella '{target_dir.name}'.")

    selected = questionary.select(
        f"Seleziona il file di {file_type} PDDL da utilizzare:",
        choices=files
    ).ask()

    if not selected:
        raise KeyboardInterrupt(f"Selezione del {file_type.lower()} interrotta dall'utente.")

    return target_dir / selected

domains_dir = Path("domains")
problems_dir = Path("problems")


# ==========================================
# 1. SELEZIONE DEL DOMAIN.PDDL e PROBLEM.PDDL 
# ==========================================
print("=== PDDL Solver Pipeline (v0.5) ===\n")

domains_dir = Path("domains")
problems_dir = Path("problems")

try:
    # 1. selezione del domain.pddl
    domain_path = _select_pddl_file(domains_dir, "Domain")
    
    # 2. selezione del problem.pddl
    problem_path = _select_pddl_file(problems_dir, "Problem")

except (FileNotFoundError, ValueError, KeyboardInterrupt) as e:
    termina_programma(str(e))

print("\n--- Configurazione Selezionata ---")
print(f"📁 Domain Path:  {domain_path}")
print(f"📁 Problem Path: {problem_path}")
print("-----------------------------------")

# ==========================================
# 3. UTILIZZO DEL PLANNER PER RISOLVERE IL PROBLEMA
# ==========================================
start_time = time.time()


end_time = time.time()
# ==========================================
# 4. RISULTATO
# ==========================================

print(f"\n[INFO] Pianificazione completata in {end_time - start_time:.2f} secondi.")