"""Reconciliation API: bank receipts in, matched invoices and exceptions out."""

from __future__ import annotations

import csv
import io
import os
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import matching, security
from .db import BankTransaction, Base, Invoice, MatchResult, WebhookEvent, engine, get_session
from .export import build_workbook


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fine for a demo. A production service would run migrations (Alembic) in its deploy step.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Recon API", version="0.1.0", lifespan=lifespan)
DB = Annotated[Session, Depends(get_session)]


@app.get("/health")
def health(session: DB) -> dict:
    session.execute(select(1))
    return {"status": "ok"}


# ---------------------------------------------------------------- imports


@app.post("/imports/bank-statement")
async def import_statement(file: UploadFile, session: DB) -> dict:
    """CSV with columns id, posted_on (YYYY-MM-DD), description, amount (decimal point,
    optional thousands separators). Re-importing the same statement is safe."""
    text = (await file.read()).decode("utf-8-sig")
    existing = set(session.scalars(select(BankTransaction.id)))
    imported, skipped, errors = 0, 0, []
    for row_no, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            tx = BankTransaction(
                id=row["id"].strip(),
                posted_on=date.fromisoformat(row["posted_on"].strip()),
                description=row["description"].strip(),
                amount=Decimal(row["amount"].replace(" ", "").replace(",", "")),
                source="statement",
            )
        except (KeyError, ValueError, InvalidOperation) as e:
            errors.append(f"row {row_no}: {e}")
            continue
        if tx.id in existing:
            skipped += 1
            continue
        session.add(tx)
        existing.add(tx.id)
        imported += 1
    if errors:
        session.rollback()
        raise HTTPException(422, {"message": "Nothing imported; fix these rows", "errors": errors})
    session.commit()
    return {"imported": imported, "skipped_duplicates": skipped}


class PaymentData(BaseModel):
    transaction_id: str
    posted_on: date
    description: str
    amount: Decimal


class PaymentEvent(BaseModel):
    id: str
    type: str
    data: PaymentData


@app.post("/webhooks/payments")
async def payment_webhook(request: Request, session: DB) -> dict:
    body = await request.body()
    try:
        security.verify(os.environ.get("WEBHOOK_SECRET", ""), body, request.headers.get("X-Signature"))
    except security.SignatureError as e:
        raise HTTPException(401, str(e)) from e

    event = PaymentEvent.model_validate_json(body)
    if session.get(WebhookEvent, event.id):
        return {"status": "duplicate"}  # providers retry; answer 200 so they stop
    session.add(WebhookEvent(event_id=event.id))
    if event.type == "payment.received" and not session.get(BankTransaction, event.data.transaction_id):
        session.add(
            BankTransaction(
                id=event.data.transaction_id,
                posted_on=event.data.posted_on,
                description=event.data.description,
                amount=event.data.amount,
                source="webhook",
            )
        )
        status = "processed"
    else:
        status = "ignored"
    session.commit()
    return {"status": status}


# ---------------------------------------------------------------- reconciliation


@app.post("/reconcile")
def run_reconciliation(session: DB) -> dict:
    """Re-run matching for every receipt without a confirmed match."""
    session.execute(delete(MatchResult).where(MatchResult.confirmed.is_(False)))
    confirmed_ids = set(session.scalars(select(MatchResult.bank_transaction_id)))

    invoices = [
        matching.OpenInvoice(i.number, i.customer, i.amount, i.due_date)
        for i in session.scalars(select(Invoice).where(Invoice.status == "open"))
    ]
    lines = [
        matching.BankLine(t.id, t.posted_on, t.description, t.amount)
        for t in session.scalars(select(BankTransaction))
        if t.id not in confirmed_ids
    ]
    results = matching.reconcile(invoices, lines)
    for r in results:
        session.add(
            MatchResult(
                bank_transaction_id=r.bank_line_id,
                invoice_number=r.invoice_number,
                rule=r.rule,
                difference=r.difference,
                note=r.note,
                confirmed=r.auto_matched,
            )
        )
        if r.auto_matched:
            session.get(Invoice, r.invoice_number).status = "paid"
    session.commit()
    return {"processed": len(results), "by_rule": dict(Counter(r.rule for r in results))}


@app.post("/matches/{bank_transaction_id}/confirm")
def confirm_match(bank_transaction_id: str, session: DB) -> dict:
    """A person accepts a suggested amount_date match."""
    result = session.get(MatchResult, bank_transaction_id)
    if result is None:
        raise HTTPException(404, "No match result for that transaction")
    if result.rule != "amount_date":
        raise HTTPException(409, f"A '{result.rule}' result can't be confirmed as a match")
    result.confirmed = True
    session.get(Invoice, result.invoice_number).status = "paid"
    session.commit()
    return {"status": "confirmed"}


def _exceptions(session: Session) -> list[dict]:
    rows = session.execute(
        select(MatchResult, BankTransaction)
        .join(BankTransaction, BankTransaction.id == MatchResult.bank_transaction_id)
        .where(MatchResult.confirmed.is_(False))
        .order_by(BankTransaction.posted_on)
    )
    return [
        {
            "bank_transaction_id": t.id,
            "posted_on": t.posted_on.isoformat(),
            "description": t.description,
            "amount": str(t.amount),
            "invoice_number": m.invoice_number,
            "rule": m.rule,
            "difference": str(m.difference),
            "note": m.note,
        }
        for m, t in rows
    ]


@app.get("/exceptions")
def exceptions(session: DB) -> list[dict]:
    return _exceptions(session)


@app.get("/summary")
def summary(session: DB) -> dict:
    def total(stmt) -> str:
        return str(session.scalar(stmt) or Decimal("0.00"))

    return {
        "open_invoices": session.scalar(select(func.count()).where(Invoice.status == "open")),
        "open_invoice_value": total(select(func.sum(Invoice.amount)).where(Invoice.status == "open")),
        "receipts_value": total(select(func.sum(BankTransaction.amount)).where(BankTransaction.amount > 0)),
        "matched_value": total(
            select(func.sum(BankTransaction.amount))
            .join(MatchResult, MatchResult.bank_transaction_id == BankTransaction.id)
            .where(MatchResult.confirmed.is_(True))
        ),
        "needs_review": session.scalar(select(func.count()).where(MatchResult.confirmed.is_(False))),
    }


@app.get("/export.xlsx")
def export(session: DB) -> Response:
    content = build_workbook(summary(session), _exceptions(session))
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="reconciliation.xlsx"'},
    )
