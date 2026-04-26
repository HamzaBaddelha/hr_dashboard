import streamlit as st


def inject_global_styles(language: str) -> None:
    is_arabic = language == "Arabic"
    direction = "rtl" if is_arabic else "ltr"
    text_align = "right" if is_arabic else "left"
    sidebar_align = "right" if is_arabic else "left"

    st.markdown(
        f"""
        <style>
            .stApp {{
                background: radial-gradient(circle at 20% 20%, #1f2937 0%, #0b1220 45%, #060b14 100%);
            }}
            [data-testid="stAppViewContainer"] {{
                direction: {direction};
                text-align: {text_align};
            }}
            [data-testid="stSidebar"] * {{
                text-align: {sidebar_align};
            }}
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] h1,
            [data-testid="stMarkdownContainer"] h2,
            [data-testid="stMarkdownContainer"] h3,
            [data-testid="stMarkdownContainer"] h4 {{
                direction: {direction};
                text-align: {text_align};
            }}
            .lv-card {{
                border-radius: 14px;
                border: 1px solid rgba(200, 161, 77, 0.35);
                background: rgba(17, 24, 39, 0.75);
                backdrop-filter: blur(8px);
                padding: 16px 18px;
                margin-bottom: 10px;
            }}
            .lv-title {{
                font-size: 1.05rem;
                color: #e5e7eb;
                margin-bottom: 0.4rem;
            }}
            .lv-value {{
                font-size: 1.7rem;
                font-weight: 700;
                color: #f3f4f6;
            }}
            .lv-subtitle {{
                color: #9ca3af;
                font-size: 0.9rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
