import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_overview_metrics
from src.ui.components import kpi_card, section_title
from src.utils.formatters import format_currency, format_percent


def render(df, title: str) -> None:
    section_title(title, "Company-wide headcount and payroll snapshot")
    metrics = get_overview_metrics(df)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Headcount", str(metrics["total_headcount"]))
    with col2:
        kpi_card("Saudization Rate", format_percent(metrics["saudization_rate"]))
    with col3:
        kpi_card("Average Salary", format_currency(metrics["avg_salary"]))
    with col4:
        kpi_card("Avg Performance", f'{metrics["avg_performance"]:.2f} / 5.00')

    c1, c2 = st.columns(2)
    with c1:
        dept_counts = df.groupby("department", as_index=False).size().rename(columns={"size": "headcount"})
        fig = px.bar(
            dept_counts,
            x="department",
            y="headcount",
            color="headcount",
            color_continuous_scale="Tealgrn",
            title="Headcount by Department",
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.pie(
            df,
            names="gender",
            title="Gender Distribution",
            color_discrete_sequence=["#C8A14D", "#60A5FA"],
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig, use_container_width=True)
