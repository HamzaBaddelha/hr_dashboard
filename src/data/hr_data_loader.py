from __future__ import annotations

from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


ARABIC_COLUMN_ALIASES = {
    "الاسم": "name",
    "رقم الاقامة": "iqama_number",
    "الجنسية": "nationality",
    "الجنس": "gender",
    "تاريخ الميلاد": "birth_date",
    "المهنة": "job_title",
    "تاريخ الالتحاق بالعمل": "join_date",
    "تاريخ انتهاء الاقامة": "iqama_expiry_date",
    "الرواتب": "salary",
    "مدة العقد (بالسنة)": "contract_years",
    "انتهاء العقود": "contract_end_date",
    "الإدارة": "department",
    "الادارة": "department",
    "القسم": "department",
    "المدينة": "city",
    "الفرع": "city",
    "Employee ID": "employee_id",
    "employee id": "employee_id",
    "employee_id": "employee_id",
    "رقم الموظف": "employee_id",
    "department": "department",
    "city": "city",
}

TEXT_NULL_TOKENS = {"", "non", "none", "null", "nan", "-", "--", "na", "n/a"}


def read_hr_excel_safely(source: Any, sheet_name: str | int = 0) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Excel file not found: {path}")
        source_to_read = path
    else:
        source_to_read = source

    try:
        df = pd.read_excel(source_to_read, sheet_name=sheet_name, engine="openpyxl")
    except ValueError:
        df = pd.read_excel(source_to_read, sheet_name=sheet_name)
    except Exception as exc:
        raise ValueError(f"Unable to read Excel file: {exc}") from exc

    if df.empty:
        raise ValueError("Excel file is empty.")

    return df


def strip_spaces(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [_normalize_space(col) for col in cleaned.columns]

    object_columns = cleaned.select_dtypes(include=["object"]).columns
    for col in object_columns:
        cleaned[col] = cleaned[col].map(_clean_text_value)

    return cleaned


def standardize_hr_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = strip_spaces(df)

    rename_map = {}
    normalized_aliases = {_normalize_space(k): v for k, v in ARABIC_COLUMN_ALIASES.items()}
    for col in cleaned.columns:
        normalized_col = _normalize_space(col)
        if normalized_col in normalized_aliases:
            rename_map[col] = normalized_aliases[normalized_col]

    standardized = cleaned.rename(columns=rename_map)
    required_columns = [
        "name",
        "iqama_number",
        "employee_id",
        "nationality",
        "gender",
        "birth_date",
        "job_title",
        "join_date",
        "iqama_expiry_date",
        "salary",
        "contract_years",
        "contract_end_date",
        "department",
        "city",
    ]
    for col in required_columns:
        if col not in standardized.columns:
            standardized[col] = pd.NA

    return standardized[required_columns]


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    for col in ["birth_date", "join_date", "iqama_expiry_date", "contract_end_date"]:
        output[col] = output[col].map(_parse_excel_or_string_date)
    return output


def clean_iqama_values(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output["iqama_number"] = output["iqama_number"].map(_normalize_iqama_number)
    return output


def compute_hr_metrics(
    df: pd.DataFrame,
    *,
    reference_date: str | pd.Timestamp | None = None,
    saudi_insurance_rate: float = 0.10,
    non_saudi_insurance_rate: float = 0.02,
) -> pd.DataFrame:
    output = df.copy()
    ref_date = _get_riyadh_today() if reference_date is None else pd.Timestamp(reference_date).normalize()

    output["salary"] = pd.to_numeric(output["salary"], errors="coerce").fillna(0.0)
    output["contract_years"] = pd.to_numeric(output["contract_years"], errors="coerce")

    output["is_saudi"] = output["nationality"].map(_is_saudi_nationality)
    output["iqama_days_left"] = (output["iqama_expiry_date"] - ref_date).dt.days
    output["iqama_status"] = output["iqama_days_left"].map(_iqama_status)
    output["contract_days_left"] = (output["contract_end_date"] - ref_date).dt.days
    output["contract_status"] = output["contract_days_left"].map(_contract_status)

    output["insurance_rate"] = output["is_saudi"].map(
        lambda is_saudi: saudi_insurance_rate if is_saudi else non_saudi_insurance_rate
    )
    output["insurance_amount"] = output["salary"] * output["insurance_rate"]
    output["net_salary"] = output["salary"] - output["insurance_amount"]

    return output


def build_hr_summary(df: pd.DataFrame) -> pd.DataFrame:
    total_employees = int(len(df))
    saudi_count = int(df["is_saudi"].sum()) if "is_saudi" in df.columns else 0
    non_saudi_count = total_employees - saudi_count
    saudization_percent = (saudi_count / total_employees * 100) if total_employees else 0.0

    return pd.DataFrame(
        [
            {
                "total_employees": total_employees,
                "saudi_count": saudi_count,
                "non_saudi_count": non_saudi_count,
                "saudization_percent": saudization_percent,
            }
        ]
    )


def load_and_clean_hr_dataframe(
    source: Any,
    *,
    sheet_name: str | int = 0,
    reference_date: str | pd.Timestamp | None = None,
    saudi_insurance_rate: float = 0.10,
    non_saudi_insurance_rate: float = 0.02,
) -> pd.DataFrame:
    raw_df = read_hr_excel_safely(source, sheet_name=sheet_name)
    _validate_required_source_columns(raw_df)
    standardized_df = standardize_hr_columns(raw_df)
    dated_df = standardize_dates(standardized_df)
    iqama_df = clean_iqama_values(dated_df)
    return compute_hr_metrics(
        iqama_df,
        reference_date=reference_date,
        saudi_insurance_rate=saudi_insurance_rate,
        non_saudi_insurance_rate=non_saudi_insurance_rate,
    )


def _normalize_space(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = str(value).replace("\u00A0", " ").replace("\u200f", "").replace("\u200e", "")
    return " ".join(text.split()).strip()


def _clean_text_value(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, str):
        normalized = _normalize_space(value)
        return pd.NA if normalized == "" else normalized
    return value


def _parse_excel_or_string_date(value: Any) -> pd.Timestamp | pd.NaT:
    if pd.isna(value):
        return pd.NaT

    if isinstance(value, pd.Timestamp):
        return value.normalize()

    if isinstance(value, (int, float)):
        if pd.isna(value):
            return pd.NaT
        # Excel serial dates are based on 1899-12-30 origin.
        return pd.to_datetime(value, unit="D", origin="1899-12-30", errors="coerce")

    text_value = _normalize_space(value)
    if text_value == "":
        return pd.NaT

    numeric_text = text_value.replace(",", "")
    if numeric_text.replace(".", "", 1).isdigit():
        return pd.to_datetime(float(numeric_text), unit="D", origin="1899-12-30", errors="coerce")

    parsed = pd.to_datetime(text_value, errors="coerce", dayfirst=True)
    return parsed.normalize() if pd.notna(parsed) else pd.NaT


def _normalize_iqama_number(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA

    normalized = _normalize_space(value).lower()
    if normalized in TEXT_NULL_TOKENS:
        return pd.NA

    return _normalize_space(value)


def _is_saudi_nationality(value: Any) -> bool:
    if pd.isna(value):
        return False
    normalized = _normalize_space(value).lower()
    normalized = normalized.replace("ى", "ي").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    normalized = normalized.replace("ال", "") if normalized.startswith("ال") else normalized
    return (
        normalized in {"saudi", "saudi arabia", "سعودي", "سعوديه", "سعودية", "سعوديين", "سعوديون"}
        or "saud" in normalized
        or "سعود" in normalized
    )


def _iqama_status(days_left: Any) -> str:
    if pd.isna(days_left):
        return "No Iqama"
    if days_left < 0:
        return "Expired"
    if days_left <= 30:
        return "Expiring Soon"
    return "Valid"


def _contract_status(days_left: Any) -> str:
    if pd.isna(days_left):
        return "No Contract Date"
    if days_left < 0:
        return "Expired"
    if days_left <= 60:
        return "Ending Soon"
    return "Active"


def _get_riyadh_today() -> pd.Timestamp:
    return pd.Timestamp.now(tz=ZoneInfo("Asia/Riyadh")).normalize().tz_localize(None)


def _validate_required_source_columns(raw_df: pd.DataFrame) -> None:
    normalized_headers = {_normalize_space(col) for col in raw_df.columns}
    if "المهنة" not in normalized_headers:
        raise ValueError('العمود المطلوب "المهنة" غير موجود في ملف Excel المرفوع.')
