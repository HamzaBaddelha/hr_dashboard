from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from src.data.hr_data_loader import load_and_clean_hr_dataframe
from src.data.sample_data import generate_hr_dataset
from src.utils.cleaner import (
    enforce_employee_id_business_rules,
    infer_is_saudi_flags,
    standardize_job_titles,
)


SAUDI_INSURANCE_RATE = 0.0975
NON_SAUDI_INSURANCE_RATE = 0.02


def get_dashboard_dataset(uploaded_file) -> tuple[pd.DataFrame, str]:
    if uploaded_file is None:
        sample_df = generate_hr_dataset()
        sample_df["employee_id"] = pd.NA
        sample_df["job_title"] = sample_df.get("job_family", pd.Series([""] * len(sample_df), index=sample_df.index))
        sample_df["iqama_expiry_date"] = pd.to_datetime(sample_df["iqama_expiry_date"], errors="coerce")
        sample_df["contract_end_date"] = pd.to_datetime(sample_df["contract_end_date"], errors="coerce")
        sample_df["insurance_cost"] = (
            sample_df["salary"]
            * sample_df["is_saudi"].map(lambda is_saudi: SAUDI_INSURANCE_RATE if is_saudi else NON_SAUDI_INSURANCE_RATE)
        ).round(2)
        sample_df = standardize_job_titles(sample_df, source_col="job_title")
        sample_df["department"] = sample_df["الإدارة"].fillna(sample_df["department"]).fillna("أخرى")
        sample_df["job_family"] = sample_df["المسمى_المصحح"].fillna(sample_df["job_family"]).fillna("غير محدد")
        sample_df = enforce_employee_id_business_rules(sample_df, nationality_col="nationality", employee_id_col="employee_id")
        return sample_df, "sample"
    data = _load_uploaded_dashboard_dataset(uploaded_file.getvalue())
    return data, "uploaded"


@st.cache_data(show_spinner=False)
def _load_uploaded_dashboard_dataset(file_bytes: bytes) -> pd.DataFrame:
    cleaned = load_and_clean_hr_dataframe(
        io.BytesIO(file_bytes),
        saudi_insurance_rate=SAUDI_INSURANCE_RATE,
        non_saudi_insurance_rate=NON_SAUDI_INSURANCE_RATE,
    )
    return _to_dashboard_schema(cleaned)


def _to_dashboard_schema(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    output = standardize_job_titles(output, source_col="job_title")

    output["employee_id"] = _series_or_default(output, "employee_id", pd.NA)
    output["employee_name"] = _series_or_default(output, "name", "غير محدد").fillna("غير محدد")
    output["department"] = output["الإدارة"].fillna("أخرى")
    output["job_family"] = output["المسمى_المصحح"].fillna(_series_or_default(output, "job_title", "غير محدد")).fillna("غير محدد")
    output["city"] = _series_or_default(output, "city", "الرياض").fillna("الرياض")
    output["gender"] = _series_or_default(output, "gender", "غير محدد").map(_normalize_gender).fillna("غير محدد")
    output["salary"] = pd.to_numeric(_series_or_default(output, "salary", 0.0), errors="coerce").fillna(0.0)
    output["insurance_cost"] = pd.to_numeric(_series_or_default(output, "insurance_amount", 0.0), errors="coerce").fillna(0.0)
    output["iqama_days_remaining"] = pd.to_numeric(_series_or_default(output, "iqama_days_left", pd.NA), errors="coerce")
    output["contract_days_remaining"] = pd.to_numeric(_series_or_default(output, "contract_days_left", pd.NA), errors="coerce")
    output["performance_score"] = 3.0

    birth_date = pd.to_datetime(_series_or_default(output, "birth_date", pd.NaT), errors="coerce")
    join_date = pd.to_datetime(_series_or_default(output, "join_date", pd.NaT), errors="coerce")
    today = pd.Timestamp.now().normalize()
    output["age"] = ((today - birth_date).dt.days / 365.25).round().fillna(0).astype(int)
    output["tenure_years"] = ((today - join_date).dt.days / 365.25).round(1).fillna(0.0)

    output["insurance_level"] = pd.cut(
        output["salary"],
        bins=[-1, 6999, 14999, float("inf")],
        labels=["C", "B", "A"],
    )
    output["insurance_level"] = output["insurance_level"].astype("string").fillna("C")

    output["iqama_expiry_date"] = pd.to_datetime(_series_or_default(output, "iqama_expiry_date", pd.NaT), errors="coerce")
    output["contract_end_date"] = pd.to_datetime(_series_or_default(output, "contract_end_date", pd.NaT), errors="coerce")

    # Recompute Saudi flag with robust nationality parsing and fallback to ID prefix.
    output["nationality"] = _series_or_default(output, "nationality", "غير محدد")
    output["is_saudi"] = infer_is_saudi_flags(output["nationality"], output["employee_id"])
    output = enforce_employee_id_business_rules(output, nationality_col="nationality", employee_id_col="employee_id")

    required_cols = [
        "employee_id",
        "employee_id_status",
        "employee_id_validation_reason",
        "المسمى_الأصلي",
        "المسمى_بعد_التنظيف",
        "المسمى_المصحح",
        "الإدارة",
        "الإدارة_المجمعة",
        "حالة_المطابقة",
        "درجة_التشابه",
        "employee_name",
        "is_saudi",
        "nationality",
        "department",
        "job_family",
        "city",
        "gender",
        "insurance_level",
        "salary",
        "insurance_cost",
        "iqama_expiry_date",
        "iqama_days_remaining",
        "contract_end_date",
        "contract_days_remaining",
        "performance_score",
        "age",
        "tenure_years",
    ]
    return output[required_cols]


def _normalize_gender(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    text = text.replace("\u00A0", " ").replace("\u200f", "").replace("\u200e", "")
    text = " ".join(text.split())

    if text in {"female", "f", "انثى", "أنثى", "female.", "fem", "lady"}:
        return "Female"
    if text in {"male", "m", "ذكر", "male.", "man"}:
        return "Male"
    return str(value).strip()


def _series_or_default(df: pd.DataFrame, col: str, default_value):
    return df.get(col, pd.Series([default_value] * len(df), index=df.index))
