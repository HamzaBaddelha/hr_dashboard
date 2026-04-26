import streamlit as st
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config.settings import APP_ICON, APP_NAME, COMPANY_LOGO_PATH, COMPANY_NAME
from src.core.database import initialize_database
from src.core.session import initialize_session_state, logout
from src.pages import admin_user_management, contracts, executive_dashboard, iqama_monitoring, overview, salaries_insurance, saudization, workforce_insights
from src.services.auth_service import authenticate_user, ensure_default_admin, get_user_by_id, register_user
from src.services.data_pipeline_service import get_dashboard_dataset
from src.ui.theme import inject_global_styles
from src.utils.i18n import t


def _resolve_page_icon():
    icon_value = APP_ICON
    if isinstance(icon_value, str):
        maybe_file = Path(icon_value)
        if maybe_file.suffix and not maybe_file.exists():
            return "🚘"
    return icon_value or "🚘"


st.set_page_config(
    page_title=APP_NAME,
    page_icon=_resolve_page_icon(),
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_auth_screen(language: str) -> None:
    _render_company_logo(width=520)
    st.title(t(language, "app_title"))
    st.caption(t(language, "auth_subtitle"))
    login_tab, register_tab = st.tabs([t(language, "login"), t(language, "register")])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input(t(language, "username"))
            password = st.text_input(t(language, "password"), type="password")
            submitted = st.form_submit_button(t(language, "login_button"), use_container_width=True)
            if submitted:
                is_ok, message, user = authenticate_user(username, password)
                if is_ok and user:
                    st.session_state["authenticated"] = True
                    st.session_state["current_user"] = user
                    st.success(message)
                    st.rerun()
                st.error(message)

    with register_tab:
        with st.form("register_form"):
            full_name = st.text_input(t(language, "full_name"))
            username = st.text_input(t(language, "username"), key="reg_username")
            password = st.text_input(t(language, "password"), type="password", key="reg_password")
            requested_role = st.selectbox("Role", ["hr_user", "viewer"], index=1)
            submitted = st.form_submit_button(t(language, "register_button"), use_container_width=True)
            if submitted:
                ok, message = register_user(full_name, username, password, role=requested_role)
                if ok:
                    st.success(message)
                else:
                    st.error(message)


def render_app(language: str) -> None:
    user = st.session_state["current_user"]
    is_admin = user.get("role") == "admin"

    uploaded_file = st.sidebar.file_uploader(
        "رفع ملف الموارد البشرية (Excel)",
        type=["xlsx", "xls"],
        help="ارفع ملف HR وسيتم تنظيف البيانات وحساب المؤشرات تلقائياً.",
    )

    try:
        df, source = get_dashboard_dataset(uploaded_file)
    except Exception as exc:
        st.error(f"تعذر قراءة الملف المرفوع: {exc}")
        return

    page_map = {
        "Executive Dashboard": (t(language, "executive_dashboard"), executive_dashboard.render),
        "Overview": (t(language, "overview"), overview.render),
        "Saudization": (t(language, "saudization"), saudization.render),
        "Iqama Monitoring": (t(language, "iqama"), iqama_monitoring.render),
        "Contracts": (t(language, "contracts"), contracts.render),
        "Salaries & Insurance": (t(language, "salary_insurance"), salaries_insurance.render),
        "Workforce Insights": (t(language, "workforce_insights"), workforce_insights.render),
    }
    if is_admin:
        page_map["User Management"] = ("User Management", admin_user_management.render)

    _render_company_logo(width=320)
    _render_saudi_datetime()
    st.sidebar.markdown(f"## {COMPANY_NAME}")
    _render_company_logo(width=220, in_sidebar=True)
    st.sidebar.caption(_get_saudi_datetime_text())
    st.sidebar.caption(f"{t(language, 'welcome')}, {user['full_name']} ({user['role']})")
    st.sidebar.caption("مصدر البيانات: ملف مرفوع" if source == "uploaded" else "مصدر البيانات: عينة تجريبية")

    current_page = st.session_state["active_page"]
    if current_page not in page_map:
        current_page = "Executive Dashboard"
        st.session_state["active_page"] = current_page

    selected_page = st.sidebar.radio(
        t(language, "navigation"),
        list(page_map.keys()),
        index=list(page_map.keys()).index(current_page),
    )
    st.session_state["active_page"] = selected_page

    if st.sidebar.button(t(language, "logout"), use_container_width=True):
        logout()
        st.rerun()

    page_title, page_renderer = page_map[selected_page]
    if selected_page == "User Management":
        page_renderer(df, page_title, user)
    else:
        page_renderer(df, page_title)


def _render_company_logo(*, width: int = 260, in_sidebar: bool = False) -> None:
    if not COMPANY_LOGO_PATH.exists():
        return
    if in_sidebar:
        st.sidebar.image(str(COMPANY_LOGO_PATH), width=width)
        return
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.image(str(COMPANY_LOGO_PATH), width=width)


def _get_saudi_datetime_text() -> str:
    try:
        now = datetime.now(ZoneInfo("Asia/Riyadh"))
    except Exception:
        now = datetime.utcnow()
    return f"Saudi Arabia Time: {now.strftime('%Y-%m-%d %I:%M %p')}"


def _render_saudi_datetime() -> None:
    st.markdown(
        f"""
        <div class="lv-card" style="margin-top:4px;">
            <div class="lv-title">التاريخ والوقت - المملكة العربية السعودية</div>
            <div class="lv-value" style="font-size:1.25rem;">{_get_saudi_datetime_text()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    try:
        initialize_database()
        ensure_default_admin()
        initialize_session_state()

        language = st.sidebar.selectbox(
            t(st.session_state["language"], "language"),
            ["Arabic", "English"],
            index=0 if st.session_state["language"] == "Arabic" else 1,
        )
        st.session_state["language"] = language

        inject_global_styles(language)

        if not st.session_state["authenticated"]:
            render_auth_screen(language)
            return

        current_user = st.session_state.get("current_user")
        if not current_user:
            logout()
            st.rerun()
            return

        fresh_user = get_user_by_id(int(current_user["id"]))
        if not fresh_user:
            logout()
            st.warning("Your account was not found. Please login again.")
            st.rerun()
            return

        if not bool(fresh_user["is_active"]):
            logout()
            st.warning("Your account is disabled. Please contact admin.")
            st.rerun()
            return

        if fresh_user["role"] != "admin" and not bool(fresh_user["is_approved"]):
            logout()
            st.warning("Your account is pending admin approval.")
            st.rerun()
            return

        st.session_state["current_user"] = fresh_user

        render_app(language)
    except Exception as exc:
        st.error(f"Startup error: {exc}")
        st.exception(exc)


if __name__ == "__main__":
    main()
