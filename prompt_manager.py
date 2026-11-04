from pathlib import Path
from l2p import PromptBuilder
from l2p.utils.pddl_prompt import load_custom_template, load_default_template

def get_domain_prompts(selected_folder: str, current_domain_file_name: str):
    """
    In base alla cartella e al file selezionato, restituisce i 4 template necessari:
    1. types
    2. predicates
    3. actions
    4. revise
    
    Se il dominio è 'farm', usa i prompt custom dettagliati.
    Altrimenti, carica i template di default di l2p.
    """
    # Assicuriamoci che la cartella custom_template esista
    Path("custom_template").mkdir(parents=True, exist_ok=True)

    # 1. CASO DOMINIO FARM (Prompt Custom)
    if selected_folder.lower() == "farm" or current_domain_file_name.startswith("farm"):
        print(f"\n[INFO] Caricamento prompt personalizzati per il dominio '{selected_folder}'...")

        # ------------------
        # TIPI
        # ------------------
        # 1. Configurazione base (ruolo, formato e regole generali)
        prompt_types = (
            PromptBuilder()
            .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain types (:types).")
            .set_format("Wrap a VALID JSON ARRAY inside the <types> ... </types> XML tags.")
            .add_rule("CRITICAL LANGUAGE RULE: All type names MUST be written strictly in ITALIAN")
            .add_rule("CRITICAL: Do NOT create inner XML tags like <type>...</type>.")
            .add_rule("CRITICAL: The content inside <types> MUST be ONLY a raw JSON array [ ... ].")
        )

        # 2. Regola opzionale/condizionale: compatibilità con il file di problema 
        # (attivata solo se il dominio in uso include frammenti di problem.pddl)
        if current_domain_file_name == "farm_v1" :
            prompt_types = prompt_types.add_rule("The type name must match the problem file objects")

        # 3. Specifiche di output, vincoli semantici strutturali e task finale
        # Inseriti qui i vincoli più importanti per evitare il "Bias di recenza"
        prompt_types = (prompt_types.add_rule("CRITICAL PDDL RULE: Do NOT include 'object' as a type. 'object' is a reserved PDDL keyword and is implicit. Start your hierarchy directly from user types (parent: 'object').")
            .add_rule("""EXACT OUTPUT FORMAT REQUIRED:
                <types>
                [
                    {"name": "contadino", "parent": "object"},
                    {"name": "campo", "parent": "object"}
                ]
                </types>""")
            .add_rule("Do NOT reuse type names as predicate names.")
            .set_task("Please process the domain description provided."))

        # carico il template personalizzato per i tipi
        prompt_types.save_prompt(filename="custom_template/custom_types_prompt.md")
        custom_prompt_prompt = load_custom_template(filepath="custom_template/custom_types_prompt.md")


        # ------------------
        # PREDICATI
        # ------------------
        # 1. Configurazione base
        prompt_predicates = (
            PromptBuilder()
            .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain predicates (:predicates).")
            .set_format("Wrap a VALID JSON ARRAY inside the <predicates> ... </predicates> XML tags.")
            .add_rule("CRITICAL: Do NOT create inner XML tags like <predicate>...</predicate>.")
            .add_rule("CRITICAL: The content inside <predicates> MUST be ONLY a raw JSON array [ ... ]. Do not use markdown syntax block like ```json.")
            .add_rule("CRITICAL LANGUAGE RULE: All predicate names, descriptions, and type references MUST be strictly in ITALIAN.")
        )

        # 2. Regola opzionale/condizionale: compatibilità con il file di problema 
        if current_domain_file_name == "farm_v1" :
            prompt_predicates = prompt_predicates.add_rule(
                "CRITICAL COMPATIBILITY RULE: Carefully read the Problem file snippet included in the description. "
                "Ensure your predicates match the entities and initial states provided (e.g., how tools or tractor types are defined)."
            )

        # 3. Specifiche di output, vincoli semantici strutturali e task finale
        prompt_predicates = ( prompt_predicates.add_rule("""EXACT OUTPUT FORMAT REQUIRED:
        <predicates>
        [
        {
            "name": "at",
            "params": [
            {"variable": "?x", "type": "contadino"}, 
            {"variable": "?y", "type": "campo"}
            ],
            "desc": "The farmer ?x is at field ?y"
        },
        {
            "name": "innaffiato",
            "params": [
            {"variable": "?c", "type": "campo"}
            ],
            "desc": "Field ?c is watered"
        }
        ]
        </predicates>""")
            .add_rule("CRITICAL: Look at the types provided in the context. DO NOT create unary predicates for concepts that are already defined as types (e.g., do NOT create a predicate named 'campo', 'contadino', etc.).")
            .add_rule("All predicate names must be completely UNIQUE and different from any type name.")
            .set_task("Extract the necessary predicates for the domain.")
        )

        prompt_predicates.save_prompt(filename="custom_template/custom_predicates_prompt.md")
        custom_predicates_prompt = load_custom_template(filepath="custom_template/custom_predicates_prompt.md")

        # ------------------
        # AZIONI
        # ------------------
        # 1. Configurazione base
        prompt_actions = (
            PromptBuilder()
            .set_role("You are an expert PDDL Generator Agent. Your role is to model PDDL domain actions (:actions).")
            .set_format("Wrap a VALID JSON ARRAY inside the <actions> ... </actions> XML tags.")
            .add_rule("CRITICAL: The content inside <actions> MUST be ONLY a raw JSON array [ ... ] containing action objects, NOT raw PDDL code.")
            .add_rule("CRITICAL LANGUAGE RULE: All action names, parameters, descriptions, and type constraints MUST be in ITALIAN.")
            .add_rule("CRITICAL NAMING RULE: Action names must be clean, grammatically correct Italian verbs/phrases. Do NOT create distorted words.")
            )

        # 2. Regola opzionale/condizionale: compatibilità con il file di problema
        if current_domain_file_name == "farm_v1" :
            prompt_actions = prompt_actions.add_rule("CRITICAL COMPATIBILITY: Ensure action parameters and types strictly match the objects and initial state definitions from the Problem file snippet.")

        # 3. Specifiche di output, vincoli semantici strutturali e task finale 
        prompt_actions = ( prompt_actions
            .add_rule("CRITICAL RULE FOR DRIVING (guida-trattore): When a farmer is `a-bordo` of a tractor and drives it, ONLY the tractor changes its position. Do NOT add an independent `at` effect for the farmer at the destination, because they move implicitly while `a-bordo`.")
            .add_rule("CRITICAL VARIABLE MATCHING RULE: Every single variable name (e.g., ?c, ?t) used inside `preconditions` and `effects` MUST be strictly declared in the action's `params` list. Do NOT introduce new variables (like ?c2, ?f1, etc.) inside conditions if they are not defined in `params`.")
            .add_rule("CRITICAL EFFICIENCY RULE: Actions MUST have a MAXIMUM of 3 parameters. Avoid actions with 4 or more parameters. If an operation involves multiple elements, break it down or design stateless intermediate checks instead of cramming everything into a single action parameters list.")
            .add_rule("""EXACT JSON STRUCTURE REQUIRED PER ACTION:
            {
                "name": "action-name",
                "params": [
                    {"variable": "?c", "type": "contadino"},
                    {"variable": "?t", "type": "trattore"}
                ],
                "preconditions": {
                    "conditions": ["(at ?c ?loc)", "(at ?t ?loc)"]
                },
                "effects": {
                    "add": ["(a-bordo ?c ?t)"],
                    "delete": ["(at ?c ?loc)"]
                },
                "desc": "Description of the action"
            }""")
            .set_task("Extract the necessary actions for the domain in JSON format. Ensure the JSON array is fully complete and closed with </actions>.")
        )

        prompt_actions.save_prompt(filename="custom_template/custom_actions_prompt.md")
        custom_actions_prompt = load_custom_template(filepath="custom_template/custom_actions_prompt.md")

        # Costruzione del prompt per la REVISIONE (FeedbackBuilder)
        prompt_revise = (
            PromptBuilder()
            .set_role("You are an expert PDDL Revision Agent. Your job is to fix failed PDDL component generations based on diagnostic feedback and validation errors.")
            .set_format("You MUST output the components wrapped in their exact XML tags using STRICT JSON arrays for ALL components.")
            .add_rule("CRITICAL FORMAT FOR <types>: Must be a VALID JSON ARRAY of objects (e.g., [{'name': '...', 'parent': '...'}]. NEVER write native PDDL text here. Do NOT include 'object' as a type).")
            .add_rule("CRITICAL FORMAT FOR <predicates>: Must be a VALID JSON ARRAY of objects with keys 'name', 'params' (containing a list of objects with 'variable' and 'type'), and 'desc'.")
            .add_rule("CRITICAL FORMAT FOR <actions>: Must be a VALID JSON ARRAY of action objects matching the expected schema (with 'name', 'params', 'preconditions', and 'effects'). NEVER write raw PDDL like '(:action ...)' inside <actions>.")
            .add_rule("CRITICAL VARIABLE MATCHING RULE: Every single variable name (like ?c, ?t, ?l, ?a, ?s) used inside preconditions and effects MUST be explicitly present in the action's 'params' list. NEVER use a variable in conditions/effects that is not declared in 'params'. If you need a variable, declare it in 'params' first.")
            .add_rule("""EXACT JSON STRUCTURE REQUIRED FOR ACTIONS IN <actions>:
            {
                "name": "action-name",
                "params": [
                    {"variable": "?c", "type": "contadino"},
                    {"variable": "?t", "type": "trattore"}
                ],
                "preconditions": {
                    "conditions": ["(predicate-name ?c ?t)"]
                },
                "effects": {
                    "add": ["(predicate-name ?c ?t)"],
                    "delete": ["(predicate-name ?c)"]
                },
                "desc": "Description"
            }""")
            .add_rule("CRITICAL PDDL RULE: Types and Predicates CANNOT share the same names. Every variable used in preconditions and effects MUST be declared in the action's parameters list.")
            .add_rule("Output ONLY the requested XML blocks containing valid JSON arrays. No conversational text, explanations, or markdown code blocks outside the XML tags.")
            .set_task("Revise the following PDDL component(s) based on the diagnostic feedback and errors provided below.\n{context}")
        )

        prompt_revise.save_prompt(filename="custom_template/custom_revise_prompt.md")
        custom_revise_prompt = load_custom_template(filepath="custom_template/custom_revise_prompt.md")

        return custom_prompt_prompt, custom_predicates_prompt, custom_actions_prompt, custom_revise_prompt
    #
    # 2. CASO ALTRI DOMINI (Blocksworld, Elevators, Gripper, ecc. -> Template di Default l2p)
    else:
        print(f"\n[INFO] Caricamento template di default di l2p per il dominio '{selected_folder}'...")
        
        default_types = load_default_template("domain", "prompt_types.md")
        default_predicates = load_default_template("domain", "prompt_predicates.md")
        default_actions = load_default_template("domain", "prompt_actions.md")
        default_revise = load_default_template("feedback", "prompt_revise.md")

        return default_types, default_predicates, default_actions, default_revise