"""Shared database connection settings for Phase 2 (MySQL + MongoDB).

Reads from the project ``.env`` (see ``.env.example``) so the SQL loader,
the Mongo setup script, and the Phase 3 API all resolve connections the
same way. Nothing here opens a connection on import.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = three levels up from this file (src/database/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

load_dotenv(PROJECT_ROOT / ".env")


def mysql_url() -> str:
    """SQLAlchemy connection URL for the MySQL database."""
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_ROOT_PASSWORD", "rootpass")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = os.getenv("MYSQL_PORT", "3306")
    db = os.getenv("MYSQL_DATABASE", "energy_pipeline")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"


def mongo_uri() -> str:
    """Connection URI for MongoDB."""
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    return f"mongodb://{host}:{port}"


def mongo_db_name() -> str:
    return os.getenv("MONGO_DATABASE", "energy_pipeline")


# The two regions Phase 1 exported to data/processed/. region_code -> metadata.
REGIONS = {
    "PJME": {
        "region_name": "PJM East",
        "description": "PJM Interconnection eastern region hourly load (MW)",
        "processed_file": "pjme_hourly_processed.csv",
    },
    "AEP": {
        "region_name": "American Electric Power",
        "description": "AEP service territory hourly load (MW)",
        "processed_file": "aep_hourly_processed.csv",
    },
}
