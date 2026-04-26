from __future__ import annotations

import pandas as pd
import streamlit as st

from src.data.sample_data import generate_hr_dataset

DEPARTMENT_TARGETS = {
    "marketing": 60.0,
    "التسويق": 60.0,
    "accounting": 50.0,
    "المحاسبة": 50.0,
}


@st.cache_data(show_spinner=False)
def get_hr_dataset() -> pd.DataFrame:
    return generate_hr_dataset()


def get_overview_metrics(df: pd.DataFrame) -> dict:
    total_headcount = len(df)
    saudi_headcount = int(df["is_saudi"].sum())
    non_saudi_headcount = total_headcount - saudi_headcount
    avg_salary = float(df["salary"].mean())
    avg_performance = float(df["performance_score"].mean())
    return {
        "total_headcount": total_headcount,
        "saudi_headcount": saudi_headcount,
        "non_saudi_headcount": non_saudi_headcount,
        "saudization_rate": (saudi_headcount / total_headcount) * 100 if total_headcount else 0,
        "avg_salary": avg_salary,
        "avg_performance": avg_performance,
    }


def get_saudization_by_department(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby("department", as_index=False)["is_saudi"]
        .mean()
        .rename(columns={"is_saudi": "saudization_rate"})
    )
    grouped["saudization_rate"] = grouped["saudization_rate"] * 100
    grouped["target_rate"] = grouped["department"].astype(str).str.strip().str.lower().map(DEPARTMENT_TARGETS)
    grouped["target_status"] = grouped.apply(
        lambda row: "N/A"
        if pd.isna(row["target_rate"])
        else ("Met" if row["saudization_rate"] >= row["target_rate"] else "Below Target"),
        axis=1,
    )
    return grouped.sort_values("saudization_rate", ascending=False)


def get_iqama_status(df: pd.DataFrame) -> pd.DataFrame:
    non_saudi = df[~df["is_saudi"]].copy()

    def iqama_bucket(days: float) -> str:
        if days < 0:
            return "Expired"
        if days <= 30:
            return "Due in 30 days"
        if days <= 90:
            return "Due in 90 days"
        return "Valid"

    non_saudi["iqama_status"] = non_saudi["iqama_days_remaining"].apply(iqama_bucket)
    return non_saudi


def get_contract_status(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()

    def contract_bucket(days: int) -> str:
        if days < 0:
            return "Expired"
        if days <= 60:
            return "Ending in 60 days"
        if days <= 120:
            return "Ending in 120 days"
        return "Active"

    frame["contract_status"] = frame["contract_days_remaining"].apply(contract_bucket)
    return frame


def get_salary_insurance_summary(df: pd.DataFrame) -> dict:
    total_salary = float(df["salary"].sum())
    total_insurance = float(df["insurance_cost"].sum())
    return {
        "total_payroll": total_salary,
        "avg_salary": float(df["salary"].mean()),
        "total_insurance": total_insurance,
        "insurance_ratio": (total_insurance / total_salary * 100) if total_salary else 0.0,
        "salary_by_department": df.groupby("department", as_index=False)["salary"].mean(),
    }


def get_workforce_insights(df: pd.DataFrame) -> dict:
    return {
        "headcount_by_city": df.groupby("city", as_index=False).size().rename(columns={"size": "headcount"}),
        "gender_distribution": df.groupby("gender", as_index=False).size().rename(columns={"size": "count"}),
        "tenure_by_department": df.groupby("department", as_index=False)["tenure_years"].mean(),
        "performance_by_department": df.groupby("department", as_index=False)["performance_score"].mean(),
    }
