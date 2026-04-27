# Luxury Vehicle - HR Analytics Dashboard

Production-ready internal HR analytics dashboard built with Python + Streamlit.

## Features

- Secure login and registration with SQLite + salted password hashing.
- Clean modular architecture and reusable page components.
- Arabic-friendly UI (RTL styling) with language switch.
- Sidebar navigation across six business pages:
  - Overview
  - Saudization
  - Iqama Monitoring
  - Contracts
  - Salaries & Insurance
  - Workforce Insights

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
.. or
python -m streamlit run app.py
```

## Environment & Packages

- Python version: `3.11` (from `runtime.txt`)
- Entry point: `app.py`
- Main dependencies (from `requirements.txt`):
  - `streamlit==1.45.1`
  - `pandas==2.2.3`
  - `plotly==5.24.1`
  - `bcrypt==4.2.1`
  - `openpyxl==3.1.5`

## Project Structure

```text
dashboard/
├── .streamlit/
│   └── config.toml
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── session.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── hr_data_loader.py
│   │   └── sample_data.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── admin_user_management.py
│   │   ├── contracts.py
│   │   ├── executive_dashboard.py
│   │   ├── iqama_monitoring.py
│   │   ├── overview.py
│   │   ├── salaries_insurance.py
│   │   ├── saudization.py
│   │   └── workforce_insights.py
│   ├── public/
│   │   └── assets/
│   │       ├── company_logo.png
│   │       └── hiring.png
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── data_pipeline_service.py
│   │   └── hr_metrics_service.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── components.py
│   │   └── theme.py
│   └── utils/
│       ├── __init__.py
│       ├── cleaner.py
│       ├── formatters.py
│       └── i18n.py
├── .gitignore
├── app.py
├── README.md
├── requirements.txt
└── runtime.txt
```
