"""Database models and session handling (SQLAlchemy 2.0 ORM).

PostgreSQL in production (e.g. Supabase); SQLite works for local development and tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

MONEY = Numeric(12, 2)


class Base(DeclarativeBase):
    pass


class Invoice(Base):
    __tablename__ = "invoices"
    number: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer: Mapped[str] = mapped_column(String(120))
    amount: Mapped[Decimal] = mapped_column(MONEY)  # incl. VAT
    issued_on: Mapped[date]
    due_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | paid


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # bank's own id, for idempotent imports
    posted_on: Mapped[date]
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    source: Mapped[str] = mapped_column(String(20))  # statement | webhook


class MatchResult(Base):
    __tablename__ = "match_results"
    bank_transaction_id: Mapped[str] = mapped_column(ForeignKey("bank_transactions.id"), primary_key=True)
    invoice_number: Mapped[str | None] = mapped_column(ForeignKey("invoices.number"))
    rule: Mapped[str] = mapped_column(String(20))
    difference: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("0.00"))
    note: Mapped[str] = mapped_column(String(200), default="")
    # Reference matches are confirmed automatically; anything else waits for a person.
    confirmed: Mapped[bool] = mapped_column(default=False)
    matched_at: Mapped[datetime] = mapped_column(server_default=func.now())


class WebhookEvent(Base):
    """Every accepted webhook id, so a retried delivery is not processed twice."""

    __tablename__ = "webhook_events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())


engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///recon_dev.db"))
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
