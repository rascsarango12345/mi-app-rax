import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL;

async function authHeaders(extra: Record<string, string> = {}) {
  const token = await storage.secureGet("rax_token", "");
  const headers: Record<string, string> = { "Content-Type": "application/json", ...extra };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export async function apiGet(path: string) {
  const r = await fetch(`${BASE}/api${path}`, { headers: await authHeaders() });
  if (!r.ok) throw new Error((await safeMsg(r)) || `GET ${path} ${r.status}`);
  return r.json();
}

export async function apiPost(path: string, body: any = {}) {
  const r = await fetch(`${BASE}/api${path}`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await safeMsg(r)) || `POST ${path} ${r.status}`);
  return r.json();
}

export async function apiPatch(path: string, body: any = {}) {
  const r = await fetch(`${BASE}/api${path}`, {
    method: "PATCH",
    headers: await authHeaders(),
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await safeMsg(r)) || `PATCH ${path} ${r.status}`);
  return r.json();
}

export async function apiDelete(path: string) {
  const r = await fetch(`${BASE}/api${path}`, { method: "DELETE", headers: await authHeaders() });
  if (!r.ok) throw new Error((await safeMsg(r)) || `DELETE ${path} ${r.status}`);
  return r.json();
}

async function safeMsg(r: Response) {
  try {
    const j = await r.json();
    return j?.detail || j?.message;
  } catch {
    return null;
  }
}

export const API_BASE = BASE;
