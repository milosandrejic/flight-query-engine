import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class SearchHistory(Base):
    __tablename__ = "search_history"
    __table_args__ = (
        Index("ix_search_history_user_id", "user_id"),
        Index("ix_search_history_origin", "origin"),
        Index("ix_search_history_destination", "destination"),
        Index("ix_search_history_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    query: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(3))
    destination: Mapped[str] = mapped_column(String(3))
    departure_date: Mapped[date] = mapped_column(Date)
    return_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )
    results_count: Mapped[int] = mapped_column(Integer)
    search_time_ms: Mapped[int] = mapped_column(Integer)
    cabin_class: Mapped[str] = mapped_column(String(50))
    passengers: Mapped[int] = mapped_column(
        Integer,
        default=1
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
