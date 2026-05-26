import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { storage } from "@/src/utils/storage";
import { apiGet, apiPost } from "@/src/api";
import { initRevenueCat, logOutRevenueCat, addCustomerInfoUpdateListener, planFromCustomerInfo } from "@/src/revenuecat";

export type RaxUser = {
  user_id: string;
  email: string;
  name: string;
  picture?: string | null;
  plan: "free" | "premium" | "pro";
  is_admin: boolean;
  is_blocked: boolean;
  is_guest: boolean;
  created_at: string;
  messages_used: number;
  images_used: number;
};

type Ctx = {
  user: RaxUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  guest: () => Promise<void>;
  loginWithGoogleSession: (session_id: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthCtx = createContext<Ctx>({} as Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<RaxUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const me = await apiGet("/auth/me");
      setUser(me as RaxUser);
      // Init RevenueCat on iOS with this user id (no-op on web/android)
      try { await initRevenueCat((me as RaxUser).user_id); } catch {}
    } catch {
      setUser(null);
      await storage.secureRemove("rax_token");
    }
  }, []);

  useEffect(() => {
    (async () => {
      const token = await storage.secureGet("rax_token", "");
      if (token) await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  // Listen for entitlement changes from RevenueCat (iOS only). When an active
  // subscription appears (purchase / renewal / restore), sync to backend so
  // MongoDB's `plan` field stays in sync — even if the screen-level sync fails.
  useEffect(() => {
    if (!user) return;
    const unsubscribe = addCustomerInfoUpdateListener(async (info: any) => {
      try {
        const newPlan = planFromCustomerInfo(info);
        if (newPlan && newPlan !== user.plan) {
          await apiPost("/revenuecat/sync", {
            app_user_id: user.user_id,
            plan: newPlan,
            entitlements: Object.keys(info?.entitlements?.active || {}),
          }).catch(() => {});
          await refresh();
        }
      } catch {}
    });
    return () => unsubscribe();
  }, [user?.user_id, user?.plan, refresh]);

  const persist = async (token: string, u: RaxUser) => {
    await storage.secureSet("rax_token", token);
    setUser(u);
    try { await initRevenueCat(u.user_id); } catch {}
  };

  const login = async (email: string, password: string) => {
    const r = await apiPost("/auth/login", { email, password });
    await persist(r.token, r.user);
  };
  const register = async (email: string, password: string, name?: string) => {
    const r = await apiPost("/auth/register", { email, password, name });
    await persist(r.token, r.user);
  };
  const guest = async () => {
    const r = await apiPost("/auth/guest", {});
    await persist(r.token, r.user);
  };
  const loginWithGoogleSession = async (session_id: string) => {
    const r = await apiPost("/auth/google/session", { session_id });
    await persist(r.token, r.user);
  };
  const logout = async () => {
    try { await logOutRevenueCat(); } catch {}
    await storage.secureRemove("rax_token");
    setUser(null);
  };

  return (
    <AuthCtx.Provider value={{ user, loading, login, register, guest, loginWithGoogleSession, logout, refresh }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  return useContext(AuthCtx);
}
