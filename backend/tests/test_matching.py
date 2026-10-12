from datetime import date
from decimal import Decimal as D

from app.matching import BankLine, OpenInvoice, reconcile


def inv(number, amount, due=date(2026, 10, 1)):
    return OpenInvoice(number, "Customer", D(amount), due)


def line(id, description, amount, posted=date(2026, 10, 2)):
    return BankLine(id, posted, description, D(amount))


def by_line(results):
    return {r.bank_line_id: r for r in results}


def test_reference_match_ignores_spacing_and_case():
    results = by_line(reconcile([inv("INV-1045", "100.00")], [line("b1", "credit inv 1045", "100.00")]))
    assert results["b1"].rule == "reference"
    assert results["b1"].auto_matched


def test_reference_does_not_match_prefix_of_longer_number():
    results = by_line(reconcile([inv("INV-104", "100.00")], [line("b1", "INV-1045", "100.00")]))
    assert results["b1"].rule == "amount_date"  # falls through to the weaker rule, needs review


def test_short_and_over_payment_are_never_auto_matched():
    invoices = [inv("INV-1", "100.00"), inv("INV-2", "100.00")]
    lines = [line("b1", "INV-1", "90.00"), line("b2", "INV-2", "110.00")]
    results = by_line(reconcile(invoices, lines))
    assert (results["b1"].rule, results["b1"].difference) == ("short_payment", D("-10.00"))
    assert (results["b2"].rule, results["b2"].difference) == ("over_payment", D("10.00"))
    assert not any(r.auto_matched for r in results.values())


def test_amount_and_date_match_needs_review():
    result = reconcile([inv("INV-1", "250.00")], [line("b1", "EFT PAYMENT", "250.00")])[0]
    assert (result.rule, result.invoice_number, result.needs_review) == ("amount_date", "INV-1", True)


def test_amount_match_outside_window_is_unmatched():
    late = line("b1", "EFT", "250.00", posted=date(2026, 12, 1))
    assert reconcile([inv("INV-1", "250.00")], [late])[0].rule == "unmatched"


def test_two_invoices_with_same_amount_are_ambiguous():
    result = reconcile([inv("INV-1", "50.00"), inv("INV-2", "50.00")], [line("b1", "EFT", "50.00")])[0]
    assert result.rule == "ambiguous"
    assert "INV-1" in result.note and "INV-2" in result.note


def test_referenced_invoice_is_not_taken_by_amount_only_match():
    # b1 (no reference, earlier) must not grab INV-1, which b2 references explicitly.
    lines = [line("b1", "EFT", "75.00", posted=date(2026, 10, 1)), line("b2", "INV-1", "75.00")]
    results = by_line(reconcile([inv("INV-1", "75.00")], lines))
    assert results["b2"].rule == "reference"
    assert results["b1"].rule == "unmatched"


def test_payments_out_are_ignored():
    assert reconcile([inv("INV-1", "10.00")], [line("b1", "ESKOM", "-10.00")]) == []
