import time 
import re
import questionary 
from datetime import datetime 
from dotenv import load_dotenv 
from pathlib import Path

# Classe per generare i componenti del problema e validare il file problem.pddl generato
from pipeline_executor import run_problem_pipeline


from llm_factory import initialize_llm
from prompt_manager import get_problem_prompts


load_dotenv()

from config import (
    MAX_ATTEMPTS, 
    termina_programma
)

domains_dir = Path("domains")
problem_descriptions_dir = Path("problem_descriptions")

# ============================================
# 1. SELEZIONE DOMAIN.PDDL ESISTENTE
# ============================================

if not domains_dir.exists() or not domains_dir.is_dir():
    termina_programma(f"[ERRORE] La cartella '{domains_dir}/' non esiste.")

available_domains = sorted(
    [f.name for f in domains_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pddl"],
    key=str.lower,
)
if not available_domains:
    termina_programma(f"[ERRORE] Nessun file .pddl trovato in '{domains_dir}/'.")

selected_domain_file = questionary.select(
    "Seleziona il file di dominio PDDL esistente:",
    choices=available_domains,
).ask()
if not selected_domain_file:
    termina_programma("Selezione del dominio annullata dall'utente.")

domain_path = domains_dir / selected_domain_file
domain_content = domain_path.read_text(encoding="utf-8")
print(f"\n[OK] Dominio caricato da: {domain_path}\n")

# ============================================
# 2. SELEZIONE A DUE PASSI (CARTELLA -> FILE)
# ============================================
if not problem_descriptions_dir.exists() or not problem_descriptions_dir.is_dir():
    termina_programma(f"[ERRORE] La cartella '{problem_descriptions_dir}/' non esiste.")

folders = sorted(
    [f.name for f in problem_descriptions_dir.iterdir() if f.is_dir() and not f.name.startswith(".")],
    key=str.lower,
)
if not folders:
    termina_programma(f"[ERRORE] Nessuna sottocartella trovata in '{problem_descriptions_dir}/'.")

selected_folder = questionary.select(
    "Seleziona la cartella del problema da esplorare:",
    choices=folders,
).ask()
if not selected_folder:
    termina_programma("Selezione della cartella annullata dall'utente.")

folder_path = problem_descriptions_dir / selected_folder

available_files = sorted(
    [f.name for f in folder_path.glob("*.txt")],
    key=str.lower,
)
if not available_files:
    termina_programma(f"[ERRORE] Nessun file .txt trovato nella cartella '{selected_folder}/'.")

current_problem_file_name = questionary.select(
    f"Seleziona il file di descrizione del problema per '{selected_folder}':",
    choices=available_files,
).ask()
if not current_problem_file_name:
    termina_programma("Selezione del file di descrizione del problema annullata dall'utente.")

file_path = folder_path / current_problem_file_name
problem_desc = file_path.read_text(encoding="utf-8")
print(f"\n[OK] Testo del problema caricato da: {file_path}\n")

# -------------------------------------------------------------
# SCELTA MODALITÀ DI NAMING DEL FILE PDDL DI SALVATAGGIO
# -------------------------------------------------------------
file_stem = Path(current_problem_file_name).stem

# Ripulisce eventuali caratteri non ideali per un identificatore PDDL
suggested_problem_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", file_stem).strip("_")
if not suggested_problem_name:
    suggested_problem_name = f"problem_{selected_folder}"

problem_name = questionary.text(
    "Conferma o modifica il nome PDDL del problema:",
    default=suggested_problem_name,
).ask()
if problem_name is None or not problem_name.strip():
    termina_programma("Nome del problema non valido o operazione annullata.")
problem_name = problem_name.strip()

# -------------------------------------------------------------
# SCELTA MODALITÀ DI NAMING DEL FILE PDDL DI SALVATAGGIO
# -------------------------------------------------------------
naming_mode = questionary.select(
    "Come vuoi gestire il nome del file PDDL del problema in salvataggio?",
    choices=[
        "Manuale (scelgo io il nome da terminale)",
        f"Automatico (genera nome con timestamp: problem_{problem_name}_YYYYMMDD_HHMMSS.pddl)",
    ],
    instruction="",
).ask()
if not naming_mode:
    termina_programma("Selezione della modalità di salvataggio annullata.")



# ==========================================
# 3. INIZIALIZZAZIONE DELL'LLM 
# ==========================================
llm = initialize_llm()

# ==========================================
# 4. CARICAMENTO / GENERAZIONE DEI PROMPT
# ==========================================
custom_objects_prompt, custom_initial_states_prompt, custom_goal_state_prompt, custom_revise_prompt = get_problem_prompts(
    selected_folder=selected_folder,
    current_domain_file_name=current_problem_file_name
)

prompts = (custom_objects_prompt, custom_initial_states_prompt, custom_goal_state_prompt, custom_revise_prompt)


# ============================================================
# 5. GENERAZIONE DEL PROBLEM.PDDL
# ============================================================
start_time = time.time()
success, problem_pddl_content, attempts_used, error_msg = run_problem_pipeline(
        llm=llm,
        problem_desc=problem_desc,
        problem_name=problem_name,
        domain_content=domain_content,
        prompts=prompts,
    )
end_time = time.time()


# =======================================================
# 6. RISULTATO FINALE
# =======================================================
