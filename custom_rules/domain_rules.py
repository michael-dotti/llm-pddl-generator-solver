from l2p.validators import ValidationRule

def check_max_action_parameters(action) -> list[str]:
    errors = []
    # Controllo sicuro nel caso in cui params sia None o vuoto
    params = getattr(action, "params", None)
    if params and len(params) > 3:
        errors.append(
            f"[CUSTOM ERROR] L'azione '{action.name}' ha {len(params)} parametri. "
            f"Il limite massimo consentito è 3. Riprogetta l'azione o usa controlli di stato intermedi."
        )
    return errors

def get_domain_validation_rules():
    # Restituisce la lista di tutte le regole custom da passare al DomainValidator
    return [
        ValidationRule(target="action", check_func=check_max_action_parameters)
    ]