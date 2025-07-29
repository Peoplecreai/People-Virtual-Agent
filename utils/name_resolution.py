from tools.sheets import get_user_record, get_preferred_name as sheets_get_preferred_name
from utils.slack_utils import get_slack_name

_name_cache = {}

def _nk(s: str) -> str:
    """Normaliza nombres de columnas: minúsculas y alfanumérico."""
    return "".join(ch for ch in s.lower() if ch.isalnum())

def get_preferred_name(slack_id):
    """Devuelve Name (pref) o Name (first) desde Sheets."""
    row = get_user_record(slack_id)
    if not row:
        return None
    # intenta claves típicas
    if isinstance(row.get("Name (pref)"), str) and row["Name (pref)"].strip():
        return row["Name (pref)"].strip()
    if isinstance(row.get("Name (first)"), str) and row["Name (first)"].strip():
        return row["Name (first)"].strip()
    # intenta variantes normalizadas
    rn = { _nk(k): v for k, v in row.items() }
    pref = rn.get("namepref")
    first = rn.get("namefirst") or rn.get("firstname")
    if isinstance(pref, str) and pref.strip():
        return pref.strip()
    if isinstance(first, str) and first.strip():
        return first.strip()
    return None

def resolve_name(slack_id):
    if slack_id in _name_cache:
        return _name_cache[slack_id]
    name = get_slack_name(slack_id)     # rápido
    pref = get_preferred_name(slack_id) # si hay en Sheet, sobrescribe
    if pref:
        name = pref
    if name:
        _name_cache[slack_id] = name
    return name
