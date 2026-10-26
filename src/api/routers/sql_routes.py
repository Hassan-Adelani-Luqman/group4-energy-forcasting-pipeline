from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.dependencies import get_sql_db
from src.api.schemas import (
    PredictionCreate,
    PredictionResponse,
    ReadingCreate,
    ReadingResponse,
    ReadingUpdate,
)

router = APIRouter()

@router.get("/readings", response_model=List[ReadingResponse])
def get_readings(limit: int = 100, db: Session = Depends(get_sql_db)):
    query = text("SELECT * FROM energy_readings ORDER BY reading_ts DESC LIMIT :limit")
    result = db.execute(query, {"limit": limit}).mappings().all()
    return result

@router.get("/readings/latest", response_model=ReadingResponse)
def get_latest_reading(region_id: int, db: Session = Depends(get_sql_db)):
    query = text("SELECT * FROM energy_readings WHERE region_id = :region_id ORDER BY reading_ts DESC LIMIT 1")
    result = db.execute(query, {"region_id": region_id}).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="Reading not found")
    return dict(result)

@router.get("/readings/range", response_model=List[ReadingResponse])
def get_readings_range(region_id: int, start_date: datetime, end_date: datetime, db: Session = Depends(get_sql_db)):
    query = text("SELECT * FROM energy_readings WHERE region_id = :region_id AND reading_ts >= :start_date AND reading_ts <= :end_date ORDER BY reading_ts ASC")
    result = db.execute(query, {"region_id": region_id, "start_date": start_date, "end_date": end_date}).mappings().all()
    return result

@router.get("/readings/{reading_id}", response_model=ReadingResponse)
def get_reading(reading_id: int, db: Session = Depends(get_sql_db)):
    query = text("SELECT * FROM energy_readings WHERE reading_id = :reading_id")
    result = db.execute(query, {"reading_id": reading_id}).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="Reading not found")
    return dict(result)

@router.post("/readings", response_model=ReadingResponse)
def create_reading(reading: ReadingCreate, db: Session = Depends(get_sql_db)):
    query = text("""
        INSERT INTO energy_readings (region_id, reading_ts, mw, lag_1h, lag_24h, lag_168h, rolling_mean_24h, rolling_mean_7d, rolling_std_24h, split)
        VALUES (:region_id, :reading_ts, :mw, :lag_1h, :lag_24h, :lag_168h, :rolling_mean_24h, :rolling_mean_7d, :rolling_std_24h, :split)
    """)
    res = db.execute(query, reading.model_dump())
    db.commit()
    return get_reading(res.lastrowid, db)

@router.put("/readings/{reading_id}", response_model=ReadingResponse)
def update_reading(reading_id: int, reading: ReadingUpdate, db: Session = Depends(get_sql_db)):
    update_data = reading.model_dump(exclude_unset=True)
    if not update_data:
        return get_reading(reading_id, db)
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE energy_readings SET {set_clause} WHERE reading_id = :reading_id")
    update_data["reading_id"] = reading_id
    db.execute(query, update_data)
    db.commit()
    return get_reading(reading_id, db)

@router.delete("/readings/{reading_id}")
def delete_reading(reading_id: int, db: Session = Depends(get_sql_db)):
    query = text("DELETE FROM energy_readings WHERE reading_id = :reading_id")
    res = db.execute(query, {"reading_id": reading_id})
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Reading not found")
    return {"message": "Reading deleted"}

@router.post("/predictions", response_model=PredictionResponse)
def create_prediction(prediction: PredictionCreate, db: Session = Depends(get_sql_db)):
    query = text("""
        INSERT INTO predictions (region_id, target_ts, predicted_mw, model_name)
        VALUES (:region_id, :target_ts, :predicted_mw, :model_name)
    """)
    res = db.execute(query, prediction.model_dump())
    db.commit()
    
    get_query = text("SELECT * FROM predictions WHERE prediction_id = :pred_id")
    result = db.execute(get_query, {"pred_id": res.lastrowid}).mappings().first()
    return dict(result)
