from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.auth_service import approve_user, list_users, set_user_active
from src.ui.components import section_title


def render(_: pd.DataFrame, title: str, current_user: dict) -> None:
    section_title(title, "Approve pending users and manage account status")

    users = list_users()
    users_df = pd.DataFrame(users)
    if users_df.empty:
        st.info("No users found.")
        return

    users_df["is_approved"] = users_df["is_approved"].map(lambda x: "Yes" if x else "No")
    users_df["is_active"] = users_df["is_active"].map(lambda x: "Active" if x else "Disabled")
    st.dataframe(
        users_df[["id", "full_name", "username", "role", "is_approved", "is_active", "created_at", "approved_at"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Approve User")
    with st.form("approve_user_form"):
        user_id_to_approve = st.number_input("User ID", min_value=1, step=1)
        approve_submitted = st.form_submit_button("Approve", use_container_width=True)
        if approve_submitted:
            ok, message = approve_user(int(user_id_to_approve), int(current_user["id"]))
            if ok:
                st.success(message)
                st.rerun()
            st.error(message)

    st.markdown("#### Disable / Enable User")
    with st.form("toggle_user_status_form"):
        user_id_to_toggle = st.number_input("User ID to update", min_value=1, step=1, key="toggle_user_id")
        action = st.selectbox("Action", ["Disable", "Enable"])
        status_submitted = st.form_submit_button("Apply", use_container_width=True)
        if status_submitted:
            target_is_active = action == "Enable"
            ok, message = set_user_active(int(user_id_to_toggle), target_is_active)
            if ok:
                st.success(message)
                st.rerun()
            st.error(message)
