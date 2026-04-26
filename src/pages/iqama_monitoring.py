import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_iqama_status
from src.ui.components import section_title


def render(df, title: str) -> None:
    section_title(title, "متابعة صلاحية الإقامات للموظفين غير السعوديين")
    iqama_df = get_iqama_status(df)

    status_summary = iqama_df.groupby("iqama_status", as_index=False).size().rename(columns={"size": "count"})
    fig = px.bar(
        status_summary,
        x="iqama_status",
        y="count",
        color="iqama_status",
        title="حالة امتثال الإقامات",
        color_discrete_map={
            "Expired": "#EF4444",
            "Due in 30 days": "#F59E0B",
            "Due in 90 days": "#38BDF8",
            "Valid": "#22C55E",
        },
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=55, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    risk_list = iqama_df[iqama_df["iqama_status"].isin(["Expired", "Due in 30 days", "Due in 90 days"])].sort_values(
        "iqama_days_remaining"
    )
    style_map = {
        "Expired": "background-color: #7f1d1d; color: #fecaca;",
        "Due in 30 days": "background-color: #78350f; color: #fde68a;",
        "Due in 90 days": "background-color: #0f766e; color: #ccfbf1;",
    }
    view = risk_list[
        [
            "employee_id",
            "employee_name",
            "department",
            "nationality",
            "iqama_days_remaining",
            "iqama_expiry_date",
            "iqama_status",
        ]
    ]
    st.dataframe(
        view.style.map(lambda value: style_map.get(value, ""), subset=["iqama_status"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("الأحمر = منتهية، البرتقالي = حرجة خلال 30 يوم، الأخضر = متابعة خلال 90 يوم.")
