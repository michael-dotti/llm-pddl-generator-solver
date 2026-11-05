
# Librerie di sistema e utilità
import time # calcola tempo di esecuzione del programma
import questionary # genera un menu a scelta
from datetime import datetime # per generare timestamp automatici nei file
from dotenv import load_dotenv # per caricare le variabili d'ambiente

# per recuperare il percorso del file
from pathlib import Path

# Caricamento delle variabili d'ambiente dal file .env
load_dotenv()

# Importo le costanti e i metodi di utilità creati da me direttamente da una classe apposita chiamata config.py
from config import (
    MAX_ATTEMPTS, 
    termina_programma
)

# Importo la funzione per inizializzare l'LLM
from llm_factory import initialize_llm

# Importo la funzione per caricare gli appropriati prompt per il dominio
from prompt_manager import get_domain_prompts

# avendo spostato la logica di creazione e validazione del dominio dentro a "pipeline_executor", devo recuperare il metodo, da questa classe, per avviare la pipeline
from pipeline_executor import run_domain_pipeline

# ==========================================
# 1. SELEZIONE A DUE PASSI (CARTELLA -> FILE)
# ==========================================
descriptions_dir = Path("domain_descriptions")

# 1. Trova tutte le sottocartelle all'interno di "domain_descriptions"
folders = [f.name for f in descriptions_dir.iterdir() if f.is_dir() and not f.name.startswith('.')]
if not folders:
    termina_programma(f"[ERRORE] Nessuna sottocartella trovata in '{descriptions_dir}/'.")

# ordina le cartelle alfabeticamente
folders.sort()

# Primo Menù: Selezione della cartella del dominio
selected_folder = questionary.select(
    "Seleziona la cartella del dominio da esplorare:",
    choices=folders
).ask()

# Percorso della cartella scelta
folder_path = descriptions_dir / selected_folder

# 2. Trova tutti i file .txt all'interno della cartella selezionata
available_files = [f.name for f in folder_path.glob("*.txt")]
if not available_files:
    termina_programma(f"[ERRORE] Nessun file .txt trovato nella cartella '{selected_folder}/'.")

available_files.sort()

# Secondo menu: Selezione del file di descrizione specifico (es. v1, v2, v3)
current_domain_file_name = questionary.select(
    f"Seleziona il file di descrizione per '{selected_folder}':",
    choices=available_files
).ask()

# Percorso completo al file di testo selezionato
file_path = folder_path / current_domain_file_name

# Lettura automatica del file di testo
try:
    with open(file_path, "r", encoding="utf-8") as f:
        domain_desc = f.read()
    print(f"\n[OK] Testo del dominio caricato correttamente da: {file_path}\n")
except FileNotFoundError:
    termina_programma(f"[ERRORE] Il file '{file_path}' non è stato trovato. Verifica il nome.")
    domain_desc = ""

# -------------------------------------------------------------
# ESTRAZIONE AUTOMATICA DEL NOME DEL DOMINIO PDDL
# -------------------------------------------------------------
# Es: se il file è "blocksworld_v1.txt", lo stem è "blocksworld_v1"
# Splittando per "_" otteniamo "blocksworld"

file_stem = Path(current_domain_file_name).stem 
suggested_domain_name = file_stem.split('_')[0] 

# Permette all'utente di confermare o modificare al volo il nome del dominio PDDL
domain_name = questionary.text(
    "Conferma o modifica il nome PDDL del dominio:",
    default=suggested_domain_name
).ask()

# -------------------------------------------------------------
# SCELTA MODALITÀ DI NAMING DEL FILE PDDL DI SALVATAGGIO
# -------------------------------------------------------------
naming_mode = questionary.select(
    "Come vuoi gestire il nome del file PDDL del dominio in salvataggio?",
    choices=[
        "Manuale (scelgo io il nome da terminale)",
        f"Automatico (genera nome con timestamp o prefisso: domain_{domain_name}_YYYYMMDD_HHMMSS.pddl)"
    ],
    instruction=""
).ask()



# ==========================================
# 2. INIZIALIZZAZIONE DELL'LLM 
# ==========================================
llm = initialize_llm()


# ==========================================
# 3. CARICAMENTO / GENERAZIONE DEI PROMPT
# ==========================================
custom_types_prompt, custom_predicates_prompt, custom_actions_prompt, custom_revise_prompt = get_domain_prompts(
    selected_folder=selected_folder,
    current_domain_file_name=current_domain_file_name
)

prompts = (custom_types_prompt, custom_predicates_prompt, custom_actions_prompt, custom_revise_prompt)

# ============================================================
# 4. GENERAZIONE INIZIALE DEI COMPONENT DEL FILE DOMAIN.PDDL
# ============================================================

# inizio da qui a contare il tempo impiegato dall'LLM per risolvere il problema.
start_time = time.time()

success, domain_pddl_content, attempts_used, error_msg = run_domain_pipeline(
        llm=llm,
        domain_desc=domain_desc,
        domain_name=domain_name,
        prompts=prompts,
    )
end_time = time.time()

# =======================================================
# 7. RISULTATO FINALE
# =======================================================
if success:
    print(f"\n[OK] Domain PDDL valido e pronto! Generato in {attempts_used} iterazione/i.")
    print("--- ANTEPRIMA DEL FILE DOMAIN.PDDL ---\n")
    print(domain_pddl_content)

    domains_dir = Path("domains")
    domains_dir.mkdir(parents=True, exist_ok=True)  # Crea la cartella se non esiste

    # Controllo in base alla scelta del flag iniziale
    if "Manuale" in naming_mode:
        domain_filename = questionary.text(
            "\nInserisci il nome del file PDDL del dominio:",
            default=f"domain_{domain_name}.pddl"
        ).ask()
        
        # Controllo di sicurezza sull'estensione
        if not domain_filename.endswith(".pddl"):
            domain_filename += ".pddl"
    else:
        # Generazione automatica con timestamp (es. domain_20261015_213000.pddl)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain_filename = f"domain_{timestamp}.pddl"

    filename_output = domains_dir / domain_filename

    with open(filename_output, "w", encoding="utf-8") as f:
        f.write(domain_pddl_content)
        
    print(f"\n[SALVATAGGIO] File scritto correttamente come: '{filename_output}'")
    print(f"\n[TIMER] Tempo totale di esecuzione: {end_time - start_time:.2f} secondi")

else:
    termina_programma(f"\n[FATAL] L'LLM ha fallito la generazione dopo {MAX_ATTEMPTS} tentativi. Ultimi errori: {error_msg}")



