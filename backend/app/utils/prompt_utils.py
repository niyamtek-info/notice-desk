import yaml
import os
from app.core.settings import settings

BASE_DIR = settings.BASE_DIR

def load_prompt(doc_type: str) -> str:
    """
    Loads a prompt file based on doc_type.
    """
    if not doc_type:
        return None

    raw = str(doc_type).strip()
    normalized = _normalize_doc_type_name(raw)
    candidates = []

    for candidate in (
        raw,
        raw.replace(" ", "_"),
        raw.lower().replace(" ", "_"),
        raw.lower().replace("_", " "),
        normalized,
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    # Keep compatibility with both the old and new naming conventions.
    alias_map = {
        "sales_deed": ["sale_deed", "Sale_Deed", "Sales_Deed", "sale deed", "Sales Deed"],
        "sale_deed": ["sales_deed", "Sale_Deed", "Sales_Deed", "sale deed", "Sales Deed"],
        "legal_report": ["LegalReport", "Legal Report", "legalreport", "legal report"],
        "legalreport": ["LegalReport", "Legal Report", "legal_report", "legal report"],
        "memorandum_of_deposit_of_title_deed": [
            "Memorandum_of_Deposit_of_Title_Deeds",
            "Memorandum_of_Deposit_of_Title_Deed",
            "memorandum_of_deposit_of_title_deeds",
        ],
        "memorandum_of_deposit_of_title_deeds": [
            "Memorandum_of_Deposit_of_Title_Deed",
            "Memorandum_of_Deposit_of_Title_Deeds",
            "memorandum_of_deposit_of_title_deed",
        ],
    }
    for alias in alias_map.get(normalized, []):
        if alias and alias not in candidates:
            candidates.append(alias)

    for candidate in candidates:
        path = os.path.join(settings.PROMPT_DIR, f"{candidate}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

    return None


def _normalize_doc_type_name(doc_type: str) -> str:
    if not doc_type:
        return ""
    normalized = doc_type.strip().lower().replace(" ", "_")
    if normalized == "sales_deed":
        return "sale_deed"
    if normalized == "memorandum_of_deposit_of_title_deed":
        return "memorandum_of_deposit_of_title_deeds"
    return normalized

def extract_required_field_names(fields):
    required_fields = []

    for field in fields:
        if field.get("required"):
            if field["type"] == "object" and "properties" in field:
                # For nested object, just include top-level key
                required_fields.append(field["name"])
            else:
                required_fields.append(field["name"])
    return required_fields

def load_prompt_and_schema(doc_type: str, return_fields: bool = False):
    yaml_path = os.path.join(BASE_DIR, "app", "metatable", "document_types.yaml")

    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"YAML file not found at: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    target_name = _normalize_doc_type_name(doc_type)
    for item in data.get("DocumentType", []):
        name = item.get("Name", "")
        normalized_name = _normalize_doc_type_name(name)
        if normalized_name == target_name or normalized_name.replace("_", "") == target_name.replace("_", ""):
            prompt = item.get("PromptTemplate", "")
            fields = item.get("Fields", [])

            if return_fields:
                return prompt, fields

            required_fields = extract_required_field_names(fields)
            return prompt, required_fields

        if target_name in {"memorandum_of_deposit_of_title_deeds", "memorandum_of_deposit_of_title_deed"} and normalized_name in {"memorandum_of_deposit_of_title_deeds", "memorandum_of_deposit_of_title_deed"}:
            prompt = item.get("PromptTemplate", "")
            fields = item.get("Fields", [])

            if return_fields:
                return prompt, fields

            required_fields = extract_required_field_names(fields)
            return prompt, required_fields

    return None, None
