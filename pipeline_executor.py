from l2p import DomainBuilder, DomainValidator # fondamentali per generare un file domain.pddl e rilevare evenuali errori
from l2p import ProblemBuilder, ProblemValidator
from l2p.feedback_builder import FeedbackBuilder # per correggere eventuali errori nel dominio

# Funzioni di utilità e tipi PDDL
from l2p.utils.pddl_types import DomainDetails, PDDLType, Action, Predicate
from l2p.utils.pddl_types import ProblemDetails, PDDLObject, InitialState, GoalState 
from l2p.utils.pddl_format import format_types, format_predicates, format_actions 
from l2p.utils.pddl_format import format_objects, format_initial_state, format_goal_states

# per estrarre da un file domain.pddl i suoi componenti 
from l2p.utils.pddl_parser import parse_domain_pddl

# Richiamo le mie regole custom per la validazione del dominio (usando @domain_rule)
import custom_rules.domain_rules

from config import (
    MAX_ATTEMPTS 
)


# ========================================================
# METODI PER LA GENERAZIONE DI DOMAIN.PDDL
# ========================================================

def _generate_domain_components(llm, domain_desc: str, prompts: tuple, domain_builder: DomainBuilder):
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


def _build_domain_pddl_content(domain_name: str, types_str: str, predicates_str: str, actions_str: str) -> str:
    """Metodo privato per assemblare la stringa del file PDDL."""

    # Requisiti di base sempre presenti
    requirements = [":typing", ":strips", ":negative-preconditions"]
    
    # Cerco nelle azioni dei costrutti che possano richiedere requisiti aggiuntivi 
    full_actions_text = actions_str.lower()
    
    # se l'LLM ha usato l'uguaglianza, aggiungiamo :equality
    if "=" in full_actions_text or "(=" in full_actions_text:
        if ":equality" not in requirements:
            requirements.append(":equality")

    reqs_formatted = " ".join(requirements)

    return f"""(define (domain {domain_name})
  (:requirements {reqs_formatted})

  (:types
{types_str}
  )

  (:predicates
{predicates_str}
  )

{actions_str}
)"""


def _run_domain_self_correction(llm, domain_desc: str, domain_details: DomainDetails, domain_result, 
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
        domain_pddl_content = _build_domain_pddl_content(domain_name, types_str, predicates_str, actions_str)

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
        extracted_types, extracted_predicates, extracted_actions, types_str, predicates_str, actions_str = _generate_domain_components(
            llm, domain_desc, prompts, domain_builder
        )
    except (ValueError, RuntimeError) as e:
        return False, "", 0, f"Errore durante l'estrazione dei componenti: {e}"

    # 2. Costruzione e Prima Validazione
    domain_pddl_content = _build_domain_pddl_content(domain_name, types_str, predicates_str, actions_str)

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
            domain_result, domain_details, current_attempt = _run_domain_self_correction(
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




# ========================================================
# METODI PER LA GENERAZIONE DI PROBLEM.PDDL
# ========================================================

def _generate_problem_components( llm, problem_desc: str, domain_details: DomainDetails, prompts: tuple, problem_builder: ProblemBuilder):
    """Metodo privato per la generazione iniziale di Oggetti, Stato Iniziale e Goal."""
    prompt_objects, prompt_initial_states, prompt_goal_state, _ = prompts

    domain_types = domain_details.types or []
    domain_predicates = domain_details.predicates or []

    # 1. Oggetti
    try:
        objects_results, _ = problem_builder.formalize_component(
            model=llm,
            component_class=PDDLObject,
            description=problem_desc,
            prompt_template=prompt_objects,
            types=domain_types,
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione degli oggetti: {e}")

    extracted_objects = objects_results[PDDLObject]
    objects_str = format_objects(extracted_objects)
    print("--- OGGETTI GENERATI ---\n")
    print(objects_str)

    # 2. Stato iniziale
    try:
        initial_state_results, _ = problem_builder.formalize_component(
            model=llm,
            component_class=InitialState,
            description=problem_desc,
            prompt_template=prompt_initial_states,
            types=domain_types,
            predicates=domain_predicates,
            objects=extracted_objects,
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione dello stato iniziale: {e}")

    extracted_initialState = initial_state_results[InitialState]
    initialState_str = format_initial_state(extracted_initialState)
    print("--- STATO INIZIALE GENERATO ---\n")
    print(initialState_str)

    # 3. Goal
    try:
        goal_results, _ = problem_builder.formalize_component(
            model=llm,
            component_class=GoalState,
            description=problem_desc,
            prompt_template=prompt_goal_state,
            types=domain_types,
            predicates=domain_predicates,
            objects=extracted_objects,
            initial_state=extracted_initialState,
        )
    except (ValueError, RuntimeError) as e:
        raise RuntimeError(f"Errore durante l'estrazione del goal: {e}")

    extracted_goal = goal_results[GoalState]
    goal_str = format_goal_states(extracted_goal)
    print("\n--- GOAL GENERATO ---")
    print(goal_str)

    return ( extracted_objects, extracted_initialState, extracted_goal, objects_str, initialState_str, goal_str)


def _build_problem_pddl_content( problem_name: str, domain_name: str, objects_str: str, initialState_str: str, goal_str: str) -> str:
    """Metodo privato per assemblare la stringa del file PDDL del problema."""


    return f"""(define (problem {problem_name})
  (:domain {domain_name})

  (:objects
{objects_str}
  )

  (:init
{initialState_str}
  )

  (:goal
{goal_str}
  )
)"""


def _run_problem_self_correction(
    llm,
    problem_desc: str,
    domain_details: DomainDetails,
    problem_details: ProblemDetails,
    problem_result,
    extracted_objects,
    extracted_initialState,
    extracted_goal,
    problem_name: str,
    prompts: tuple,
    problem_validator: ProblemValidator,
    feedback_builder: FeedbackBuilder,
):
    """Metodo privato che gestisce il ciclo di iterazione e self-correction del problema in caso di errori."""

    _, _, _, prompt_revise = prompts
    current_attempt = 1

    while not problem_result.valid and current_attempt <= MAX_ATTEMPTS:
        print(f"\n[ERRORE] Validazione semantica PDDL del problema fallita. Avvio Self-Correction {current_attempt}/{MAX_ATTEMPTS}...")
        print(f"Errori: {problem_result.errors}\n")

        # Fase A: Diagnosi
        diagnosis_result, _ = feedback_builder.llm_diagnose(
            model=llm,
            artifact=problem_details,
            errors=problem_result.errors,
            description=problem_desc,
        )

        # Fase B: Filtraggio intelligente dei target da correggere
        error_str = str(problem_result.errors).lower()
        target_classes = []

        if any(keyword in error_str for keyword in ["object", "type"]):
            target_classes.append(PDDLObject)
        if any(keyword in error_str for keyword in ["init", "initial", "fact", "predicate", "function"]):
            target_classes.append(InitialState)
        if any(keyword in error_str for keyword in ["goal", "condition", "preference"]):
            target_classes.append(GoalState)

        if not target_classes:
            target_classes = [PDDLObject, InitialState, GoalState]

        if target_classes == [PDDLObject]:
            current_artifact = extracted_objects
        elif target_classes == [InitialState]:
            current_artifact = extracted_initialState
        elif target_classes == [GoalState]:
            current_artifact = extracted_goal
        else:
            current_artifact = problem_details

        # Fase C: Revisione dei componenti tramite LLM
        try:
            revised_results, _ = feedback_builder.llm_revise(
                model=llm,
                artifact=current_artifact,
                component_class=target_classes,
                diagnosis=diagnosis_result,
                description=problem_desc,
                prompt_template=prompt_revise,
            )
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(f"Errore durante la revisione dei componenti del problema PDDL: {e}")

        # Aggiornamento componenti
        if PDDLObject in revised_results:
            extracted_objects = revised_results[PDDLObject]
        if InitialState in revised_results:
            extracted_initialState = revised_results[InitialState]
        if GoalState in revised_results:
            extracted_goal = revised_results[GoalState]

        objects_str = format_objects(extracted_objects)
        initialState_str = format_initial_state(extracted_initialState)
        goal_str = format_goal_states(extracted_goal)

        # Ricostruzione e validazione
        problem_pddl_content = _build_problem_pddl_content(
            problem_name, domain_details.name, objects_str, initialState_str, goal_str
        )

        problem_details.problem_pddl = problem_pddl_content
        problem_details.objects = extracted_objects
        problem_details.initial_state = extracted_initialState
        problem_details.goal_state = extracted_goal

        problem_result = problem_validator.validate_problem(problem_details)
        current_attempt += 1

    return problem_result, problem_details, current_attempt


def run_problem_pipeline(llm, problem_desc: str, problem_name: str, domain_content: str, prompts: tuple):
    print("\n\n[INFO] Inizio Generazione dei componenti del Problem PDDL (Object, Stato Iniziale, Goal)")

    domain_details = parse_domain_pddl(domain_content)
    problem_builder = ProblemBuilder(domain_details=domain_details)
    feedback_builder = FeedbackBuilder()
    problem_validator = ProblemValidator(use_defaults=True)


    # 1. Generazione iniziale
    try:
        extracted_objects, extracted_initialState, extracted_goal, objects_str, initialState_str, goal_str = _generate_problem_components(
            llm, problem_desc, domain_details , prompts, problem_builder
        )
    except (ValueError, RuntimeError) as e:
        return False, "", 0, f"Errore durante l'estrazione dei componenti: {e}" 


    # 2. Costruzione e Prima Validazione
    problem_pddl_content = _build_problem_pddl_content(
        problem_name, domain_details.name, objects_str, initialState_str, goal_str
    )

    problem_details = ProblemDetails(
        name=problem_name,
        objects=extracted_objects,
        initial_state=extracted_initialState,
        goal_state=extracted_goal,
        problem_pddl=problem_pddl_content
    )

    problem_result = problem_validator.validate_problem(problem_details)
    current_attempt = 1

    # 3. Self-Correction (si attiva solo se fallisce)
    if not problem_result.valid:
        try:
            problem_result, problem_details, current_attempt = _run_problem_self_correction(
                llm, problem_desc, domain_details, problem_details, problem_result,
                extracted_objects, extracted_initialState, extracted_goal,
                problem_name, prompts, problem_validator, feedback_builder
            )
        except Exception as e:
            return False, "", current_attempt, str(e)

    # 4. Restituzione del risultato al Main
    if problem_result.valid:
        return True, problem_details.problem_pddl, current_attempt, ""
    else:
        return False, "", MAX_ATTEMPTS, problem_result.errors