from fastapi import FastAPI
from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.routers import mongo_routes, sql_routes
from src.database.config import mongo_db_name, mongo_uri, mysql_url

app = FastAPI(
    title="Energy Forecasting Pipeline API",
    description="CRUD API for both MySQL and MongoDB energy data.",
    version="1.0.0",
)

app.include_router(sql_routes.router, prefix="/api/sql", tags=["SQL"])
app.include_router(mongo_routes.router, prefix="/api/mongo", tags=["MongoDB"])
