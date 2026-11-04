# Moduli fondamentali per la gestione di LLM e PDDL
from l2p import DomainBuilder, UnifiedLLM, OPENAI, DomainValidator # fondamentali per generare un file domain.pddl e rilevare evenuali errori
from l2p.feedback_builder import FeedbackBuilder # per correggere eventuali errori nel dominio
from l2p.prompt_builder import PromptBuilder # per aiutare LLM nel comprendere come eseguire correttamente il suo compito

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_format import format_types, format_predicates, format_actions
from l2p.utils.pddl_prompt import load_custom_template, load_default_template # per caricare i template custom o quelli di default di l2p (legati a PromptBuilder)

# Librerie di sistema e utilità
import time # calcola tempo di esecuzione del programma
import questionary # genera un menu a scelta
from datetime import datetime # per generare timestamp automatici nei file
from dotenv import load_dotenv # per caricare le variabili d'ambiente

# per recuperare il percorso del file
from pathlib import Path

# Importo le classi wrapper per utilizzare gli llm in cloud con l2p
from WrapperClass.OpenRouterLLMWrapper import OpenRouterLLMWrapper

# Richiamo le mie regole custom per la validazione del dominio
import custom_rules.domain_rules

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

# ============================================================
# 4. GENERAZIONE INIZIALE DEI COMPONENT DEL FILE DOMAIN.PDDL
# ============================================================
print("\n\n[INFO] Inizio Generazione dei componenti del Domain PDDL (Tipi, Predicati, Azioni)")
# istanzio le classi necessarie
# istanza del DomainBuilder: classe che permette di creare a partire da una descrizione in linguaggio umano il dominio del problema PDDL
domain_builder = DomainBuilder()

# Istanza del FeedbackBuilder
feedback_builder = FeedbackBuilder()


# inizio da qui a contare il tempo impiegato dall'LLM per risolvere il problema.
start_time = time.time()

# Tipi
try:
    types_results, llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=PDDLType,
        description=domain_desc,
        prompt_template=custom_types_prompt
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione dei tipi: {e}")

extracted_types = types_results[PDDLType]
types_str = format_types(extracted_types)
print("--- TIPI GENERATI ---\n")
print(types_str)  # stampa i tipi estratti dall'LLM

# Predicati
try:
    predicates_results, predicates_llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=Predicate,   # Specifichiamo di voler estrarre i predicati
        description=domain_desc,     # Usiamo la stessa descrizione
        types=extracted_types,        # Passiamo i tipi all'LLM per garantirne la coerenza
        prompt_template=custom_predicates_prompt
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione dei predicati: {e}")

extracted_predicates = predicates_results[Predicate] #  Estraiamo la lista dei predicati dal dizionario dei risultati
predicates_str = format_predicates(extracted_predicates)  # Formattiamo i predicati in sintassi PDDL standard usando le utils della libreria
print("--- PREDICATI GENERATI ---\n")
print(predicates_str)

# Azioni
try:
    actions_results, actions_llm_output = domain_builder.formalize_component(
        model=llm,
        component_class=Action,
        description=domain_desc,
        types=extracted_types,
        predicates=extracted_predicates,
        prompt_template=custom_actions_prompt
    )
except (ValueError, RuntimeError) as e:
    termina_programma(f"Errore durante l'estrazione delle azioni: {e}")

extracted_actions = actions_results[Action]  # Estraiamo la lista delle azioni
actions_str = format_actions(extracted_actions) # Formattiamo le azioni in sintassi PDDL standard
print("\n--- AZIONI GENERATE ---")
print(actions_str)


# =======================================================
# 5. PRIMA COSTRUZIONE E VALIDAZIONE
# =======================================================
# Costruisco il contenuto del file
domain_pddl_content = f"""(define (domain {domain_name})
  (:requirements :typing :strips :negative-preconditions)

  (:types
{types_str}
  )

  (:predicates
{predicates_str}
  )

{actions_str}
)"""

domain_details = DomainDetails(
    name=domain_name,
    types=extracted_types,
    predicates=extracted_predicates,
    actions=extracted_actions,
    domain_pddl=domain_pddl_content
)



# Inizializza il validatore (user_defaults=True caricherà automaticamente la funzione decorata)
domain_validator = DomainValidator(use_defaults=True)
domain_result = domain_validator.validate_domain(domain_details)

# =======================================================
# 6. CICLO DI SELF-CORRECTION (Si attiva SOLO se fallisce)
# =======================================================
current_attempt = 1

while not domain_result.valid and current_attempt <= MAX_ATTEMPTS:
    print(f"\n[ERRORE] Validazione semantica PDDL fallita. Avvio Self-Correction {current_attempt}/{MAX_ATTEMPTS}...")
    print(f"Errori: {domain_result.errors}\n")

    # Fase A: Diagnosi dell'errore PDDL
    diagnosis_result, raw_text_diag = feedback_builder.llm_diagnose(
        model=llm,
        artifact=domain_details,
        errors=domain_result.errors,
        description=domain_desc
    )

    # Fase B: Analizziamo gli errori per costruire una lista cumulativa dei componenti da correggere
    # in questo modo, faremo correggere all'LLM solo i componenti dove è contenuto l'errore
    error_str = str(domain_result.errors).lower()
    target_classes = []


   # 1. Raccogliamo i componenti da correggere in base alle parole chiave nell'errore
    if "action" in error_str or "precondition" in error_str or "effect" in error_str or "parameter" in error_str:
        target_classes.append(Action)
            
    if "predicate" in error_str:
        target_classes.append(Predicate)
            
    if "type" in error_str or "object" in error_str:
        target_classes.append(PDDLType)

    # 2. Fallback di sicurezza: se nessun filtro ha intercettato parole chiave
    # può succedere quando ci sono errori di validazione incrociata o errori geenrati da regole custom i cui messaggi non contengono nessuna di queste parole. 
    if not target_classes:
        target_classes = [PDDLType, Predicate, Action]

    # Scegliamo l'artifact specifico in base al target, oppure usiamo domain_details se misto
    if target_classes == [Action]:
        current_artifact = extracted_actions
    elif target_classes == [Predicate]:
        current_artifact = extracted_predicates
    elif target_classes == [PDDLType]:
        current_artifact = extracted_types
    else:
        current_artifact = domain_details

    # Fase C: Revisione intelligente dei componenti
    # (Qui max_retries interverrà automaticamente se sbaglia l'XML)
    try:
        revised_results, raw_text_rev = feedback_builder.llm_revise(
            model=llm,
            artifact=current_artifact,
            component_class=target_classes,
            diagnosis=diagnosis_result,
            description=domain_desc,
            prompt_template=custom_revise_prompt
        )
    except (ValueError, RuntimeError) as e:
        termina_programma(f"Errore durante la revisione dei componenti PDDL: {e}")

    
    # Aggiorna i componenti corretti
    if PDDLType in revised_results:
        extracted_types = revised_results[PDDLType]
    if Predicate in revised_results:
        extracted_predicates = revised_results[Predicate]
    if Action in revised_results:
        extracted_actions = revised_results[Action]

    types_str = format_types(extracted_types)
    predicates_str = format_predicates(extracted_predicates)
    actions_str = format_actions(extracted_actions)
    
    # Ricostruisci il file PDDL con i componenti aggiornati
    domain_pddl_content = f"""(define (domain {domain_name})
        (:requirements :typing :strips :negative-preconditions)

        (:types
        {types_str}
        )

        (:predicates
        {predicates_str}
        )

        {actions_str}
        )"""

    domain_details.domain_pddl = domain_pddl_content
    domain_details.types = extracted_types
    domain_details.predicates = extracted_predicates
    domain_details.actions = extracted_actions

    # Determinare se il dominio e' corretto o se e' necessario correggerlo nuovamente
    domain_result = domain_validator.validate_domain(domain_details)
    current_attempt += 1


# =======================================================
# 7. RISULTATO FINALE
# =======================================================
if domain_result.valid:
    print(f"\n[OK] Domain PDDL valido e pronto! Generato in {current_attempt} iterazione/i.")
    print("--- ANTEPRIMA DEL FILE DOMAIN.PDDL ---\n")
    print(domain_pddl_content)

    domains_dir = Path("domains")
    domains_dir.mkdir(parents=True, exist_ok=True)  # Crea la cartella se non esiste

    # Controllo in base alla scelta del flag iniziale
    if "Manuale" in naming_mode:
        domain_filename = questionary.text(
            "/nInserisci il nome del file PDDL del dominio:",
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
else:
    termina_programma(f"\n[FATAL] L'LLM ha fallito la generazione dopo {MAX_ATTEMPTS} tentativi. Ultimi errori: {domain_result.errors}")

end_time = time.time()
print(f"\n[TIMER] Tempo totale di esecuzione: {end_time - start_time:.2f} secondi")
