from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from src.api.dependencies import get_mongo_db
from src.api.schemas import MongoPredictionCreate, MongoReadingCreate, MongoReadingUpdate

router = APIRouter()

DAILY_COL = "energy_daily"
PRED_COL = "predictions"

@router.get("/readings")
def get_readings(limit: int = 10, db: Database = Depends(get_mongo_db)):
    cursor = db[DAILY_COL].find({}, {"_id": 0}).sort("date", -1).limit(limit)
    return list(cursor)

@router.get("/readings/latest")
def get_latest_reading(region_code: str, db: Database = Depends(get_mongo_db)):
    doc = db[DAILY_COL].find_one({"region_code": region_code}, {"_id": 0}, sort=[("date", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Reading not found")
    return doc

@router.get("/readings/range")
def get_readings_range(region_code: str, start_date: datetime, end_date: datetime, db: Database = Depends(get_mongo_db)):
    query = {
        "region_code": region_code,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    cursor = db[DAILY_COL].find(query, {"_id": 0}).sort("date", 1)
    return list(cursor)

@router.get("/readings/{region_code}/{date}")
def get_reading(region_code: str, date: datetime, db: Database = Depends(get_mongo_db)):
    doc = db[DAILY_COL].find_one({"region_code": region_code, "date": date}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Reading not found")
    return doc

@router.post("/readings")
def create_reading(region_code: str, date: datetime, reading: MongoReadingCreate, db: Database = Depends(get_mongo_db)):
    # Update the embedded array for the specific day
    result = db[DAILY_COL].update_one(
        {"region_code": region_code, "date": date},
        {"$push": {"hourly_readings": reading.model_dump()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Day document not found for this region and date")
    return {"message": "Reading added"}

@router.put("/readings/{region_code}/{date}/{hour}")
def update_reading(region_code: str, date: datetime, hour: int, reading: MongoReadingUpdate, db: Database = Depends(get_mongo_db)):
    update_data = {f"hourly_readings.$.{k}": v for k, v in reading.model_dump(exclude_unset=True).items()}
    if not update_data:
        return {"message": "No fields to update"}
    
    result = db[DAILY_COL].update_one(
        {"region_code": region_code, "date": date, "hourly_readings.hour": hour},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reading not found")
    return {"message": "Reading updated"}

@router.delete("/readings/{region_code}/{date}/{hour}")
def delete_reading(region_code: str, date: datetime, hour: int, db: Database = Depends(get_mongo_db)):
    result = db[DAILY_COL].update_one(
        {"region_code": region_code, "date": date},
        {"$pull": {"hourly_readings": {"hour": hour}}}
    )
    if result.matched_count == 0 or result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Reading not found")
    return {"message": "Reading deleted"}

@router.post("/predictions")
def create_prediction(prediction: MongoPredictionCreate, db: Database = Depends(get_mongo_db)):
    pred_data = prediction.model_dump()
    pred_data["generated_at"] = datetime.utcnow()
    db[PRED_COL].insert_one(pred_data)
    
    # Remove _id for return
    pred_data.pop("_id", None)
    return pred_data
