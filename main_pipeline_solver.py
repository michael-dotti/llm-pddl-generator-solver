# Fasi sviluppo main_pipeline_solver: 
# 1) versione 0.1: l'utente può selezionare un domain.pddl e problem.pddl tra quelli esistenti
# 2) versione 0.5 :l'utente può dare in pasto a un planner i domain.pddl e problem.pddl scelti per risolvere il problema
# 3) versione 1 : il sistema chiederà se selezionare un domain.pddl e/o problem.pddl esistenti o se generarli al momento

import os
import re # libreria per cercare, verificare, estrarre o sostituire parti di testo seguendo un pattern
import tempfile
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
from prompt_manager import get_domain_prompts, get_problem_prompts
from pipeline_executor import run_domain_pipeline, run_problem_pipeline

def _select_pddl_file(target_dir: Path, file_type: str) -> Path:
    """Funzione helper privata per gestire la scansione e scelta del file (domain.pddl o problem.pddl) tramite questionary."""

    # verifico che la cartella esista
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"La cartella '{target_dir}' non esiste o non è una directory.")

    # ordino i file
    files = sorted(
        [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pddl'],
        key=str.lower
    )

    # controllo che esistano file nella cartella selezionata, altrimenti generò un'eccezione.
    if not files:
        raise ValueError(f"Nessun file .pddl trovato nella cartella '{target_dir.name}'.")

    # seleziono 
    selected = questionary.select(
        f"Seleziona il file di {file_type} PDDL da utilizzare:",
        choices=files
    ).ask()

    if not selected:
        raise KeyboardInterrupt(f"Selezione del {file_type.lower()} interrotta dall'utente.")

    return target_dir / selected


def _select_description_file(descriptions_dir: Path, label: str) -> tuple[str, Path]:
    """Selezione a due passi (sottocartella -> file .txt) e lettura del testo descrittivo (per generare il dominio o il problema)."""
    
    # Verifico che la cartella esista (domains_descriptions o problem_description a seconda del valore assunto dal parametro 'description_dir')
    if not descriptions_dir.exists() or not descriptions_dir.is_dir():
        raise FileNotFoundError(
            f"La cartella '{descriptions_dir}' non esiste o non è una directory."
        )

    folders = sorted(
        [
            f.name
            for f in descriptions_dir.iterdir()
            if f.is_dir() and not f.name.startswith(".")
        ],
        key=str.lower,
    )
    if not folders:
        raise ValueError(
            f"Nessuna sottocartella trovata in '{descriptions_dir}/'."
        )

    # seleziono la cartella da esplorare
    selected_folder = questionary.select(
        f"Seleziona la cartella del {label} da esplorare:",
        choices=folders,
    ).ask()
    if not selected_folder:
        raise KeyboardInterrupt(
            f"Selezione della cartella per {label} interrotta dall'utente."
        )

    folder_path = descriptions_dir / selected_folder
    available_files = sorted(
        [f.name for f in folder_path.glob("*.txt")],
        key=str.lower,
    )
    if not available_files:
        raise ValueError(
            f"Nessun file .txt trovato nella cartella '{selected_folder}/'."
        )

    # seleziono uno dei file contenuti nella cartella
    selected_file_name = questionary.select(
        f"Seleziona il file di descrizione per '{selected_folder}':",
        choices=available_files,
    ).ask()
    if not selected_file_name:
        raise KeyboardInterrupt(
            f"Selezione del file di descrizione per {label} interrotta dall'utente."
        )

    file_path = folder_path / selected_file_name
    description_text = file_path.read_text(encoding="utf-8")
    print(f"\n[OK] Testo del {label} caricato correttamente da: {file_path}\n")
    return description_text, file_path


def _ask_name(prompt: str, default: str, label: str) -> str:
    """Chiede all'utente un nome testuale da terminale"""
    value = questionary.text(
        prompt,
        default=default,
        validate=lambda text: True if text.strip() else f"Il nome del {label} non può essere vuoto.",
    ).ask()
    if not value:
        raise KeyboardInterrupt(f"Inserimento del nome {label} interrotto dall'utente.")
    return value.strip()


def _save_pddl(out_dir: Path, prefix: str, base_name: str, content: str) -> Path:
    """Salva su disco il contenuto PDDL generato e restituisce il percorso del file creato"""
    out_dir.mkdir(parents=True, exist_ok=True)
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", base_name.lower()).strip("_") or prefix
    path = out_dir / f"{prefix}_{clean}.pddl"
    path.write_text(content, encoding="utf-8")
    print(f"[SALVATAGGIO] {prefix.capitalize()} salvato in: '{path}'")
    return path


def _extract_plan_actions(raw_output: str, plan_file_path: Path | None = None) -> list[str]:
    """ """
    # 1. Se il file temporaneo del piano esiste ed è non vuoto, leggiamo da lì
    if plan_file_path and plan_file_path.exists():
        lines = [
            line.strip()
            for line in plan_file_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith(";")
        ]
        if lines:
            return lines

    # 2. Altrimenti estraiamo le azioni da raw_output ignorando le righe di log (es. INFO ...)
    matches = re.findall(
        r"^(?!INFO\b)[a-zA-Z0-9_-]+(?:\s+[a-zA-Z0-9_-]+)*\s+\(\d+\)$",
        raw_output,
        re.MULTILINE,
    )
    return [f"({m.rsplit('(', 1)[0].strip()})" for m in matches]

# Creiamo un percorso temporaneo per --plan-file così non sporca la cartella con "sas_plan"
tmp_plan_file = tempfile.NamedTemporaryFile(prefix="fd_plan_", delete=False)
tmp_plan_path = Path(tmp_plan_file.name)
tmp_plan_file.close()


domains_dir = Path("domains")
problems_dir = Path("problems")

domain_descriptions_dir = Path("domain_descriptions")
problem_descriptions_dir = Path("problem_descriptions")

# ==========================================
# 1. SELEZIONE DEL DOMAIN.PDDL e PROBLEM.PDDL 
# ==========================================
print("=== PDDL Solver Pipeline (v1.0) ===\n")

try:

    # --------------------------------------
    # 1. GENERAZIONE O CARICAMENTO DOMINIO 
    # -------------------------------------
    want_gen_domain = questionary.confirm(
        "Vuoi generare un nuovo Domain PDDL?", default=False
    ).ask()
    if want_gen_domain is None:
        raise KeyboardInterrupt("Operazione interrotta dall'utente.")

    if want_gen_domain:
        llm = initialize_llm()
        domain_desc, _ = _select_description_file(domain_descriptions_dir, "dominio")
        domain_name = _ask_name("Inserisci il nome del dominio (es. CAMPI):", "CAMPI", "dominio")

        ok, domain_content, iters, err = run_domain_pipeline(
            llm=llm,
            domain_desc=domain_desc,
            domain_name=domain_name,
            prompts=get_domain_prompts(),
        )
        if not ok or not domain_content:
            raise RuntimeError(f"Generazione del dominio fallita dopo {iters} iterazioni: {err}")

        domain_path = _save_pddl(domains_dir, "domain", domain_name, domain_content)
    else:
        domain_path = _select_pddl_file(domains_dir, "Domain")
        domain_content = domain_path.read_text(encoding="utf-8")


    # --------------------------------------
    # 2. GENERAZIONE O CARICAMENTO PROBLEMA 
    # -------------------------------------
    want_gen_problem = questionary.confirm(
        "Vuoi generare un nuovo Problem PDDL sul dominio attivo?", default=False
    ).ask()
    if want_gen_problem is None:
        raise KeyboardInterrupt("Operazione interrotta dall'utente.")

    if want_gen_problem:
        if llm is None:
            llm = initialize_llm()
        problem_desc, _ = _select_description_file(problem_descriptions_dir, "problema")
        problem_name = _ask_name("Inserisci il nome del problema (es. farm_v1):", "problem_v1", "problema")

        ok, problem_content, iters, err = run_problem_pipeline(
            llm=llm,
            problem_desc=problem_desc,
            problem_name=problem_name,
            domain_content=domain_content,
            prompts=get_problem_prompts(),
        )
        if not ok or not problem_content:
            raise RuntimeError(f"Generazione del problema fallita dopo {iters} iterazioni: {err}")

        problem_path = _save_pddl(problems_dir, "problem", problem_name, problem_content)
    else:
        problem_path = _select_pddl_file(problems_dir, "Problem")

except (FileNotFoundError, ValueError, RuntimeError, KeyboardInterrupt) as e:
    tmp_plan_path.unlink(missing_ok=True) # cancella il file temporaneo se il programma si interrompe a causa di un'eccezione
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
        timeout=60,
        custom_args=["--search", "eager_greedy([ff()])"],
    )

    if result.is_successful:
        default_plan_path = Path("sas_plan")
        plan_source = default_plan_path if default_plan_path.exists() else tmp_plan_path
        result.plan = _extract_plan_actions(result.raw_output or "", plan_source)

except Exception as e:
    termina_programma(f"Errore durante l'esecuzione di Fast Downward: {e}")
finally:
    for temp_file in (tmp_plan_path, Path("sas_plan"), Path("output.sas")):
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
end_time = time.time()



# ==========================================
# 4. RISULTATO
# ==========================================
elapsed = end_time - start_time
print(f"\n[INFO] Pianificazione completata in {elapsed:.2f} secondi.")

if result.is_successful:
    print("\n✅ Piano trovato:")
    solutions_dir.mkdir(parents=True, exist_ok=True)

    if result.plan:
        for step_idx, action in enumerate(result.plan, start=1):
            print(f"  {step_idx}. {action}")

        plan_lines = [action.strip() for action in result.plan]
        plan_content = "\n".join(plan_lines) + "\n"
    else:
        print("  (Nessuna azione necessaria: stato iniziale già conforme all'obiettivo)")
        plan_content = "; Nessuna azione necessaria: stato iniziale già conforme all'obiettivo.\n"

    with open(solution_output_path, "w", encoding="utf-8") as f:
        f.write(plan_content)

    print(f"\n[SALVATAGGIO] Soluzione salvata correttamente in: '{solution_output_path}'")

else:
    print("\n❌ Il planner non ha trovato una soluzione.")
    if result.error_message:
        print(f"Dettaglio errore: {result.error_message}")