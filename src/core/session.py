import streamlit as st


def initialize_session_state() -> None:
    defaults = {
        "authenticated": False,
        "current_user": None,
        "language": "Arabic",
        "active_page": "Executive Dashboard",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state["current_user"] = None
    st.session_state["active_page"] = "Executive Dashboard"
