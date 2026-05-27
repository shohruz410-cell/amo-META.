from datetime import datetime

from sqlalchemy import Integer, Text, DateTime, String, func, BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import db


class FacebookOAuth(db.Model):
    __tablename__ = 'facebook_oauth'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    ad_account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pixel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)

    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    def __repr__(self):
        return f"<FacebookOAuth (business_id: {self.business_id})>"
