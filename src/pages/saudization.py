import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_saudization_by_department
from src.ui.components import section_title
from src.utils.formatters import format_percent


def render(df, title: str) -> None:
    section_title(title, "تحليل السعودة حسب الإدارات مع مقارنة المستهدف")
    saudization_df = get_saudization_by_department(df)
    company_rate = (df["is_saudi"].mean() * 100) if len(df) else 0

    st.metric("نسبة السعودة على مستوى الشركة", format_percent(company_rate))

    fig = px.bar(
        saudization_df,
        x="department",
        y="saudization_rate",
        color="target_status",
        color_discrete_map={"Met": "#22C55E", "Below Target": "#F59E0B", "N/A": "#60A5FA"},
        title="نسب السعودة حسب الإدارة",
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)

    styled_df = saudization_df.copy()
    styled_df["saudization_rate"] = styled_df["saudization_rate"].map(lambda x: f"{x:.1f}%")
    styled_df["target_rate"] = styled_df["target_rate"].map(lambda x: "-" if x != x else f"{x:.1f}%")
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    st.caption("المستهدفات الخاصة: إدارة التسويق 60%، وإدارة المحاسبة 50%.")
