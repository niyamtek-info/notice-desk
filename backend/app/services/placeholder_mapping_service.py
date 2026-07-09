from functools import lru_cache
import json
from pathlib import Path


MAPPING_PATH = Path(__file__).resolve().parents[1] / "metatable" / "placeholder_mapping.json"


@lru_cache(maxsize=1)
def load_placeholder_mapping() -> dict:
    if not MAPPING_PATH.exists():
        return {
            "report_fields": [],
            "notice_template_aliases": [],
            "notice_party_mappings": [],
        }

    with MAPPING_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle) or {
            "report_fields": [],
            "notice_template_aliases": [],
            "notice_party_mappings": [],
        }


def get_report_fields() -> list[dict]:
    mapping = load_placeholder_mapping()
    fields = mapping.get("report_fields", [])
    return fields if isinstance(fields, list) else []


def get_placeholder_aliases() -> list[dict]:
    mapping = load_placeholder_mapping()
    aliases = mapping.get("notice_template_aliases", [])
    return aliases if isinstance(aliases, list) else []


def get_notice_template_aliases() -> list[dict]:
    mapping = load_placeholder_mapping()
    aliases = mapping.get("notice_template_aliases", [])
    return aliases if isinstance(aliases, list) else []


def get_notice_party_mappings() -> list[dict]:
    mapping = load_placeholder_mapping()
    parties = mapping.get("notice_party_mappings", [])
    return parties if isinstance(parties, list) else []


def get_placeholder_mapping_lookup() -> dict:
    """
    Return the raw placeholder mapping as a dict keyed by section name.

    This keeps the JSON file as the single source of truth while letting
    services consume only the section they need.
    """
    mapping = load_placeholder_mapping()
    return mapping if isinstance(mapping, dict) else {}
