"""Business settings data access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business_setting import BusinessSetting


class BusinessSettingRepository:
    """Repository for key-value business settings."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all(self) -> dict[str, str]:
        stmt = select(BusinessSetting)
        rows = self.db.scalars(stmt).all()
        return {row.key: row.value for row in rows}

    def get_by_key(self, key: str) -> BusinessSetting | None:
        return self.db.get(BusinessSetting, key)

    def upsert(self, key: str, value: str) -> BusinessSetting:
        existing = self.get_by_key(key)
        if existing:
            existing.value = value
            self.db.add(existing)
            return existing
        row = BusinessSetting(key=key, value=value)
        self.db.add(row)
        return row
