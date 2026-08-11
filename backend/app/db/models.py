"""SQLAlchemy models for the fixed FMCG/D2C scenario and module outputs."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class SKU(Base):
    __tablename__ = "skus"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    holding_cost_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    ordering_cost: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    processing_time_m1: Mapped[float] = mapped_column(Float, nullable=False)
    processing_time_m2: Mapped[float] = mapped_column(Float, nullable=False)
    processing_time_m3: Mapped[float] = mapped_column(Float, nullable=False)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    fixed_cost: Mapped[float] = mapped_column(Float, nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False)
    is_open_baseline: Mapped[bool] = mapped_column(Boolean, default=True)


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    weekly_demand_share: Mapped[float] = mapped_column(Float, nullable=False)


class DemandHistory(Base):
    __tablename__ = "demand_history"
    __table_args__ = (UniqueConstraint("sku_id", "week_start", name="uq_demand_sku_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(16), ForeignKey("skus.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"
    __table_args__ = (UniqueConstraint("sku_id", "week_start", name="uq_forecast_sku_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku_id: Mapped[str] = mapped_column(String(16), ForeignKey("skus.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    forecast: Mapped[float] = mapped_column(Float, nullable=False)
    lower_ci: Mapped[float] = mapped_column(Float, nullable=False)
    upper_ci: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False, default="ensemble")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScenarioMeta(Base):
    """Key-value metadata for the seeded scenario (seed, generated_at, etc.)."""

    __tablename__ = "scenario_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
