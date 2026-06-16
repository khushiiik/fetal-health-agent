# Fetal Health Multi-Agent Monitoring System

This project is a lightweight, multi-agent monitoring dashboard built to analyze fetal health records and provide automated diagnostics. It consists of:
- A FastAPI backend running a multi-agent orchestration pipeline.
- A Streamlit frontend dashboard rendering live status updates and console tool logs.

---

## Prerequisites

- **Python**: version 3.11+
- **Google Gemini API Key** (for agent reasoning models)

---

## Installation & Setup

1. **Clone the repository** and navigate to the project directory:
   ```bash
   cd fetal_health_agent
   ```

2. **Create and activate a virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration (`.env`)

Copy `.env.example` to create your local `.env` file:
```bash
cp .env.example .env
```

Open `.env` and fill out the configuration values.

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API Key. |
| `GEMINI_MODEL` | Gemini model name (default: `gemini-2.0-flash`). |
| `DATA_SOURCE` | Set to `mock` or `bigquery` (see details below). |
| `MOCK_DATA_PATH` | Directory containing mock local files (`data/mock`). |
| `CLINICAL_DATA_PATH` | Path to reference range clinical guidelines JSON. |
| `ADK_MAX_ITERATIONS` | Safety cap for maximum agent tool iterations (default: `10`). |
| `AGENT_TIMEOUT_SECONDS` | Maximum runtime timeout for agents in seconds (default: `60`). |
| `STREAMLIT_PORT` | Frontend dashboard port (default: `8501`). |

---

## Data Source Modes

The system supports running in two distinct modes using the `DATA_SOURCE` environment variable:

### 1. Mock Mode (Default)
In mock mode, the system retrieves fetal vitals and record sheets locally from mock CSV files without needing any cloud connection.

* **Configuration in `.env`**:
  ```ini
  DATA_SOURCE=mock
  MOCK_DATA_PATH=data/mock
  ```

### 2. BigQuery Mode
In BigQuery mode, the system queries live GCP BigQuery tables to extract patient records and fetal health indicators.

* **Configuration in `.env`**:
  ```ini
  DATA_SOURCE=bigquery
  BIGQUERY_PROJECT_ID=your_bigquery_project_id
  BIGQUERY_DATASET=your_bigquery_dataset
  BIGQUERY_TABLE=your_bigquery_table
  GOOGLE_CLOUD_PROJECT=your_google_cloud_project
  GOOGLE_APPLICATION_CREDENTIALS=credentials/fetal-health-service.json
  ```
* **Authentication**: Store your GCP Service Account JSON key inside the `credentials/` folder and update `GOOGLE_APPLICATION_CREDENTIALS` to point to it.

---

## Running the Application

Ensure your virtual environment is activated, then run the services:

### 1. Start the Backend API (FastAPI)
Run the backend server from the project root:
```bash
uvicorn app.main:app --reload
```
The FastAPI documentation will be available at `http://127.0.0.1:8000/docs`.

### 2. Start the Frontend Dashboard (Streamlit)
Run the monitoring UI from the project root:
```bash
streamlit run streamlit_ui/app.py
```
Or navigate into the `streamlit_ui` folder and run:
```bash
cd streamlit_ui
streamlit run app.py
```
The Streamlit server will start on `http://localhost:8501`.

---

## Verification & QA Check

To format the code and run the full test suite, execute the QA runner:
```bash
python run_qa.py
```
This runs:
- `black` (Formatting check)
- `isort` (Import sorting check)
- `ruff` (Linting checks)
- `mypy` (Type checking check)
- `pytest` (Unit testing and coverage reporting)
