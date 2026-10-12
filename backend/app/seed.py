"""Load fictional open invoices for the demo.

python -m app.seed
curl -F file=@sample_data/bank_statement.csv localhost:8000/imports/bank-statement
"""

from datetime import date
from decimal import Decimal

from .db import Base, Invoice, SessionLocal, engine

INVOICES = [
    ("INV-1042", "Coastal Bakeries (Pty) Ltd", "7274.90", date(2026, 9, 1), date(2026, 10, 1)),
    ("INV-1043", "Berea Fresh Markets CC", "7952.25", date(2026, 9, 3), date(2026, 10, 3)),
    ("INV-1044", "Ridgeview Catering Services", "12098.00", date(2026, 9, 5), date(2026, 10, 5)),
    ("INV-1045", "Umdloti Juice Co", "8977.25", date(2026, 9, 8), date(2026, 10, 8)),
    ("INV-1046", "Highway Deli Franchises (Pty) Ltd", "2300.00", date(2026, 9, 10), date(2026, 10, 10)),
    ("INV-1047", "Coastal Bakeries (Pty) Ltd", "2300.00", date(2026, 9, 12), date(2026, 10, 12)),
    ("INV-1048", "Berea Fresh Markets CC", "1150.00", date(2026, 9, 15), date(2026, 10, 15)),
]


def seed() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add_all(
            Invoice(number=n, customer=c, amount=Decimal(a), issued_on=i, due_date=d)
            for n, c, a, i, d in INVOICES
        )
        session.commit()


if __name__ == "__main__":
    seed()
    print(f"Seeded {len(INVOICES)} open invoices")
