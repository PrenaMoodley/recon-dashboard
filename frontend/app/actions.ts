"use server";

import { revalidatePath } from "next/cache";
import { api } from "@/lib/api";

export async function runReconciliation() {
  await api("/reconcile", { method: "POST" });
  revalidatePath("/");
}

export async function confirmMatch(bankTransactionId: string) {
  await api(`/matches/${encodeURIComponent(bankTransactionId)}/confirm`, { method: "POST" });
  revalidatePath("/");
}
