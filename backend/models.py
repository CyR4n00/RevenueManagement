from pydantic import BaseModel
from typing import List, Optional

class Facility(BaseModel):
    id: int
    name: str
    base_price: int
    min_price: int
    max_price: int
    total_rooms: int
    max_sell_rooms: int # オーバーブッキング防止用（実際に販売する最大室数）
    plan: str # "Standard", "Pro", "Enterprise"

class IntegrationSettings(BaseModel):
    facility_id: int
    # サイトコントローラー連携
    site_controller_type: Optional[str] # "neppan", "beds24", "temairazu", None
    site_controller_api_key: Optional[str]
    # 個別OTA連携（サイトコントローラーを使わない場合や併用）
    rakuten_enabled: bool = False
    bookingcom_enabled: bool = False
    airbnb_enabled: bool = False
    # 同期設定（プランに応じた課金要素）
    sync_mode: str # "daily" (Standard), "realtime" (Pro), "auto_optimize" (Enterprise)

class SyncStatus(BaseModel):
    facility_id: int
    last_sync_time: str
    status: str # "success", "error", "pending"
    synced_ota_list: List[str]
    message: str
