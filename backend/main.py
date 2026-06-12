from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
import random
from ml_model import ml_predictor
from models import Facility, IntegrationSettings, SyncStatus, RuleCreate

app = FastAPI(title="Revenue Control System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Fixed CORS issue
    allow_methods=["*"],
    allow_headers=["*"],
)

class Rule(BaseModel):
    id: int
    facility_id: int
    occupancy_threshold_percent: float
    price_multiplier: float
    active: bool = True

class OccupancyData(BaseModel):
    facility_id: int
    date: str
    booked_rooms: int

class PriceRecommendation(BaseModel):
    facility_id: int
    date: str
    recommended_price_rule_based: int
    rule_applied: Optional[str]
    recommended_price_ml_based: Optional[int]
    event_multiplier: float
    final_price: int

class PerformanceData(BaseModel):
    facility_id: int
    month: str
    target_revenue: int
    actual_revenue: int

class SuggestionData(BaseModel):
    facility_id: int
    date_generated: str
    suggestion_text: str

# In-memory storage for demonstration
facilities = [
    Facility(id=1, name="サンプル ホテル", base_price=10000, min_price=6000, max_price=20000, total_rooms=50, max_sell_rooms=48, plan="Enterprise", custom_event_multiplier=1.2),
    Facility(id=2, name="サンプル ゲストハウス", base_price=5000, min_price=3000, max_price=10000, total_rooms=10, max_sell_rooms=10, plan="Standard", custom_event_multiplier=1.1)
]

integration_settings_db = {
    1: IntegrationSettings(facility_id=1, site_controller_type="beds24", site_controller_api_key="mock_key_123", rakuten_enabled=True, bookingcom_enabled=True, airbnb_enabled=False, sync_mode="auto_optimize"),
    2: IntegrationSettings(facility_id=2, site_controller_type="neppan", site_controller_api_key="mock_key_456", rakuten_enabled=True, bookingcom_enabled=False, airbnb_enabled=True, sync_mode="daily")
}

rules = [
    Rule(id=1, facility_id=1, occupancy_threshold_percent=0.8, price_multiplier=1.3, active=True),
    Rule(id=2, facility_id=1, occupancy_threshold_percent=0.5, price_multiplier=1.1, active=True),
    Rule(id=3, facility_id=2, occupancy_threshold_percent=0.9, price_multiplier=1.5, active=True)
]
rule_id_counter = 4

def get_event_multiplier(date_str: str, custom_multiplier: float) -> float:
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    if target_date.weekday() in [4, 5]: # Friday, Saturday
        return custom_multiplier
    return 1.0

def get_mock_occupancy(facility_id: int, date_str: str) -> int:
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        return 0
    seed_str = f"{facility_id}_{date_str}"
    random.seed(seed_str)
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    if target_date.weekday() >= 5:
        base_rate = random.uniform(0.7, 1.0)
    else:
        base_rate = random.uniform(0.3, 0.7)
    return int(base_rate * facility.total_rooms)


@app.on_event("startup")
def startup_event():
    print("Training ML model with historical dummy data...")
    all_data = []
    for facility in facilities:
        df = ml_predictor.generate_dummy_data(facility.id, facility.base_price, facility.total_rooms)
        all_data.append(df)

    if all_data:
        combined_df = __import__("pandas").concat(all_data)
        ml_predictor.train(combined_df)

# ---------- Facilities & Settings API ----------

@app.get("/facilities", response_model=List[Facility])
def get_facilities():
    return facilities

@app.put("/facilities/{f_id}", response_model=Facility)
def update_facility(f_id: int, updated_f: Facility):
    for i, f in enumerate(facilities):
        if f.id == f_id:
            facilities[i] = updated_f
            return updated_f
    raise HTTPException(status_code=404, detail="Facility not found")

@app.get("/integrations/{f_id}", response_model=IntegrationSettings)
def get_integrations(f_id: int):
    if f_id in integration_settings_db:
        return integration_settings_db[f_id]
    raise HTTPException(status_code=404, detail="Settings not found")

@app.put("/integrations/{f_id}", response_model=IntegrationSettings)
def update_integrations(f_id: int, settings: IntegrationSettings):
    integration_settings_db[f_id] = settings
    return settings

@app.get("/sync_status/{f_id}", response_model=SyncStatus)
def get_sync_status(f_id: int):
    settings = integration_settings_db.get(f_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    status = "success"
    msg = "正常に同期完了しました。"
    if settings.sync_mode == "auto_optimize":
         msg = "AIによるチャネル別販売比率の最適化と共に、リアルタイム同期が完了しました。"
    elif settings.sync_mode == "realtime":
         msg = "予約増減に伴うリアルタイムでの価格・在庫同期が完了しました。"
    else:
         msg = "1日1回のバッチ同期が完了しました。"

    otash = []
    if settings.site_controller_type:
        otash.append(settings.site_controller_type.upper())
    if settings.rakuten_enabled: otash.append("Rakuten")
    if settings.bookingcom_enabled: otash.append("Booking.com")
    if settings.airbnb_enabled: otash.append("Airbnb")

    return SyncStatus(
        facility_id=f_id,
        last_sync_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status=status,
        synced_ota_list=otash,
        message=msg
    )

# ---------- Revenue Engine API ----------

@app.get("/rules", response_model=List[Rule])
def get_rules(facility_id: Optional[int] = None):
    if facility_id:
        return [r for r in rules if r.facility_id == facility_id]
    return rules

@app.post("/rules", response_model=Rule)
def create_rule(rule_in: RuleCreate):
    global rule_id_counter
    new_rule = Rule(
        id=rule_id_counter,
        facility_id=rule_in.facility_id,
        occupancy_threshold_percent=rule_in.occupancy_threshold_percent,
        price_multiplier=rule_in.price_multiplier,
        active=rule_in.active
    )
    rules.append(new_rule)
    rule_id_counter += 1
    return new_rule

@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    global rules
    initial_len = len(rules)
    rules = [r for r in rules if r.id != rule_id]
    if len(rules) == initial_len:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "ok"}

@app.put("/rules/{rule_id}/toggle", response_model=Rule)
def toggle_rule(rule_id: int):
    rule = next((r for r in rules if r.id == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.active = not rule.active
    return rule

@app.get("/occupancy", response_model=List[OccupancyData])
def get_occupancy(facility_id: Optional[int] = None, date: Optional[str] = None):
    if not date:
        date = datetime.date.today().isoformat()
    result = []
    target_facilities = [f for f in facilities if f.id == facility_id] if facility_id else facilities
    for f in target_facilities:
        booked = get_mock_occupancy(f.id, date)
        result.append(OccupancyData(facility_id=f.id, date=date, booked_rooms=booked))
    return result

@app.get("/recommendations/{facility_id}/{date}", response_model=PriceRecommendation)
def get_recommendation(facility_id: int, date: str):
    facility = next((f for f in facilities if f.id == facility_id), None)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    booked_rooms = get_mock_occupancy(facility_id, date)
    occupancy_rate = booked_rooms / facility.max_sell_rooms if facility.max_sell_rooms > 0 else 0

    event_mult = 1.0
    if facility.plan in ["Pro", "Enterprise"]:
        event_mult = get_event_multiplier(date, facility.custom_event_multiplier)

    facility_rules = sorted(
        [r for r in rules if r.facility_id == facility_id and r.active],
        key=lambda x: x.occupancy_threshold_percent,
        reverse=True
    )

    recommended_price_rule = facility.base_price
    rule_applied = None

    for rule in facility_rules:
        if occupancy_rate >= rule.occupancy_threshold_percent:
            recommended_price_rule = int(facility.base_price * rule.price_multiplier)
            rule_applied = f"稼働率 {int(rule.occupancy_threshold_percent*100)}% 以上 (x{rule.price_multiplier})"
            break

    recommended_price_rule = int(recommended_price_rule * event_mult)

    recommended_price_ml = None
    if facility.plan == "Enterprise":
        recommended_price_ml = ml_predictor.predict_optimal_price(
            date_str=date,
            current_occupancy_rate=occupancy_rate,
            base_price=facility.base_price
        )

    raw_final_price = recommended_price_ml if (recommended_price_ml is not None) else recommended_price_rule
    final_price = max(facility.min_price, min(raw_final_price, facility.max_price))

    return PriceRecommendation(
        facility_id=facility_id,
        date=date,
        recommended_price_rule_based=recommended_price_rule,
        rule_applied=rule_applied,
        recommended_price_ml_based=recommended_price_ml,
        event_multiplier=event_mult,
        final_price=final_price
    )

@app.get("/performance/{facility_id}", response_model=List[PerformanceData])
def get_performance(facility_id: int):
    months = ["2026-03", "2026-04", "2026-05"]
    facility = next((f for f in facilities if f.id == facility_id), None)
    base_rev = facility.base_price * facility.total_rooms * 20 if facility else 0
    return [
        PerformanceData(facility_id=facility_id, month=months[0], target_revenue=int(base_rev*1.0), actual_revenue=int(base_rev*0.95)),
        PerformanceData(facility_id=facility_id, month=months[1], target_revenue=int(base_rev*1.05), actual_revenue=int(base_rev*1.08)),
        PerformanceData(facility_id=facility_id, month=months[2], target_revenue=int(base_rev*1.1), actual_revenue=int(base_rev*1.15))
    ]

@app.get("/suggestions/{facility_id}", response_model=SuggestionData)
def get_suggestion(facility_id: int):
    suggestions = [
        "【AIからの提案】直近3ヶ月で、金曜日の実際の稼働率が目標を下回っています。週末のベース価格を5%下げるか、イベント時の上乗せ倍率を1.2倍から1.1倍に調整することを推奨します。",
        "【AIからの提案】先月、設定された『下限価格』で販売された日数が10日ありました。オフシーズンのため、下限価格を一時的に3,000円から2,500円に引き下げることで、機会損失を防げる可能性があります。",
        "【AIからの提案】オーバーブッキング防止のためブロックしている2室について、キャンセル率が低いためブロックを1室に減らしても安全です。"
    ]
    seed_str = f"sugg_{facility_id}_{datetime.date.today().isoformat()}"
    random.seed(seed_str)
    sug = random.choice(suggestions)
    return SuggestionData(
        facility_id=facility_id,
        date_generated=datetime.date.today().isoformat(),
        suggestion_text=sug
    )
