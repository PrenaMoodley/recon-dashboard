"""Bank-to-invoice matching rules.

A pure function over plain data: no database, no web framework. That keeps the
rules easy to read, easy to test and easy to explain to the finance team.

Rules, in order of confidence:
  1. reference      - the bank description contains the invoice number and the amount is equal.
  2. short / over   - the invoice number matches but the amount differs. Never auto-matched.
  3. amount_date    - no reference, but exactly one open invoice has the same amount and
                      the payment is within WINDOW_DAYS of its due date. Needs a human to confirm.
  4. ambiguous      - several open invoices fit rule 3.
  5. unmatched      - nothing fits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

WINDOW_DAYS = 30


@dataclass(frozen=True)
class OpenInvoice:
    number: str
    customer: str
    amount: Decimal  # incl. VAT, what the customer should pay
    due_date: date


@dataclass(frozen=True)
class BankLine:
    id: str
    posted_on: date
    description: str
    amount: Decimal  # positive = money in


@dataclass(frozen=True)
class Result:
    bank_line_id: str
    invoice_number: str | None
    rule: str  # reference | short_payment | over_payment | amount_date | ambiguous | unmatched
    difference: Decimal = Decimal("0.00")
    note: str = ""

    @property
    def auto_matched(self) -> bool:
        return self.rule == "reference"

    @property
    def needs_review(self) -> bool:
        return not self.auto_matched


def _normalise(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _mentions(description: str, invoice_number: str) -> bool:
    """True if the bank description contains the invoice number, however it is
    spaced or punctuated ("INV-1045", "INV 1045", "inv1045"), but not as the
    start of a longer number ("INV-104" must not match "INV-1045")."""
    desc, number = _normalise(description), _normalise(invoice_number)
    return re.search(re.escape(number) + r"(?![0-9])", desc) is not None


def reconcile(invoices: list[OpenInvoice], lines: list[BankLine]) -> list[Result]:
    open_invoices = {inv.number: inv for inv in invoices}
    results: list[Result] = []

    # Pass 1: reference matches. Done first so an invoice that is clearly
    # referenced can't be taken by a weaker amount-only match.
    remaining: list[BankLine] = []
    for line in sorted(lines, key=lambda bank_line: (bank_line.posted_on, bank_line.id)):
        if line.amount <= 0:
            continue  # payments out are not customer receipts
        referenced = [inv for n, inv in open_invoices.items() if _mentions(line.description, n)]
        if len(referenced) != 1:
            remaining.append(line)
            continue
        inv = referenced[0]
        diff = line.amount - inv.amount
        if diff == 0:
            results.append(Result(line.id, inv.number, "reference"))
            del open_invoices[inv.number]
        else:
            rule = "short_payment" if diff < 0 else "over_payment"
            results.append(
                Result(line.id, inv.number, rule, diff, f"Paid R{line.amount} against R{inv.amount}")
            )

    # Pass 2: amount and date, only for lines with no usable reference.
    for line in remaining:
        candidates = [
            inv
            for inv in open_invoices.values()
            if inv.amount == line.amount and abs((line.posted_on - inv.due_date).days) <= WINDOW_DAYS
        ]
        if len(candidates) == 1:
            inv = candidates[0]
            results.append(
                Result(line.id, inv.number, "amount_date", note="No reference; amount and date fit")
            )
            del open_invoices[inv.number]
        elif candidates:
            names = ", ".join(sorted(c.number for c in candidates))
            results.append(Result(line.id, None, "ambiguous", note=f"Could be {names}"))
        else:
            results.append(Result(line.id, None, "unmatched", note="No open invoice fits"))

    return results
