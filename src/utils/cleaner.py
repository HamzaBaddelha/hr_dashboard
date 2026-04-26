from __future__ import annotations

from typing import Any
from difflib import SequenceMatcher

import pandas as pd

try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover - fallback for environments without rapidfuzz
    fuzz = None
    process = None


SAUDI_VALUES = {"saudi", "saudi arabia", "سعودي", "سعودية", "سعوديه", "سعودى", "السعودي", "السعودية"}
SAUDI_ID_PREFIXES = ("1", "10", "11")
NON_SAUDI_ID_PREFIX = "2"
FUZZY_MATCH_THRESHOLD = 90

JOB_TITLE_TO_DEPARTMENT = {
    "أخصائي تسويق": "التسويق",
    "مدير إداري": "الإدارة",
    "موظف استقبال": "الاستقبال وخدمة العملاء",
    "أخصائي مبيعات": "المبيعات",
    "مندوب مبيعات": "المبيعات",
    "مدير مبيعات": "المبيعات",
    "مشرف صيانة": "الصيانة",
    "مساعد ميكانيكي صيانة": "الصيانة",
    "مدير تطوير موارد بشرية": "الموارد البشرية",
    "أخصائي تقنية هندسة تقنية معلومات": "تقنية المعلومات",
    "مبرمج حاسب آلي": "تقنية المعلومات",
    "كاتب علاقات حكومية": "العلاقات الحكومية",
    "محاسب": "المالية والمحاسبة",
    "كاتب حسابات": "المالية والمحاسبة",
    "عامل ورشة": "الورشة والعمليات الفنية",
    "عامل عزل حراري": "الورشة والعمليات الفنية",
    "عامل تلميع مركبات": "الورشة والعمليات الفنية",
    "عامل طلاء مركبات": "الورشة والعمليات الفنية",
    "عامل تنظيف مركبات": "الورشة والعمليات الفنية",
    "عامل عادي": "العمليات العامة",
    "سائق سيارة": "النقل واللوجستيات",
    "سائق شاحنة ثقيلة": "النقل واللوجستيات",
    "عامل تحميل وتنزيل": "المخزون واللوجستيات",
    "عامل مخزن": "المخزون والمستودعات",
    "عامل تعبئة رفوف": "المخزون والمستودعات",
    "مراقب الجودة": "الجودة",
}

JOB_TITLE_ALIASES = {
    "اخصائي تسويق": "أخصائي تسويق",
    "اخصائي مبيعات": "أخصائي مبيعات",
    "مدير اداري": "مدير إداري",
    "مدير تطوير الموارد البشرية": "مدير تطوير موارد بشرية",
    "كاتب علاقات حكوميه": "كاتب علاقات حكومية",
    "عامل مستودع": "عامل مخزن",
    "عامل مخزون": "عامل مخزن",
    "مراقب جودة": "مراقب الجودة",
}

MERGED_DEPARTMENT_MAP = {
    "الصيانة": "العمليات التشغيلية",
    "الورشة والعمليات الفنية": "العمليات التشغيلية",
    "العمليات العامة": "العمليات التشغيلية",
    "النقل واللوجستيات": "الخدمات اللوجستية",
    "المخزون واللوجستيات": "الخدمات اللوجستية",
    "المخزون والمستودعات": "الخدمات اللوجستية",
    "الإدارة": "الدعم الإداري",
    "الموارد البشرية": "الدعم الإداري",
    "العلاقات الحكومية": "الدعم الإداري",
    "الاستقبال وخدمة العملاء": "الدعم الإداري",
    "التسويق": "الدعم التجاري",
    "المبيعات": "الدعم التجاري",
    "تقنية المعلومات": "الدعم الفني",
    "المالية والمحاسبة": "الدعم المالي",
    "الجودة": "الجودة",
    "أخرى": "أخرى",
}

NORMALIZED_TITLE_TO_CANONICAL = {
    " ".join(normalize_key.split()): canonical
    for canonical in JOB_TITLE_TO_DEPARTMENT
    for normalize_key in [canonical]
}


def infer_is_saudi_flags(
    nationality_series: pd.Series,
    employee_id_series: pd.Series | None = None,
) -> pd.Series:
    normalized_nat = nationality_series.map(_normalize_text)
    from_nationality = normalized_nat.map(_is_saudi_text)

    if employee_id_series is None:
        return from_nationality

    normalized_id = employee_id_series.map(_normalize_employee_id).astype("string")
    from_id = normalized_id.str.startswith(SAUDI_ID_PREFIXES, na=False)
    has_known_nationality = normalized_nat.map(lambda value: value != "")

    # Primary source is nationality; fallback to ID prefix when nationality is missing.
    return from_nationality.where(has_known_nationality, from_id)


def normalize_arabic_text(text: Any) -> str:
    if pd.isna(text):
        return ""
    value = str(text)
    for ch in ["\u200f", "\u200e", "\u202a", "\u202b", "\u202c", "\u2066", "\u2067", "\u2068", "\u2069", "\ufeff"]:
        value = value.replace(ch, "")
    value = value.replace("ـ", "")
    value = value.replace("\u00A0", " ")
    value = " ".join(value.split()).strip()
    return value


def clean_job_title(title: Any) -> str:
    cleaned = normalize_arabic_text(title)
    cleaned = cleaned.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return cleaned.strip()


def assign_merged_department(department: Any) -> str:
    if pd.isna(department):
        return "أخرى"
    normalized = normalize_arabic_text(department)
    return MERGED_DEPARTMENT_MAP.get(normalized, "أخرى")


def standardize_job_titles(df: pd.DataFrame, source_col: str = "job_title") -> pd.DataFrame:
    if source_col not in df.columns:
        raise ValueError('العمود "المهنة" غير موجود في الملف المرفوع.')

    output = df.copy()
    output["المسمى_الأصلي"] = output[source_col]
    output["المسمى_بعد_التنظيف"] = output[source_col].map(clean_job_title)

    result_rows = output["المسمى_بعد_التنظيف"].map(_resolve_job_title_match)
    resolved_df = pd.DataFrame(
        result_rows.tolist(),
        columns=["المسمى_المصحح", "الإدارة", "حالة_المطابقة", "درجة_التشابه"],
        index=output.index,
    )
    output = pd.concat([output, resolved_df], axis=1)
    output["الإدارة_المجمعة"] = output["الإدارة"].map(assign_merged_department)
    return output


def build_job_title_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [
        "المسمى_الأصلي",
        "المسمى_بعد_التنظيف",
        "المسمى_المصحح",
        "الإدارة",
        "الإدارة_المجمعة",
        "حالة_المطابقة",
        "درجة_التشابه",
    ]
    report = df.copy()
    for col in required_cols:
        if col not in report.columns:
            report[col] = pd.NA
    return report[required_cols].copy()


def get_job_title_quality_summary(df: pd.DataFrame) -> dict[str, int]:
    if "حالة_المطابقة" not in df.columns:
        return {"مطابق مباشر": 0, "تم التصحيح تلقائيًا": 0, "غير معروف": 0, "فارغ": 0}
    return {
        "مطابق مباشر": int((df["حالة_المطابقة"] == "مطابق مباشر").sum()),
        "تم التصحيح تلقائيًا": int((df["حالة_المطابقة"] == "تم التصحيح تلقائيًا").sum()),
        "غير معروف": int((df["حالة_المطابقة"] == "غير معروف").sum()),
        "فارغ": int((df["حالة_المطابقة"] == "فارغ").sum()),
    }


def enforce_employee_id_business_rules(
    df: pd.DataFrame,
    *,
    nationality_col: str = "nationality",
    employee_id_col: str = "employee_id",
) -> pd.DataFrame:
    output = df.copy()

    if nationality_col not in output.columns:
        output[nationality_col] = pd.NA
    if employee_id_col not in output.columns:
        output[employee_id_col] = pd.NA

    is_saudi = infer_is_saudi_flags(output[nationality_col], output[employee_id_col])
    expected_prefix = is_saudi.map(lambda value: "11" if value else "2")

    employee_ids = output[employee_id_col].map(_normalize_employee_id)
    present_mask = employee_ids.notna()
    id_text = employee_ids.astype("string")
    saudi_valid = id_text.str.startswith(SAUDI_ID_PREFIXES, na=False)
    non_saudi_valid = id_text.str.startswith(NON_SAUDI_ID_PREFIX, na=False)
    valid_mask = present_mask & ((is_saudi & saudi_valid) | (~is_saudi & non_saudi_valid))
    invalid_mask = present_mask & ~valid_mask
    generated_mask = ~present_mask

    generated_ids = _generate_missing_ids(expected_prefix, employee_ids)
    output[employee_id_col] = employee_ids.where(~generated_mask, generated_ids)

    output["employee_id_status"] = "Valid"
    output.loc[generated_mask, "employee_id_status"] = "Generated"
    output.loc[invalid_mask, "employee_id_status"] = "Invalid"

    output["employee_id_validation_reason"] = "-"
    output.loc[generated_mask, "employee_id_validation_reason"] = "Generated automatically because Employee ID was missing."
    output.loc[invalid_mask & is_saudi, "employee_id_validation_reason"] = (
        "Invalid: Saudi employee ID must start with 1, 10, or 11."
    )
    output.loc[invalid_mask & ~is_saudi, "employee_id_validation_reason"] = (
        "Invalid: Non-Saudi employee ID must start with 2."
    )

    return output


def _generate_missing_ids(expected_prefix: pd.Series, existing_ids: pd.Series) -> pd.Series:
    used_ids = {str(value) for value in existing_ids.dropna().astype(str)}
    prefixes = sorted({str(prefix) for prefix in expected_prefix.dropna().astype(str)})
    next_seq = {prefix: 1 for prefix in prefixes}

    for employee_id in used_ids:
        for prefix in prefixes:
            if employee_id.startswith(prefix):
                suffix = employee_id[len(prefix) :]
                if suffix.isdigit():
                    next_seq[prefix] = max(next_seq[prefix], int(suffix) + 1)

    generated = pd.Series([pd.NA] * len(expected_prefix), index=expected_prefix.index, dtype="object")
    for idx, prefix in expected_prefix.items():
        if prefix not in next_seq:
            prefix = "2"
            if prefix not in next_seq:
                next_seq[prefix] = 1

        candidate = f"{prefix}{next_seq[prefix]:08d}"
        while candidate in used_ids:
            next_seq[prefix] += 1
            candidate = f"{prefix}{next_seq[prefix]:08d}"
        generated.loc[idx] = candidate
        used_ids.add(candidate)
        next_seq[prefix] += 1

    return generated


def _normalize_employee_id(value: Any) -> Any:
    if pd.isna(value):
        return pd.NA
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return pd.NA
        if float(value).is_integer():
            return str(int(value))
        return str(value).strip()

    normalized = str(value).strip()
    if normalized == "":
        return pd.NA
    if normalized.endswith(".0") and normalized.replace(".", "", 1).isdigit():
        normalized = normalized[:-2]
    return normalized


def _normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    text = normalize_arabic_text(value).lower()
    text = text.replace("ى", "ي").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return text


def _is_saudi_text(value: str) -> bool:
    if not value:
        return False
    normalized = value[2:] if value.startswith("ال") else value
    return normalized in SAUDI_VALUES or "saud" in normalized or "سعود" in normalized


def _resolve_job_title_match(cleaned_title: str) -> tuple[str, str, str, float | None]:
    if cleaned_title == "":
        return "", "أخرى", "فارغ", None

    # exact after normalization
    for canonical_title, department in JOB_TITLE_TO_DEPARTMENT.items():
        if clean_job_title(canonical_title) == cleaned_title:
            return canonical_title, department, "مطابق مباشر", 100.0

    # alias correction
    alias_target = JOB_TITLE_ALIASES.get(cleaned_title)
    if alias_target:
        return alias_target, JOB_TITLE_TO_DEPARTMENT[alias_target], "تم التصحيح تلقائيًا", 100.0

    # fuzzy correction
    normalized_candidates = [clean_job_title(title) for title in JOB_TITLE_TO_DEPARTMENT.keys()]
    best = _extract_best_match(cleaned_title, normalized_candidates)
    if best:
        matched_normalized, score, _ = best
        if score >= FUZZY_MATCH_THRESHOLD:
            for canonical_title, department in JOB_TITLE_TO_DEPARTMENT.items():
                if clean_job_title(canonical_title) == matched_normalized:
                    return canonical_title, department, "تم التصحيح تلقائيًا", float(score)
        return cleaned_title, "أخرى", "غير معروف", float(score)

    return cleaned_title, "أخرى", "غير معروف", None


def _extract_best_match(query: str, candidates: list[str]) -> tuple[str, float, int] | None:
    if not candidates:
        return None
    if process is not None and fuzz is not None:
        return process.extractOne(query, candidates, scorer=fuzz.ratio)

    best_idx = -1
    best_score = -1.0
    best_value = ""
    for idx, candidate in enumerate(candidates):
        score = SequenceMatcher(None, query, candidate).ratio() * 100
        if score > best_score:
            best_score = score
            best_idx = idx
            best_value = candidate

    if best_idx < 0:
        return None
    return best_value, float(best_score), best_idx
