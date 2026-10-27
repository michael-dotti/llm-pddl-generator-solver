from l2p.validators import domain_rule #  decoratore nativo di l2p

# quando domainValidator() ha come parametro use_defaults=True, carica in
# automatico tutte le regole @domain_rule
@domain_rule
def check_max_action_parameters(action) -> list[str]:
    """
    Regola custom per verificare che nessuna azione superi i 3 parametri.
    """
    errors = []
    # Recupero parametri (restituisce lista vuota se manca o è None)
    params = getattr(action, "params", []) or []
    
    if len(params) > 3:
        errors.append(
            f"[CUSTOM ERROR] L'azione '{getattr(action, 'name', 'unknown')}' ha {len(params)} parametri. "
            f"Il limite massimo consentito è 3. Riprogetta l'azione o usa controlli di stato intermedi."
        )
    return errors