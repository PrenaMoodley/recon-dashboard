// Server-side client for the reconciliation API.
// The browser never calls the API directly: pages and actions run on the server,
// so the API URL stays private and no CORS setup is needed.

export const API_URL = process.env.RECON_API_URL ?? "http://localhost:8000";

export type Summary = {
  open_invoices: number;
  open_invoice_value: string;
  receipts_value: string;
  matched_value: string;
  needs_review: number;
};

export type Rule = "short_payment" | "over_payment" | "amount_date" | "ambiguous" | "unmatched";

export type ExceptionRow = {
  bank_transaction_id: string;
  posted_on: string;
  description: string;
  amount: string;
  invoice_number: string | null;
  rule: Rule;
  difference: string;
  note: string;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

const zar = new Intl.NumberFormat("en-ZA", { style: "currency", currency: "ZAR" });

// Amounts arrive as decimal strings so no precision is lost in transit.
// Converting to a number here is only for display.
export function money(value: string): string {
  return zar.format(Number(value));
}
