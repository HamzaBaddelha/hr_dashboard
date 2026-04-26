import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_salary_insurance_summary
from src.ui.components import kpi_card, section_title
from src.utils.formatters import format_currency, format_percent


def render(df, title: str) -> None:
    section_title(title, "Payroll, insurance cost, and compensation distribution")
    summary = get_salary_insurance_summary(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card("Total Payroll", format_currency(summary["total_payroll"]))
    with col2:
        kpi_card("Total Insurance", format_currency(summary["total_insurance"]))
    with col3:
        kpi_card("Insurance Ratio", format_percent(summary["insurance_ratio"]))

    df_line = df.groupby("department")["salary"].mean().reset_index()

    fig = px.line(
        df_line,
        x="department",
        y="salary",
        markers=True,
        title="Average Salary by Department",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)