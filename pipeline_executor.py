from l2p import DomainBuilder, DomainValidator # fondamentali per generare un file domain.pddl e rilevare evenuali errori
from l2p.feedback_builder import FeedbackBuilder # per correggere eventuali errori nel dominio

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_format import format_types, format_predicates, format_actions 

# Richiamo le mie regole custom per la validazione del dominio (usando @domain_rule)
import custom_rules.domain_rules

from config import (
    MAX_ATTEMPTS 
)

def _generate_initial_components(llm, domain_desc: str, prompts: tuple, domain_builder: DomainBuilder):
    """Metodo privato per la generazione iniziale di Tipi, Predicati e Azioni."""
    prompt_types, prompt_predicates, prompt_actions, _ = prompts

    # Tipi
    try:
        types_results, _ = domain_builder.formalize_component(
            model=llm,
            component_class=PDDLType,
            description=domain_desc,
            prompt_template=prompt_types
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione dei tipi: {e}")

    extracted_types = types_results[PDDLType]
    types_str = format_types(extracted_types)
    print("--- TIPI GENERATI ---\n")
    print(types_str)


    # Predicati
    try:
        predicates_results, _ = domain_builder.formalize_component(
            model=llm,
            component_class=Predicate,   # Specifichiamo di voler estrarre i predicati
            description=domain_desc,     # Usiamo la stessa descrizione
            types=extracted_types,       # Passiamo i tipi all'LLM per garantirne la coerenza
            prompt_template=prompt_predicates
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione dei predicati: {e}")

    extracted_predicates = predicates_results[Predicate] #  Estraiamo la lista dei predicati dal dizionario dei risultati
    predicates_str = format_predicates(extracted_predicates)  # Formattiamo i predicati in sintassi PDDL standard usando le utils della libreria
    print("--- PREDICATI GENERATI ---\n")
    print(predicates_str)


    # Azioni
    try:
        actions_results, _ = domain_builder.formalize_component(
            model=llm,
            component_class=Action,
            description=domain_desc,
            types=extracted_types,
            predicates=extracted_predicates,
            prompt_template=prompt_actions
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione delle azioni: {e}")

    extracted_actions = actions_results[Action]  # Estraiamo la lista delle azioni
    actions_str = format_actions(extracted_actions) # Formattiamo le azioni in sintassi PDDL standard
    print("\n--- AZIONI GENERATE ---")
    print(actions_str)

    return extracted_types, extracted_predicates, extracted_actions, types_str, predicates_str, actions_str


def _build_pddl_content(domain_name: str, types_str: str, predicates_str: str, actions_str: str) -> str:
    """Metodo privato per assemblare la stringa del file PDDL."""
    return f"""(define (domain {domain_name})
  (:requirements :typing :strips :negative-preconditions)

  (:types
{types_str}
  )

  (:predicates
{predicates_str}
  )

{actions_str}
)"""


def _run_self_correction(llm, domain_desc: str, domain_details: DomainDetails, domain_result, 
                         extracted_types, extracted_predicates, extracted_actions, 
                         domain_name: str, prompts: tuple, 
                         domain_validator: DomainValidator, feedback_builder: FeedbackBuilder):
    """Metodo privato che gestisce il ciclo di iterazione e self-correction in caso di errori."""
    
    _, _, _, prompt_revise = prompts
    current_attempt = 1

    while not domain_result.valid and current_attempt <= MAX_ATTEMPTS:
        print(f"\n[ERRORE] Validazione semantica PDDL fallita. Avvio Self-Correction {current_attempt}/{MAX_ATTEMPTS}...")
        print(f"Errori: {domain_result.errors}\n")

        # Fase A: Diagnosi
        diagnosis_result, _ = feedback_builder.llm_diagnose(
            model=llm, artifact=domain_details, errors=domain_result.errors, description=domain_desc
        )

        # Fase B: Filtraggio intelligente dei target da correggere
        error_str = str(domain_result.errors).lower()
        target_classes = []

        if any(keyword in error_str for keyword in ["action", "precondition", "effect", "parameter"]):
            target_classes.append(Action)
        if "predicate" in error_str:
            target_classes.append(Predicate)
        if any(keyword in error_str for keyword in ["type", "object"]):
            target_classes.append(PDDLType)

        if not target_classes:
            target_classes = [PDDLType, Predicate, Action]

        if target_classes == [Action]:
            current_artifact = extracted_actions
        elif target_classes == [Predicate]:
            current_artifact = extracted_predicates
        elif target_classes == [PDDLType]:
            current_artifact = extracted_types
        else:
            current_artifact = domain_details


        # Fase C: Revisione dei componenti tramite LLM
        try:
            revised_results, _ = feedback_builder.llm_revise(
                model=llm,
                artifact=current_artifact,
                component_class=target_classes,
                diagnosis=diagnosis_result,
                description=domain_desc,
                prompt_template=prompt_revise
            )
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(f"Errore durante la revisione dei componenti PDDL: {e}")


        # Aggiornamento componenti
        if PDDLType in revised_results:
            extracted_types = revised_results[PDDLType]
        if Predicate in revised_results:
            extracted_predicates = revised_results[Predicate]
        if Action in revised_results:
            extracted_actions = revised_results[Action]

        types_str = format_types(extracted_types)
        predicates_str = format_predicates(extracted_predicates)
        actions_str = format_actions(extracted_actions)

        # Ricostruzione e validazione
        domain_pddl_content = _build_pddl_content(domain_name, types_str, predicates_str, actions_str)

        domain_details.domain_pddl = domain_pddl_content
        domain_details.types = extracted_types
        domain_details.predicates = extracted_predicates
        domain_details.actions = extracted_actions

        domain_result = domain_validator.validate_domain(domain_details)
        current_attempt += 1

    return domain_result, domain_details, current_attempt



def run_domain_pipeline(llm, domain_desc: str, domain_name: str, prompts: tuple):
    """
    Funzione principale pubblica richiamata dal main.
    Coordina generazione, validazione ed eventuale self-correction.
    restituisce in ordine: True/False (Dominio corretto o meno), contenuto_dominio_in_pddl (se la validazione è passata, altrimenti ""), numero_di_tentativi, (eventuali, altrimenti "") messaggi_di_errore
    """
    print("\n\n[INFO] Inizio Generazione dei componenti del Domain PDDL (Tipi, Predicati, Azioni)")
    
    domain_builder = DomainBuilder()
    feedback_builder = FeedbackBuilder()
    domain_validator = DomainValidator(use_defaults=True) # Inizializza il validatore (user_defaults=True caricherà automaticamente la funzione decorata)

    # 1. Generazione iniziale
    try:
        extracted_types, extracted_predicates, extracted_actions, types_str, predicates_str, actions_str = _generate_initial_components(
            llm, domain_desc, prompts, domain_builder
        )
    except (ValueError, RuntimeError) as e:
        return False, "", 0, f"Errore durante l'estrazione dei componenti: {e}"

    # 2. Costruzione e Prima Validazione
    domain_pddl_content = _build_pddl_content(domain_name, types_str, predicates_str, actions_str)

    domain_details = DomainDetails(
        name=domain_name,
        types=extracted_types,
        predicates=extracted_predicates,
        actions=extracted_actions,
        domain_pddl=domain_pddl_content
    )

    domain_result = domain_validator.validate_domain(domain_details)
    current_attempt = 1

    # 3. Self-Correction (si attiva solo se fallisce)
    if not domain_result.valid:
        try:
            domain_result, domain_details, current_attempt = _run_self_correction(
                llm, domain_desc, domain_details, domain_result,
                extracted_types, extracted_predicates, extracted_actions,
                domain_name, prompts, domain_validator, feedback_builder
            )
        except Exception as e:
            return False, "", current_attempt, str(e)

    # 4. Restituzione del risultato al Main
    if domain_result.valid:
        return True, domain_details.domain_pddl, current_attempt, ""
    else:
        return False, "", MAX_ATTEMPTS, domain_result.errors