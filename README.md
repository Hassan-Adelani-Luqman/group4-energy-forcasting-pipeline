# Group 4 — Energy Forecasting Pipeline

End-to-end time series pipeline for the [PJM Hourly Energy Consumption](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption) dataset (PJME + AEP regions): EDA & forecasting models -> MySQL + MongoDB storage -> FastAPI CRUD -> forecast script that writes predictions back through the API.

**Repository:** https://github.com/Hassan-Adelani-Luqman/group4-energy-forecasting-pipeline

## Team & Roles

| Member | Task | Branch |
|---|---|---|
| Hassan Adelani Luqman | Task 1 — EDA, preprocessing, modeling | `phase1-eda` |
| AbdalazizI Twariki | Task 2 — SQL + MongoDB design & implementation | `databases` |
| Nkhomotabo Amazing Mkhonta | Task 3 — CRUD API for both databases | `phase3-api` |
| Parfait Shema Semana | Task 4 — Forecast script | `phase4-forecast` |

## Repo Structure

| Path | Contents |
|---|---|
| `data/{raw,processed}/` | Raw Kaggle CSVs (manual) + Task 1's feature-engineered output (gitignored) |
| `notebooks/` | Task 1 EDA & preprocessing notebook |
| `src/preprocessing/` | `clean.py` (gap-filling) + `features.py` (calendar/lag/rolling features) |
| `src/models/` | `train.py` / `evaluate.py` + saved model artifacts |
| `src/database/sql/` | MySQL `schema.sql`, `load_mysql.py`, `queries.sql`, captured `query_results.md` |
| `src/database/mongodb/` | `setup.py`, `queries.py`, `sample_documents.json` |
| `src/api/` | FastAPI app, routers (`sql_routes.py`, `mongo_routes.py`), `api_examples.md` |
| `src/forecast/` | `run_forecast.py` + captured `forecast_example.md` |
| `docs/erd.mmd` | Mermaid ERD for the MySQL schema |
| `reports/` | `report.pdf` + `figures/` used in the report |

## Setup

1. Clone the repo and create a Python virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and adjust values if needed.
3. Start local MySQL + MongoDB:
   ```
   docker-compose up -d
   ```
4. Download the PJME and AEP CSVs from the [Kaggle dataset](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption) and place them in `data/raw/`.
5. Run the EDA notebook: `notebooks/01_eda_and_preprocessing.ipynb` — this trains the models and writes
   `data/processed/*.csv` (used by Task 2) and `src/models/artifacts/*.joblib` (used by Task 4).
6. Load the databases:
   ```
   python -m src.database.sql.load_mysql
   python -m src.database.mongodb.setup
   ```

## Running the API

```
uvicorn src.api.main:app --reload
```
Interactive docs available at `http://localhost:8000/docs`.

## Running the forecast script

With the API running (above):
```
python -m src.forecast.run_forecast              # both regions
python -m src.forecast.run_forecast --region PJME  # single region
```
Fetches a trailing window through the API, engineers features with Task 1's pipeline, predicts with the Task 1
model, and writes the result back to both `/predictions` endpoints. See
[src/forecast/forecast_example.md](src/forecast/forecast_example.md) for a captured example run.
