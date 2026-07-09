from datetime import datetime, date
import pandas as pd

def parse_datetime(value):

    if value is None:
        return None

    if pd.isna(value):
        return None

    # If already datetime
    if isinstance(value, datetime):
        return value.date()   # ✅ return only date

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().date()  # ✅ only date

    # Convert to string
    value = str(value).strip()

    # Try known formats
    for fmt in (
        "%d.%m.%Y",   # 30.05.2026
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d"
    ):
        try:
            return datetime.strptime(value, fmt).date()  # ✅ only date
        except ValueError:
            continue

    # Fallback
    try:
        return pd.to_datetime(value).date()  # ✅ only date
    except Exception:
        return None
