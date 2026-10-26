# Group 4 — Energy Forecasting Pipeline

End-to-end time series pipeline for the [PJM Hourly Energy Consumption](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption) dataset (PJME + AEP regions): EDA & forecasting models -> MySQL + MongoDB storage -> FastAPI CRUD -> forecast script that writes predictions back through the API.

**Repository:** https://github.com/Hassan-Adelani-Luqman/group4-energy-forcasting-pipeline

**Report:** [reports/report.pdf](reports/report.pdf)

## Team & Roles

| # | Member | Task | Responsibilities | Main Code |
|:-:|---|---|---|---|
| 1 | **Hassan Adelani Luqman** | Task 1 — Time-Series EDA, Preprocessing & Modeling | Data cleaning, exploratory analysis, analytical questions, feature engineering, model training & tuning | `notebooks/`, `src/preprocessing/`, `src/models/` |
| 2 | **Abdalaziz Twariki** | Task 2 — Database Design | MySQL schema & ERD, MongoDB collection design, data loading, demonstration queries | `src/database/`, `docs/erd.mmd` |
| 3 | **Nkhomotabo Amazing Mkhonta** | Task 3 — CRUD & Time-Series API | FastAPI CRUD endpoints for MySQL and MongoDB, latest-record and date-range queries | `src/api/` |
| 4 | **Parfait Shema Semana** | Task 4 — Forecast Script | Fetch data from the API, preprocess, load the trained model, predict and write the forecast back | `src/forecast/` |

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
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # macOS / Linux
   pip install -r requirements.txt
   ```
   Package versions are pinned to the ones the pipeline was tested with (Python 3.12).
2. Copy `.env.example` to `.env` and adjust values if needed.
3. Start local MySQL + MongoDB:
   ```
   docker-compose up -d
   ```
4. Download the PJME and AEP CSVs from the [Kaggle dataset](https://www.kaggle.com/datasets/robikscube/hourly-energy-consumption) and place them in `data/raw/`.
5. Run the EDA notebook: `notebooks/01_eda_and_preprocessing.ipynb` — this cleans the raw series, answers the
   analytical questions, saves figures to `reports/figures/`, and writes `data/processed/*.csv` (used by Task 2).
6. Train the models (Linear Regression baseline vs tuned XGBoost, per region):
   ```
   python -m src.models.train
   ```
   This writes the experiment table to `src/models/artifacts/experiment_results.csv` and the winning model per
   region to `src/models/artifacts/*.joblib` (used by Task 4). Both trained models are already committed, so this
   step is only needed to reproduce the experiments.
7. Load the databases:
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
model, and writes the result back to both `/predictions` endpoints. The API address comes from `API_BASE_URL` in
`.env` (default `http://localhost:8000`) and can be overridden with `--api-base`. Re-running for an hour that is
already predicted is skipped with a warning (the API returns `409 Conflict`). See
[src/forecast/forecast_example.md](src/forecast/forecast_example.md) for a captured example run.

## Results

| Region | Model | Test RMSE (MW) | Test MAPE |
|---|---|---|---|
| PJME | Linear Regression (baseline) | 1627.4 | 3.84% |
| PJME | **XGBoost (tuned)** | **537.7** | **1.08%** |
| AEP | Linear Regression (baseline) | 575.6 | 3.10% |
| AEP | **XGBoost (tuned)** | **188.5** | **0.90%** |

Full experiment table: [src/models/artifacts/experiment_results.csv](src/models/artifacts/experiment_results.csv).
