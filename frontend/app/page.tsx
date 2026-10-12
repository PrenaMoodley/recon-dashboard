import { api, money, type ExceptionRow, type Rule, type Summary } from "@/lib/api";
import { confirmMatch, runReconciliation } from "./actions";

const RULE_LABEL: Record<Rule, string> = {
  short_payment: "Short payment",
  over_payment: "Over payment",
  amount_date: "Suggested match",
  ambiguous: "Ambiguous",
  unmatched: "Unmatched",
};

export default async function Dashboard() {
  let summary: Summary;
  let exceptions: ExceptionRow[];
  try {
    [summary, exceptions] = await Promise.all([
      api<Summary>("/summary"),
      api<ExceptionRow[]>("/exceptions"),
    ]);
  } catch {
    return (
      <main className="page">
        <h1>Reconciliation</h1>
        <p className="error">
          Can&apos;t reach the reconciliation API. Check that it is running and that
          RECON_API_URL is set.
        </p>
      </main>
    );
  }

  const unreconciled = Number(summary.receipts_value) - Number(summary.matched_value);

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Reconciliation</h1>
          <p className="muted">Bank receipts matched to customer invoices</p>
        </div>
        <div className="actions">
          <form action={runReconciliation}>
            <button type="submit">Run reconciliation</button>
          </form>
          <a className="button secondary" href="/export">
            Download Excel
          </a>
        </div>
      </header>

      <section className="tiles" aria-label="Summary">
        <Tile label="Receipts in bank" value={money(summary.receipts_value)} />
        <Tile label="Matched to invoices" value={money(summary.matched_value)} />
        <Tile
          label="Not yet reconciled"
          value={money(unreconciled.toFixed(2))}
          tone={unreconciled > 0 ? "warn" : "ok"}
        />
        <Tile
          label="Open invoices"
          value={money(summary.open_invoice_value)}
          detail={`${summary.open_invoices} invoices`}
        />
      </section>

      <section>
        <h2>
          Needs review <span className="count">{summary.needs_review}</span>
        </h2>
        {exceptions.length === 0 ? (
          <p className="muted">Nothing to review. Import a statement and run reconciliation.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Bank description</th>
                  <th className="num">Amount</th>
                  <th>Invoice</th>
                  <th>Status</th>
                  <th>Note</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {exceptions.map((e) => (
                  <tr key={e.bank_transaction_id}>
                    <td>{e.posted_on}</td>
                    <td>{e.description}</td>
                    <td className="num">{money(e.amount)}</td>
                    <td>{e.invoice_number ?? "—"}</td>
                    <td>
                      <span className={`badge ${e.rule}`}>{RULE_LABEL[e.rule]}</span>
                    </td>
                    <td className="muted">{e.note}</td>
                    <td>
                      {e.rule === "amount_date" && (
                        <form action={confirmMatch.bind(null, e.bank_transaction_id)}>
                          <button type="submit" className="small">
                            Confirm
                          </button>
                        </form>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function Tile({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "ok" | "warn";
}) {
  return (
    <div className={`tile ${tone ?? ""}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {detail && <div className="muted">{detail}</div>}
    </div>
  );
}
