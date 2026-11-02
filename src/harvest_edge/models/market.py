from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from harvest_edge.models.base import Base, TimestampMixin
from harvest_edge.models.reference import Location


class DataSource(TimestampMixin, Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    publisher_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="unverified", server_default="unverified"
    )
    licence_restrictions: Mapped[str | None] = mapped_column(String(1000))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BuyerBid(TimestampMixin, Base):
    __tablename__ = "buyer_bids"
    __table_args__ = (
        CheckConstraint(
            "effective_end_date IS NULL OR effective_end_date >= effective_start_date",
            name="valid_dates",
        ),
        CheckConstraint("bid_price_aud_per_tonne >= 0", name="nonnegative_bid"),
        CheckConstraint(
            "fob_export_price_aud_per_tonne IS NULL OR fob_export_price_aud_per_tonne >= 0",
            name="nonnegative_fob",
        ),
        CheckConstraint("uncertainty_margin_aud_per_tonne >= 0", name="nonnegative_uncertainty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receival_site_id: Mapped[int] = mapped_column(
        ForeignKey("receival_sites.id", ondelete="RESTRICT"), index=True
    )
    commodity_id: Mapped[int] = mapped_column(
        ForeignKey("commodities.id", ondelete="RESTRICT"), index=True
    )
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), index=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="RESTRICT"), index=True
    )
    delivery_window_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_windows.id", ondelete="RESTRICT"), index=True
    )
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    bid_price_aud_per_tonne: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fob_export_price_aud_per_tonne: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    uncertainty_margin_aud_per_tonne: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    quoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date | None] = mapped_column(Date)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class HandlingFreightCharge(TimestampMixin, Base):
    __tablename__ = "handling_freight_charges"
    __table_args__ = (
        CheckConstraint(
            "effective_end_date IS NULL OR effective_end_date >= effective_start_date",
            name="valid_dates",
        ),
        CheckConstraint("freight_cost_aud_per_tonne >= 0", name="nonnegative_freight"),
        CheckConstraint("receival_fee_aud_per_tonne >= 0", name="nonnegative_receival_fee"),
        CheckConstraint("handling_fee_aud_per_tonne >= 0", name="nonnegative_handling_fee"),
        CheckConstraint("uncertainty_margin_aud_per_tonne >= 0", name="nonnegative_uncertainty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receival_site_id: Mapped[int] = mapped_column(
        ForeignKey("receival_sites.id", ondelete="RESTRICT"), index=True
    )
    port_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("port_terminals.id", ondelete="RESTRICT"), index=True
    )
    commodity_id: Mapped[int | None] = mapped_column(
        ForeignKey("commodities.id", ondelete="RESTRICT"), index=True
    )
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    freight_cost_aud_per_tonne: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    receival_fee_aud_per_tonne: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    handling_fee_aud_per_tonne: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    uncertainty_margin_aud_per_tonne: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    effective_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end_date: Mapped[date | None] = mapped_column(Date)


class IngestionLog(TimestampMixin, Base):
    __tablename__ = "ingestion_logs"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'succeeded', 'failed')", name="valid_status"),
        CheckConstraint("records_processed >= 0", name="nonnegative_records"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    scraper_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'running'")
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_processed: Mapped[int] = mapped_column(nullable=False, server_default="0")
    error_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class Price(TimestampMixin, Base):
    __tablename__ = "prices"
    __table_args__ = (CheckConstraint("price_per_tonne > 0", name="positive_price"),)

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    location_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    commodity: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price_per_tonne: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    location: Mapped[Location] = relationship(back_populates="prices")
