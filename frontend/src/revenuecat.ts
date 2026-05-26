/**
 * RevenueCat service — used ONLY on iOS for Apple In-App Purchases.
 * Web and Android keep using Stripe via the existing flow.
 *
 * Safe to import on any platform: all functions early-return on non-iOS
 * or when the native module isn't available (e.g. Expo Go / web dev).
 */
import { Platform } from "react-native";

export type Plan = "free" | "premium" | "pro";

// Entitlement IDs as configured in the RevenueCat dashboard
export const ENTITLEMENT_PREMIUM = "premium";
export const ENTITLEMENT_PRO = "pro";

// Package identifiers as configured in the "default" Offering on RevenueCat
export const PACKAGE_PREMIUM = "$rc_monthly_premium";
export const PACKAGE_PRO = "$rc_monthly_pro";

let _configured = false;
let _Purchases: any = null;

/** Lazy-load the native module. Returns null on platforms where it isn't available. */
function getPurchases(): any | null {
  if (Platform.OS !== "ios") return null;
  if (_Purchases) return _Purchases;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require("react-native-purchases");
    _Purchases = mod?.default || mod;
    return _Purchases;
  } catch (e) {
    console.warn("[RevenueCat] native module not available", e);
    return null;
  }
}

/** Returns true if RevenueCat is usable in the current runtime (iOS native build). */
export function isRevenueCatAvailable(): boolean {
  return Platform.OS === "ios" && getPurchases() !== null;
}

/**
 * Configure RevenueCat once per app session.
 * Should be called after the user has logged in so we have their user_id.
 */
export async function initRevenueCat(userId: string | null): Promise<void> {
  if (Platform.OS !== "ios") return;
  const Purchases = getPurchases();
  if (!Purchases) return;
  const apiKey = process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY;
  if (!apiKey) {
    console.warn("[RevenueCat] EXPO_PUBLIC_REVENUECAT_IOS_KEY is not set");
    return;
  }
  try {
    if (!_configured) {
      Purchases.setLogLevel?.("ERROR");
      // v10 prefers a config object
      await Purchases.configure({ apiKey, appUserID: userId ?? undefined });
      _configured = true;
    } else if (userId) {
      // Already configured — just log in this user
      try {
        await Purchases.logIn(userId);
      } catch {}
    }
  } catch (e) {
    console.warn("[RevenueCat] configure failed", e);
  }
}

/** Log out of RevenueCat (when the app user signs out). */
export async function logOutRevenueCat(): Promise<void> {
  if (Platform.OS !== "ios") return;
  const Purchases = getPurchases();
  if (!Purchases || !_configured) return;
  try {
    await Purchases.logOut();
  } catch {}
}

/** Fetch the current Offering with its packages. Returns null if unavailable. */
export async function getCurrentOffering(): Promise<any | null> {
  const Purchases = getPurchases();
  if (!Purchases) return null;
  try {
    const offerings = await Purchases.getOfferings();
    return offerings?.current || null;
  } catch (e) {
    console.warn("[RevenueCat] getOfferings failed", e);
    return null;
  }
}

/** Convert a CustomerInfo object to our internal plan value. */
export function planFromCustomerInfo(info: any): Plan {
  if (!info?.entitlements?.active) return "free";
  const active = info.entitlements.active as Record<string, unknown>;
  if (active[ENTITLEMENT_PRO]) return "pro";
  if (active[ENTITLEMENT_PREMIUM]) return "premium";
  return "free";
}

/** Get the current CustomerInfo (cached or fresh). */
export async function getCustomerInfo(): Promise<any | null> {
  const Purchases = getPurchases();
  if (!Purchases) return null;
  try {
    return await Purchases.getCustomerInfo();
  } catch (e) {
    console.warn("[RevenueCat] getCustomerInfo failed", e);
    return null;
  }
}

/**
 * Purchase a package. Returns the new plan after the purchase.
 * Throws on errors; if the user cancelled, the error has `userCancelled === true`.
 */
export async function purchasePackage(pkg: any): Promise<{ plan: Plan; customerInfo: any }> {
  const Purchases = getPurchases();
  if (!Purchases) throw new Error("RevenueCat no disponible en esta plataforma");
  const res = await Purchases.purchasePackage(pkg);
  const customerInfo = res?.customerInfo || res;
  return { plan: planFromCustomerInfo(customerInfo), customerInfo };
}

/** Restore previous purchases (e.g. after re-install). */
export async function restorePurchases(): Promise<{ plan: Plan; customerInfo: any }> {
  const Purchases = getPurchases();
  if (!Purchases) throw new Error("RevenueCat no disponible en esta plataforma");
  const customerInfo = await Purchases.restorePurchases();
  return { plan: planFromCustomerInfo(customerInfo), customerInfo };
}

/** Register a listener that fires when entitlements change (purchase, renewal, expiry). */
export function addCustomerInfoUpdateListener(cb: (info: any) => void): () => void {
  const Purchases = getPurchases();
  if (!Purchases) return () => {};
  try {
    const sub = Purchases.addCustomerInfoUpdateListener(cb);
    // v10 may return either a subscription with remove() or just a function
    return () => {
      try {
        if (typeof sub === "function") sub();
        else if (sub?.remove) sub.remove();
        else Purchases.removeCustomerInfoUpdateListener?.(cb);
      } catch {}
    };
  } catch {
    return () => {};
  }
}
