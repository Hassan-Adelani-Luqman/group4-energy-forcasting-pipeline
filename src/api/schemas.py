from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# SQL Schemas
class ReadingBase(BaseModel):
    region_id: int
    reading_ts: datetime
    mw: float
    lag_1h: Optional[float] = None
    lag_24h: Optional[float] = None
    lag_168h: Optional[float] = None
    rolling_mean_24h: Optional[float] = None
    rolling_mean_7d: Optional[float] = None
    rolling_std_24h: Optional[float] = None
    split: str

class ReadingCreate(ReadingBase):
    pass

class ReadingUpdate(BaseModel):
    mw: Optional[float] = None
    lag_1h: Optional[float] = None
    lag_24h: Optional[float] = None
    lag_168h: Optional[float] = None
    rolling_mean_24h: Optional[float] = None
    rolling_mean_7d: Optional[float] = None
    rolling_std_24h: Optional[float] = None
    split: Optional[str] = None

class ReadingResponse(ReadingBase):
    reading_id: int
    model_config = ConfigDict(from_attributes=True)


class PredictionBase(BaseModel):
    region_id: int
    target_ts: datetime
    predicted_mw: float
    model_name: str

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    prediction_id: int
    generated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# MongoDB Schemas
class MongoReadingCreate(BaseModel):
    hour: int
    ts: datetime
    mw: float
    lag_1h: Optional[float] = None
    lag_24h: Optional[float] = None
    lag_168h: Optional[float] = None
    rolling_mean_24h: Optional[float] = None
    rolling_mean_7d: Optional[float] = None
    rolling_std_24h: Optional[float] = None
    split: str

class MongoReadingUpdate(BaseModel):
    mw: Optional[float] = None
    lag_1h: Optional[float] = None
    lag_24h: Optional[float] = None
    lag_168h: Optional[float] = None
    rolling_mean_24h: Optional[float] = None
    rolling_mean_7d: Optional[float] = None
    rolling_std_24h: Optional[float] = None
    split: Optional[str] = None

class MongoPredictionCreate(BaseModel):
    region_code: str
    target_ts: datetime
    predicted_mw: float
    model_name: str
