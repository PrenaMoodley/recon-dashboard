import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Reconciliation",
  description: "Bank receipts matched to customer invoices",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-ZA">
      <body>{children}</body>
    </html>
  );
}
