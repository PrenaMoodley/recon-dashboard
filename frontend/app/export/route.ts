// Proxies the Excel export so the browser can download it without knowing the API URL.
import { API_URL } from "@/lib/api";

export async function GET() {
  const res = await fetch(`${API_URL}/export.xlsx`, { cache: "no-store" });
  if (!res.ok) {
    return new Response("Export failed", { status: 502 });
  }
  return new Response(res.body, {
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": 'attachment; filename="reconciliation.xlsx"',
    },
  });
}
