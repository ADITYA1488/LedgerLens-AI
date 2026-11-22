# LedgerLens AI

LedgerLens AI is a financial intelligence demo for exploring working-capital trends, forecasts, heuristic risk indicators, and investigation actions across three business entities.

## Features and architecture

- Static dashboard in `frontend/`, with Chart.js trend and forecast chart.
- FastAPI service in `main.py` for analytics, forecasts, actions, dataset upload, and multi-agent analysis.
- LangGraph workflow in `backend/agents/`; Gemini reasoning is optional and uses deterministic, evidence-based analysis when no key is configured.
- Optional Groq-backed chat service in `backend/api/main.py`.
- CSV data and model selection are loaded from the configured paths below.

## Run locally

Use Python 3.10 or later. From the repository root, install dependencies and copy the environment template:

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Place `DD-WCP-003_FactMonthlyPL.csv` in `data/dataset/`, or set `LEDGERLENS_DATA_DIR` to its containing directory. Then run these in separate terminals from the repository root:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
python -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8001
python -m http.server 5500 --directory frontend
```

Open `http://127.0.0.1:5500`. The dashboard and analysis API use port 8000; the optional chat widget uses port 8001. Check `http://127.0.0.1:8000/health` and `http://127.0.0.1:8001/health` for service health.

## Environment variables

- `LEDGERLENS_DATA_DIR`: dataset directory; defaults to `data/dataset`.
- `LEDGERLENS_SELECTION_FILE`: model-selection CSV; defaults to `experiments/selected_forecasting_models.csv`.
- `LEDGERLENS_PROJECT_ROOT`: optional project root override.
- `GEMINI_API_KEY`: optional; enables Gemini-backed analysis. Without it, the analysis workflow uses its deterministic fallback and identifies that mode in the result.
- `GEMINI_MODEL`: optional model name; defaults to `gemini-2.5-flash`.
- `LLM_TEMPERATURE`: optional model temperature; defaults to `0.2`.
- `GROQ_API_KEY`: required only when using chat.

Keep real keys in the ignored `.env` file. `.env.example` contains placeholders only.

## Demo data and limitations

The bundled DD-WCP-003 data is synthetic demonstration data, not real company transactions. The dashboard labels the demo accordingly. Risk scores are heuristic indicators, not probabilities. Forecasts and metrics are demonstrations and are not financial advice or validated predictions for a real business.

## 60-second demo walkthrough

1. Show the dashboard KPI cards and the synthetic-data badge (10 seconds).
2. Point out the historical trend and forecast line; switch entities or forecast metrics (15 seconds).
3. Run the suggested AI investigation and show the financial snapshot and trends (15 seconds).
4. Scroll through risk indicators, recommended investigation steps, and the agent trace (20 seconds).

## Submission description

LedgerLens AI is an explainable working-capital intelligence demo that combines historical financial analytics, forecasting, multi-agent investigation, and actionable heuristic risk indicators in one dashboard. It is built to help small and midsize businesses explore cash-flow drivers while making evidence, assumptions, and synthetic-data limitations visible.
