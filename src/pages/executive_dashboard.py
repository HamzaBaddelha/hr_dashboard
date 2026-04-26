from __future__ import annotations

import io

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from src.services.hr_metrics_service import (
    get_contract_status,
    get_iqama_status,
    get_overview_metrics,
    get_saudization_by_department,
)
from src.ui.components import kpi_card, section_title
from src.utils.cleaner import build_job_title_quality_report, get_job_title_quality_summary
from src.utils.formatters import format_currency, format_percent


def render(df, title: str) -> None:
    section_title(title, "لوحة تنفيذية متكاملة للموارد البشرية مع قراءات امتثال وتوصيات عملية")

    _render_kpi_overview(df)
    _render_saudi_donut(df)
    _render_iqama_section(df)
    _render_contract_section(df)
    _render_salary_by_department(df)
    _render_salary_insurance_chart(df)
    _render_workforce_insights(df)
    _render_employee_id_validation(df)
    _render_department_analysis(df)
    _render_job_title_quality(df)


def _render_kpi_overview(df) -> None:
    st.markdown("### 1) بطاقات مؤشرات الأداء الرئيسية")
    metrics = get_overview_metrics(df)
    total_insurance = float(df["insurance_cost"].sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("إجمالي الموظفين", str(metrics["total_headcount"]))
    with c2:
        kpi_card("عدد السعوديين", str(metrics["saudi_headcount"]))
    with c3:
        kpi_card("عدد غير السعوديين", str(metrics["non_saudi_headcount"]))
    with c4:
        kpi_card("نسبة السعودة", format_percent(metrics["saudization_rate"]))
    with c5:
        kpi_card("إجمالي الاستقطاعات", format_currency(total_insurance))


def _render_saudi_donut(df) -> None:
    st.markdown("### 2) توزيع السعوديين وغير السعوديين")
    count_df = (
        df.assign(category=df["is_saudi"].map(lambda x: "Saudi" if x else "Non-Saudi"))
        .groupby("category", as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )

    fig = px.pie(
        count_df,
        names="category",
        values="count",
        hole=0.62,
        color="category",
        color_discrete_map={"Saudi": "#10B981", "Non-Saudi": "#F59E0B"},
        title="توزيع القوى العاملة بين السعوديين وغير السعوديين",
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)

    dept_targets = get_saudization_by_department(df)
    targets_view = dept_targets[dept_targets["target_rate"].notna()][
        ["department", "saudization_rate", "target_rate", "target_status"]
    ].copy()
    if not targets_view.empty:
        targets_view["saudization_rate"] = targets_view["saudization_rate"].map(lambda x: f"{x:.1f}%")
        targets_view["target_rate"] = targets_view["target_rate"].map(lambda x: f"{x:.1f}%")
        st.dataframe(targets_view, use_container_width=True, hide_index=True)

    _arabic_explanation(
        what_it_shows="يوضح توزيع القوى العاملة بين السعوديين وغير السعوديين.",
        current_insight=f"نسبة السعودة الحالية تبلغ {format_percent(df['is_saudi'].mean() * 100)} من إجمالي الموظفين.",
        risk_note="أي انخفاض مستمر في نسبة السعودة قد يرفع مخاطر عدم الالتزام بمتطلبات التوطين.",
        action_recommendation="تعزيز التوظيف المحلي في الإدارات الأقل سعودة مع متابعة شهرية للنسبة.",
    )


def _render_iqama_section(df) -> None:
    st.markdown("### 3) تنبيهات انتهاء الإقامة")
    iqama_df = get_iqama_status(df).copy()
    iqama_df["iqama_expiry_date"] = pd.to_datetime(iqama_df["iqama_expiry_date"], errors="coerce")
    alerts = iqama_df[iqama_df["iqama_status"].isin(["Expired", "Due in 30 days", "Due in 90 days"])].copy()
    alerts["expiry_month"] = alerts["iqama_expiry_date"].dt.to_period("M").astype(str)

    c1, c2 = st.columns([1.2, 1.8])
    with c1:
        st.dataframe(
            alerts[
                [
                    "employee_id",
                    "employee_name",
                    "department",
                    "nationality",
                    "iqama_days_remaining",
                    "iqama_expiry_date",
                    "iqama_status",
                ]
            ].sort_values("iqama_days_remaining"),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        monthly = alerts.groupby("expiry_month", as_index=False).size().rename(columns={"size": "count"})
        fig = px.bar(
            monthly,
            x="expiry_month",
            y="count",
            color="count",
            color_continuous_scale="OrRd",
            title="اتجاه انتهاء الإقامات شهرياً",
        )
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)

    _arabic_explanation(
        what_it_shows="يبين الجدول الحالات الحرجة للإقامات، ويعرض الرسم عدد الإقامات المنتهية أو القريبة من الانتهاء شهرياً.",
        current_insight=f"عدد الحالات الحرجة حالياً هو {len(alerts)} حالة، مع تركّز واضح في الأشهر القادمة.",
        risk_note="التأخر في التجديد يعرض المنشأة لمخالفات نظامية وتعطيل إجراءات الموظفين.",
        action_recommendation="تفعيل تنبيه تلقائي قبل 90/30 يوم، وتحديد مالك متابعة لكل إدارة.",
    )


def _render_contract_section(df) -> None:
    st.markdown("### 4) تنبيهات انتهاء العقود")
    contract_df = get_contract_status(df).copy()
    contract_df["contract_end_date"] = pd.to_datetime(contract_df["contract_end_date"], errors="coerce")
    alerts = contract_df[contract_df["contract_status"].isin(["Expired", "Ending in 60 days", "Ending in 120 days"])].copy()
    alerts["contract_month"] = alerts["contract_end_date"].dt.to_period("M").astype(str)

    c1, c2 = st.columns([1.2, 1.8])
    with c1:
        st.dataframe(
            alerts[
                [
                    "employee_id",
                    "employee_name",
                    "department",
                    "job_family",
                    "contract_days_remaining",
                    "contract_end_date",
                    "contract_status",
                ]
            ].sort_values("contract_days_remaining"),
            use_container_width=True,
            hide_index=True,
        )
    with c2:
        monthly = alerts.groupby("contract_month", as_index=False).size().rename(columns={"size": "count"})
        fig = px.line(
            monthly,
            x="contract_month",
            y="count",
            markers=True,
            title="اتجاه انتهاء العقود شهرياً",
        )
        fig.update_traces(line=dict(color="#60A5FA", width=3))
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig, use_container_width=True)

    _arabic_explanation(
        what_it_shows="يعرض الجدول العقود المنتهية أو القريبة للانتهاء، ويعرض الرسم اتجاه الانتهاء حسب الشهر.",
        current_insight=f"إجمالي العقود التي تحتاج إجراء قريباً هو {len(alerts)} عقداً.",
        risk_note="عدم التخطيط المبكر للتجديد قد يؤدي إلى فقد كفاءات أو انقطاع في العمليات.",
        action_recommendation="بدء دورة قرار التجديد قبل 120 يوماً مع ربطها بتقييم الأداء والميزانية.",
    )


def _render_salary_by_department(df) -> None:
    st.markdown("### 5) الرواتب حسب الإدارة")
    salary_df = df.groupby("department", as_index=False)["salary"].mean().sort_values("salary", ascending=False)
    fig = px.bar(
        salary_df,
        x="department",
        y="salary",
        color="salary",
        color_continuous_scale="Blues",
        title="متوسط الرواتب حسب الإدارة",
    )
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, use_container_width=True)

    _arabic_explanation(
        what_it_shows="يوضح متوسط الرواتب لكل إدارة ويُظهر الفروقات بين الوظائف والمجالات.",
        current_insight="توجد فجوات واضحة بين الإدارات ذات الرواتب المرتفعة والمنخفضة.",
        risk_note="الفجوات غير المبررة قد تؤثر على العدالة الداخلية والاحتفاظ بالمواهب.",
        action_recommendation="مراجعة هيكل الرواتب حسب العائلة الوظيفية والسوق المرجعي بشكل ربع سنوي.",
    )


def _render_salary_insurance_chart(df) -> None:
    st.markdown("### 6) الرواتب مقابل الاستقطاع التأميني")
    comp_df = (
        df.groupby("department", as_index=False)
        .agg(avg_salary=("salary", "mean"), avg_insurance=("insurance_cost", "mean"))
        .sort_values("avg_salary", ascending=False)
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=comp_df["department"],
            y=comp_df["avg_salary"],
            name="متوسط الراتب",
            marker_color="#60A5FA",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=comp_df["department"],
            y=comp_df["avg_insurance"],
            mode="lines+markers",
            name="متوسط الاستقطاع",
            line=dict(color="#F59E0B", width=3),
        )
    )
    fig.update_layout(
        title="مقارنة الرواتب وتكلفة الاستقطاع حسب الإدارة",
        height=390,
        margin=dict(l=10, r=10, t=60, b=10),
        barmode="group",
    )
    st.plotly_chart(fig, use_container_width=True)

    _arabic_explanation(
        what_it_shows="يقارن بين متوسط الراتب ومتوسط تكلفة التأمين لكل إدارة في رسم واحد.",
        current_insight="الارتفاع في الرواتب ينعكس مباشرة على تكلفة التأمين وخاصة في الإدارات الكبيرة.",
        risk_note="ارتفاع التكلفة دون ضبط قد يضغط على هامش الربحية وتكاليف التشغيل السنوية.",
        action_recommendation="محاكاة سيناريوهات الميزانية وربط الزيادات بخطط إنتاجية واضحة.",
    )


def _render_workforce_insights(df) -> None:
    st.markdown("### 7) رؤى القوى العاملة")
    workforce = df.copy()

    workforce["age_band"] = pd.cut(
        workforce["age"],
        bins=[0, 25, 35, 45, 55, 100],
        labels=["<=25", "26-35", "36-45", "46-55", "56+"],
        include_lowest=True,
    )
    workforce["tenure_band"] = pd.cut(
        workforce["tenure_years"],
        bins=[0, 2, 5, 10, 20, 50],
        labels=["0-2", "3-5", "6-10", "11-20", "20+"],
        include_lowest=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        gender = workforce.groupby("gender", as_index=False).size().rename(columns={"size": "count"})
        fig_gender = px.pie(gender, names="gender", values="count", hole=0.55, title="توزيع الجنس")
        fig_gender.update_layout(height=350, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_gender, use_container_width=True)
        _workforce_chart_explanation(
            what_it_shows="يوضح توزيع الموظفين حسب الجنس داخل الشركة.",
            current_insight="يساعد على قراءة التوازن الديموغرافي وتحديد الفجوات في التنوع.",
            risk_note="عدم التوازن الكبير قد يؤثر على بيئة العمل ومؤشرات التنوع المؤسسي.",
            action_recommendation="مراجعة خطط الاستقطاب لضمان توازن أفضل عبر الإدارات المختلفة.",
        )
    with c2:
        age_band = workforce.groupby("age_band", as_index=False).size().rename(columns={"size": "count"})
        fig_age = px.bar(age_band, x="age_band", y="count", color="count", title="شرائح الأعمار")
        fig_age.update_layout(height=350, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_age, use_container_width=True)
        _workforce_chart_explanation(
            what_it_shows="يعرض عدد الموظفين ضمن كل شريحة عمرية.",
            current_insight="يكشف الشرائح العمرية المهيمنة ومدى توفر عمق قيادي مستقبلي.",
            risk_note="الاعتماد على شريحة عمرية واحدة قد يرفع مخاطر فجوات الإحلال الوظيفي.",
            action_recommendation="تخطيط التوظيف والتطوير لتحقيق توزيع عمري أكثر استدامة.",
        )

    c3, c4 = st.columns(2)
    with c3:
        tenure = workforce.groupby("tenure_band", as_index=False).size().rename(columns={"size": "count"})
        fig_tenure = px.bar(tenure, x="tenure_band", y="count", color="count", title="شرائح الخبرة")
        fig_tenure.update_layout(height=350, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_tenure, use_container_width=True)
        _workforce_chart_explanation(
            what_it_shows="يوزع الموظفين حسب سنوات الخدمة داخل الشركة.",
            current_insight="يوضح تركز القوى العاملة بين الموظفين الجدد وذوي الخبرة الطويلة.",
            risk_note="ارتفاع نسبة فئة واحدة فقط قد يضعف نقل المعرفة أو سرعة الإنتاجية.",
            action_recommendation="موازنة برامج الاحتفاظ والتأهيل لضمان استمرارية المعرفة المؤسسية.",
        )
    with c4:
        top_nat = (
            workforce.groupby("nationality", as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values("count", ascending=False)
            .head(8)
        )
        fig_nat = px.bar(top_nat, x="nationality", y="count", color="count", title="أعلى الجنسيات")
        fig_nat.update_layout(height=350, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_nat, use_container_width=True)
        _workforce_chart_explanation(
            what_it_shows="يبين أكثر الجنسيات تمثيلًا في القوى العاملة.",
            current_insight="يساعد على فهم تنوع الموارد البشرية وتوزيع الاعتماد على مصادر التوظيف.",
            risk_note="التركيز المرتفع على جنسيات محددة قد يزيد حساسية المخاطر التشغيلية والتنظيمية.",
            action_recommendation="تنويع قنوات التوظيف ومراقبة التوازن بما يدعم الاستقرار والامتثال.",
        )


def _render_employee_id_validation(df) -> None:
    st.markdown("### 8) التحقق من Employee ID")
    working_df = df.copy()
    if "employee_id_status" not in working_df.columns:
        st.info("بيانات التحقق من Employee ID غير متوفرة.")
        return

    valid_count = int((working_df["employee_id_status"] == "Valid").sum())
    invalid_count = int((working_df["employee_id_status"] == "Invalid").sum())
    generated_count = int((working_df["employee_id_status"] == "Generated").sum())

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total Valid IDs", str(valid_count))
    with c2:
        kpi_card("Total Invalid IDs", str(invalid_count))
    with c3:
        kpi_card("Total Generated IDs", str(generated_count))

    invalid_rows = working_df[working_df["employee_id_status"] == "Invalid"][
        [
            "employee_id",
            "employee_name",
            "nationality",
            "employee_id_status",
            "employee_id_validation_reason",
        ]
    ].copy()
    if invalid_rows.empty:
        st.success("لا توجد Employee IDs غير صالحة حالياً.")
    else:
        st.dataframe(invalid_rows, use_container_width=True, hide_index=True)

    _arabic_explanation(
        what_it_shows="يعرض مؤشرات وصحة Employee ID وفق قاعدة بداية الرقم 1 للسعودي و2 لغير السعودي.",
        current_insight=f"عدد المعرّفات الصالحة {valid_count}، وغير الصالحة {invalid_count}، والمولدة تلقائياً {generated_count}.",
        risk_note="المعرّفات غير المطابقة قد تسبب أخطاء ربط في الأنظمة الداخلية والتقارير النظامية.",
        action_recommendation="معالجة السجلات غير الصالحة في المصدر واعتماد فحص تلقائي قبل أي رفع جديد للبيانات.",
    )


def _render_department_analysis(df) -> None:
    st.markdown("### 9) تحليل الإدارات")
    if "الإدارة" not in df.columns:
        st.info("بيانات الإدارة غير متوفرة.")
        return

    detailed_counts = df.groupby("الإدارة", as_index=False).size().rename(columns={"size": "headcount"})
    merged_counts = (
        df.groupby("الإدارة_المجمعة", as_index=False).size().rename(columns={"size": "headcount"})
        if "الإدارة_المجمعة" in df.columns
        else pd.DataFrame(columns=["الإدارة_المجمعة", "headcount"])
    )
    saudization = (
        df.groupby("الإدارة", as_index=False)["is_saudi"].mean().rename(columns={"is_saudi": "saudization_percent"})
    )
    saudization["saudization_percent"] = saudization["saudization_percent"] * 100

    c1, c2 = st.columns(2)
    with c1:
        fig_dept = px.bar(
            detailed_counts.sort_values("headcount", ascending=False),
            x="الإدارة",
            y="headcount",
            color="headcount",
            title="عدد الموظفين حسب الإدارة",
        )
        fig_dept.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig_dept, use_container_width=True)
    with c2:
        if not merged_counts.empty:
            fig_merged = px.bar(
                merged_counts.sort_values("headcount", ascending=False),
                x="الإدارة_المجمعة",
                y="headcount",
                color="headcount",
                title="عدد الموظفين حسب الإدارة المجمعة",
            )
            fig_merged.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
            st.plotly_chart(fig_merged, use_container_width=True)

    fig_saud = px.bar(
        saudization.sort_values("saudization_percent", ascending=False),
        x="الإدارة",
        y="saudization_percent",
        color="saudization_percent",
        title="نسبة السعودة حسب الإدارة",
    )
    fig_saud.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_saud, use_container_width=True)


def _render_job_title_quality(df) -> None:
    st.markdown("### 10) جودة بيانات المسميات الوظيفية")
    summary = get_job_title_quality_summary(df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("المطابقات المباشرة", str(summary["مطابق مباشر"]))
    with c2:
        kpi_card("التصحيحات التلقائية", str(summary["تم التصحيح تلقائيًا"]))
    with c3:
        kpi_card("المسميات غير المعروفة", str(summary["غير معروف"]))
    with c4:
        kpi_card("المسميات الفارغة", str(summary["فارغ"]))

    report = build_job_title_quality_report(df)
    unknown_df = report[report["حالة_المطابقة"] == "غير معروف"]
    corrected_df = report[report["حالة_المطابقة"] == "تم التصحيح تلقائيًا"]

    st.markdown("#### المسميات غير المعروفة")
    st.dataframe(unknown_df, use_container_width=True, hide_index=True)

    st.markdown("#### المسميات المصححة تلقائيًا")
    st.dataframe(corrected_df, use_container_width=True, hide_index=True)

    csv_data = report.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "تصدير تقرير الجودة (CSV)",
        data=csv_data,
        file_name="job_title_quality_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        report.to_excel(writer, index=False, sheet_name="quality_report")
    st.download_button(
        "تصدير تقرير الجودة (Excel)",
        data=excel_buffer.getvalue(),
        file_name="job_title_quality_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _arabic_explanation(
    *,
    what_it_shows: str,
    current_insight: str,
    risk_note: str,
    action_recommendation: str,
) -> None:
    st.markdown(
        f"""
        <div class="lv-card" style="margin-top:8px;">
            <div class="lv-title">توضيح تنفيذي</div>
            <div class="lv-subtitle"><b>ماذا يوضح الرسم:</b> {what_it_shows}</div>
            <div class="lv-subtitle"><b>القراءة الحالية:</b> {current_insight}</div>
            <div class="lv-subtitle"><b>ملاحظة مخاطر/امتثال:</b> {risk_note}</div>
            <div class="lv-subtitle"><b>توصية تنفيذية:</b> {action_recommendation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _workforce_chart_explanation(
    *,
    what_it_shows: str,
    current_insight: str,
    risk_note: str,
    action_recommendation: str,
) -> None:
    st.caption(f"يوضح الرسم: {what_it_shows}")
    st.caption(f"القراءة الحالية: {current_insight}")
    st.caption(f"مخاطر/امتثال: {risk_note}")
    st.caption(f"الإجراء المقترح: {action_recommendation}")
