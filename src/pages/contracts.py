import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_contract_status
from src.ui.components import section_title


def render(df, title: str) -> None:
    section_title(title, "متابعة انتهاء العقود وخطط التجديد")
    contracts_df = get_contract_status(df)

    summary = contracts_df.groupby("contract_status", as_index=False).size().rename(columns={"size": "count"})
    fig = px.pie(
        summary,
        names="contract_status",
        values="count",
        title="توزيع حالة العقود",
        color="contract_status",
        color_discrete_map={
            "Expired": "#EF4444",
            "Ending in 60 days": "#F59E0B",
            "Ending in 120 days": "#38BDF8",
            "Active": "#22C55E",
        },
    )
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)

    renewals = contracts_df[
        contracts_df["contract_status"].isin(["Expired", "Ending in 60 days", "Ending in 120 days"])
    ].sort_values(
        "contract_days_remaining"
    )
    style_map = {
        "Expired": "background-color: #7f1d1d; color: #fecaca;",
        "Ending in 60 days": "background-color: #78350f; color: #fde68a;",
        "Ending in 120 days": "background-color: #0f766e; color: #ccfbf1;",
    }
    view = renewals[
        [
            "employee_id",
            "employee_name",
            "department",
            "contract_days_remaining",
            "contract_end_date",
            "job_family",
            "contract_status",
        ]
    ]
    st.dataframe(
        view.style.map(lambda value: style_map.get(value, ""), subset=["contract_status"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("الأحمر = منتهي، البرتقالي = ينتهي خلال 60 يوم، الأخضر = متابعة خلال 120 يوم.")
