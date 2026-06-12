from pydantic import BaseModel
from typing import List, Optional

class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    min_price: int
    max_price: int
    total_rooms: int
    max_sell_rooms: int
    plan: str # "Standard", "Pro", "Enterprise"
    custom_event_multiplier: float = 1.2 # 週末・イベント時の加算倍率（オーナーが設定可能）

class IntegrationSettings(BaseModel):
    facility_id: int
    site_controller_type: Optional[str]
    site_controller_api_key: Optional[str]
    rakuten_enabled: bool = False
    bookingcom_enabled: bool = False
    airbnb_enabled: bool = False
    sync_mode: str

class SyncStatus(BaseModel):
    facility_id: int
    last_sync_time: str
    status: str
    synced_ota_list: List[str]
    message: str

class RuleCreate(BaseModel):
    facility_id: int
    occupancy_threshold_percent: float
    price_multiplier: float
    active: bool = True
