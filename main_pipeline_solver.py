# Fasi sviluppo main_pipeline_solver: 
# 1) versione 0.1: l'utente può selezionare un domain.pddl e problem.pddl tra quelli esistenti
# 2) versione 0.5 :l'utente può dare in pasto a un planner i domain.pddl e problem.pddl scelti per risolvere il problema
# 3) versione 1 : il sistema chiederà se selezionare un domain.pddl e/o problem.pddl esistenti o se generarli al momento

import os
import time 
import questionary 
from datetime import datetime 
from dotenv import load_dotenv
from pathlib import Path

# Importo le classi per utilizzare i planner. 
from l2p.planner_builder import FastDownward, PlanningResult

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

    files = sorted(
        [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pddl'],
        key=str.lower
    )

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


# ======================================================================
# 2. SCELTA NOME DEL FILE CHE CONTERRA' LA SOLUZIONE AL PROBLEMA (PIANO)
# ======================================================================

# -------------------------------------------------------------
# ESTRAZIONE AUTOMATICA DEL NOME SUGGERITO PER LA SOLUZIONE
# -------------------------------------------------------------
# Es: se il problema è "dieci_campi_v1.pddl", lo stem è "dieci_campi_v1"
problem_stem = Path(problem_path).stem # rimuove l'estensione
suggested_solution_name = problem_stem.removeprefix("problem_") # rimuove la parola iniziale "problem_"


solution_base_name = questionary.text(
    "Conferma o modifica il nome base per il file contenente il piano:",
    default=suggested_solution_name
).ask()

# -------------------------------------------------------------
# SCELTA MODALITÀ DI NAMING DEL FILE CONTENENTE IL PIANO
# -------------------------------------------------------------
solution_naming_mode = questionary.select(
    "Come vuoi gestire il nome del file contenente il piano?",
    choices=[
        "Manuale (scelgo io il nome da terminale)",
        f"Automatico (genera nome con timestamp: solution_{solution_base_name}_YYYYMMDD_HHMMSS.txt)"
    ],
    instruction=""
).ask()

if "Manuale" in solution_naming_mode:
    solution_filename = questionary.text(
        "Inserisci il nome del file della soluzione:",
        default=f"solution_{solution_base_name}.txt"
    ).ask()

    if not solution_filename.endswith((".txt", ".plan")):
        solution_filename += ".txt"
else:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    solution_filename = f"solution_{solution_base_name}_{timestamp}.txt"

solutions_dir = Path("solutions")
solution_output_path = solutions_dir / solution_filename


# ==========================================
# 3. UTILIZZO DEL PLANNER PER RISOLVERE IL PROBLEMA
# ==========================================

# Recupero il percorso dell'eseguibile di Fast Downward dal file .env
fd_executable = os.getenv("FAST_DOWNWARD_PATH") 
if not fd_executable or not Path(fd_executable).exists():
    termina_programma("Percorso di Fast Downward non configurato o non valido (controlla FAST_DOWNWARD_PATH).")

# Istanzio il wrapper del planner Fast Downward
planner = FastDownward(executable_path=fd_executable, cleanup_temp_files=True)

start_time = time.time()
try:
    result: PlanningResult = planner.run_planner(
        domain_path=str(domain_path),
        problem_path=str(problem_path),
        timeout=60
    )
except Exception as e:
    termina_programma(f"Errore durante l'esecuzione di Fast Downward: {e}")
end_time = time.time()
# ==========================================
# 4. RISULTATO
# ==========================================
elapsed = end_time - start_time
print(f"\n[INFO] Pianificazione completata in {elapsed:.2f} secondi.")

if result.is_successful:
    print("\n✅ Piano trovato:")
    if result.plan:
        for step_idx, action in enumerate(result.plan, start=1):
            print(f"  {step_idx}. {action}")
    else:
        print("  (Nessuna azione necessaria: stato iniziale già conforme all'obiettivo)")

    # Salvataggio automatico in solutions/
    solutions_dir.mkdir(parents=True, exist_ok=True)

    if result.plan:
        plan_lines = [action.strip() for action in result.plan]
        plan_content = "\n".join(plan_lines) + "\n"
    else:
        plan_content = "; Nessuna azione necessaria: stato iniziale già conforme all'obiettivo.\n"

    with open(solution_output_path, "w", encoding="utf-8") as f:
        f.write(plan_content)

    print(f"\n[SALVATAGGIO] Soluzione salvata correttamente in: '{solution_output_path}'")

else:
    print("\n❌ Il planner non ha trovato una soluzione.")
    if result.error_message:
        print(f"Dettaglio errore: {result.error_message}")