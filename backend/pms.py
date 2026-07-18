"""CSV export profiles.

Only the generic profile is verified.  A client-specific controller profile is
enabled after its official import sample has been mapped and acceptance-tested.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CsvProfile:
    id: str
    name: str
    verified: bool
    description: str
    headers: tuple[str, ...]


PROFILES = {
    "generic": CsvProfile(
        id="generic",
        name="標準CSV",
        verified=True,
        description="日付・施設コード・料金ランク・提案価格をUTF-8 BOMで出力します。",
        headers=("date", "facility_code", "room_type_code", "rate_plan_code", "rank", "price_jpy"),
    ),
    "neppan-draft": CsvProfile(
        id="neppan-draft",
        name="ねっぱん！用マッピング（要検証）",
        verified=False,
        description="導入先の公式インポート見本CSVを受領後に、列名・必須値を確定してください。",
        headers=("date", "facility_code", "room_type_code", "rate_plan_code", "rank", "price_jpy"),
    ),
    "temairazu-draft": CsvProfile(
        id="temairazu-draft",
        name="手間いらず用マッピング（要検証）",
        verified=False,
        description="導入先の公式インポート見本CSVを受領後に、列名・必須値を確定してください。",
        headers=("date", "facility_code", "room_type_code", "rate_plan_code", "rank", "price_jpy"),
    ),
}


def get_profile(profile_id: str) -> CsvProfile:
    try:
        return PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown CSV profile: {profile_id}") from exc
