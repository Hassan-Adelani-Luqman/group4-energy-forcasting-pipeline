from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.config import mongo_db_name, mongo_uri, mysql_url

# SQL Setup
engine = create_engine(mysql_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_sql_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mongo Setup
mongo_client = MongoClient(mongo_uri())
mongo_db = mongo_client[mongo_db_name()]

def get_mongo_db():
    yield mongo_db
