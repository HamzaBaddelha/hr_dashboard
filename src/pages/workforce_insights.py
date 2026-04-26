import plotly.express as px
import streamlit as st

from src.services.hr_metrics_service import get_workforce_insights
from src.ui.components import section_title


def render(df, title: str) -> None:
    section_title(title, "Workforce composition, tenure, and performance trends")
    insights = get_workforce_insights(df)

    col1, col2 = st.columns(2)
    with col1:
        fig_city = px.bar(
            insights["headcount_by_city"],
            x="city",
            y="headcount",
            color="headcount",
            color_continuous_scale="Sunset",
            title="Headcount by City",
        )
        fig_city.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig_city, use_container_width=True)
    with col2:
        fig_gender = px.pie(
            insights["gender_distribution"],
            names="gender",
            values="count",
            title="Gender Mix",
            color_discrete_sequence=["#60A5FA", "#F472B6"],
        )
        fig_gender.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
        st.plotly_chart(fig_gender, use_container_width=True)

    fig_perf = px.bar(
        insights["performance_by_department"],
        x="department",
        y="performance_score",
        color="performance_score",
        color_continuous_scale="Viridis",
        title="Average Performance by Department",
    )
    fig_perf.update_layout(height=390, margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_perf, use_container_width=True)
    st.caption("يوضح هذا الرسم متوسط تقييم الأداء في كل إدارة، ويساعد على مقارنة الفروقات بين الإدارات.")
    st.caption("القراءة الحالية: تقارب القيم يدل على ثبات نسبي، بينما أي تباين واضح يشير إلى فجوات أداء تحتاج متابعة.")
    st.caption("التوصية: مراجعة الإدارات الأقل أداءً بخطط تطوير مستهدفة وربط النتائج بمؤشرات الأداء الشهرية.")
