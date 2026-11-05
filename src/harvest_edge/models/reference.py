from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from geoalchemy2 import Geography, Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from harvest_edge.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from harvest_edge.models.market import Buyer, Price


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("idx_locations_point_gist", "point", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("buyers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    point: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    buyer: Mapped["Buyer"] = relationship(back_populates="locations")
    prices: Mapped[list["Price"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )


class Operator(TimestampMixin, Base):
    __tablename__ = "operators"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    abn: Mapped[str | None] = mapped_column(String(11), unique=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")


class ReceivalSite(TimestampMixin, Base):
    __tablename__ = "receival_sites"
    __table_args__ = (
        Index("idx_receival_sites_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int] = mapped_column(
        ForeignKey("operators.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(3), nullable=False)
    postcode: Mapped[str | None] = mapped_column(String(4))
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class PortTerminal(TimestampMixin, Base):
    __tablename__ = "port_terminals"
    __table_args__ = (
        Index("idx_port_terminals_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    state: Mapped[str] = mapped_column(String(3), nullable=False)
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )


class FreightCorridor(TimestampMixin, Base):
    __tablename__ = "freight_corridors"
    __table_args__ = (
        CheckConstraint(
            "effective_end_date IS NULL OR effective_end_date >= effective_start_date",
            name="valid_dates",
        ),
        CheckConstraint("distance_km > 0", name="positive_distance"),
        Index("idx_freight_corridors_route_gist", "route", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    origin_site_id: Mapped[int] = mapped_column(
        ForeignKey("receival_sites.id", ondelete="RESTRICT"), index=True
    )
    destination_terminal_id: Mapped[int] = mapped_column(
        ForeignKey("port_terminals.id", ondelete="RESTRICT"), index=True
    )
    route: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False
    )
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(nullable=False)
    effective_end_date: Mapped[date | None]


class Commodity(TimestampMixin, Base):
    __tablename__ = "commodities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)


class Grade(TimestampMixin, Base):
    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("commodity_id", "code", name="uq_grades_commodity_code"),
        CheckConstraint(
            "effective_end_date IS NULL OR effective_end_date >= effective_start_date",
            name="valid_dates",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    commodity_id: Mapped[int] = mapped_column(
        ForeignKey("commodities.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_start_date: Mapped[date] = mapped_column(nullable=False)
    effective_end_date: Mapped[date | None]


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="valid_season_dates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)


class DeliveryWindow(TimestampMixin, Base):
    __tablename__ = "delivery_windows"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="valid_window_dates"),
        CheckConstraint(
            "effective_end_date IS NULL OR effective_end_date >= effective_start_date",
            name="valid_dates",
        ),
        UniqueConstraint(
            "receival_site_id", "season_id", "name", name="uq_delivery_windows_site_season_name"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receival_site_id: Mapped[int] = mapped_column(
        ForeignKey("receival_sites.id", ondelete="RESTRICT"), index=True
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)
    effective_start_date: Mapped[date] = mapped_column(nullable=False)
    effective_end_date: Mapped[date | None]
