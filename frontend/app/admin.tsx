import { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Platform, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPatch, apiPost } from "@/src/api";

type AdminUser = {
  user_id: string;
  email: string;
  name: string;
  plan: "free" | "premium" | "pro";
  is_blocked: boolean;
  is_admin: boolean;
  messages_used: number;
  images_used: number;
};

type Sub = {
  user_id: string;
  email: string;
  name: string;
  plan: string;
  monthly_price_usd: number;
  messages_used: number;
  images_used: number;
  since: string;
};

type Tab = "stats" | "users" | "subs" | "theme";

const PRESETS = [
  { id: "neon_blue", name: "Neón Azul", primary: "#00E5FF", accent: "#7C4DFF" },
  { id: "neon_green", name: "Neón Verde", primary: "#00FF66", accent: "#00E5FF" },
  { id: "cyber_purple", name: "Cyber Púrpura", primary: "#B388FF", accent: "#FF4081" },
  { id: "matrix", name: "Matrix", primary: "#00FF41", accent: "#39FF14" },
  { id: "fire", name: "Fuego", primary: "#FF6B35", accent: "#FFB800" },
  { id: "ice", name: "Hielo", primary: "#80D8FF", accent: "#E0F7FA" },
];

export default function AdminScreen() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("stats");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [subs, setSubs] = useState<{ subscriptions: Sub[]; total_active: number; monthly_revenue_usd: number; annual_projection_usd: number } | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [theme, setTheme] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [u, s, sb, th] = await Promise.all([
        apiGet("/admin/users"),
        apiGet("/admin/stats"),
        apiGet("/admin/subscriptions"),
        apiGet("/theme"),
      ]);
      setUsers(u);
      setStats(s);
      setSubs(sb);
      setTheme(th);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setPlan = async (uid: string, plan: AdminUser["plan"]) => {
    await apiPatch(`/admin/users/${uid}/plan`, { plan });
    setUsers((x) => x.map((u) => (u.user_id === uid ? { ...u, plan } : u)));
    await load();
  };

  const toggleBlock = async (u: AdminUser) => {
    await apiPatch(`/admin/users/${u.user_id}/block`, { blocked: !u.is_blocked });
    setUsers((x) => x.map((v) => (v.user_id === u.user_id ? { ...v, is_blocked: !u.is_blocked } : v)));
  };

  const applyPreset = async (p: typeof PRESETS[0]) => {
    const payload = {
      primary_color: p.primary,
      accent_color: p.accent,
      success_color: "#00FF66",
      background_color: "#050505",
      preset: p.id,
    };
    try {
      const url = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/admin/theme`;
      const token = (await import("@/src/utils/storage")).storage;
      const t = await token.secureGet("rax_token", "");
      const r = await fetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error("Theme update failed");
      const data = await r.json();
      setTheme(data.theme);
      if (Platform.OS === "web") window.alert("Tema actualizado. Recarga la app para ver cambios completos.");
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>Panel Manager · RASC</Text>
        <TouchableOpacity onPress={load}>
          <Ionicons name="refresh" size={22} color={Colors.electricBlue} />
        </TouchableOpacity>
      </View>

      <View style={styles.tabBar}>
        {(["stats", "users", "subs", "theme"] as Tab[]).map((t) => (
          <TouchableOpacity
            key={t}
            testID={`admin-tab-${t}`}
            style={[styles.tab, tab === t && styles.tabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.tabText, tab === t && { color: "#000" }]}>
              {t === "stats" ? "📊 Stats" : t === "users" ? "👥 Usuarios" : t === "subs" ? "💎 Suscripciones" : "🎨 Diseño"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity testID="btn-admin-support" style={styles.supportBtn} onPress={() => router.push("/support")}>
        <Ionicons name="headset" size={18} color={Colors.neonGreen} />
        <Text style={{ color: Colors.neonGreen, fontWeight: "700" }}>
          Soporte ({stats?.open_tickets ?? 0} abiertos)
        </Text>
        <Ionicons name="chevron-forward" size={18} color={Colors.neonGreen} />
      </TouchableOpacity>

      {loading ? (
        <ActivityIndicator color={Colors.electricBlue} style={{ marginTop: 40 }} />
      ) : tab === "stats" ? (
        <ScrollView contentContainerStyle={{ padding: Spacing.md }}>
          {stats && (
            <>
              <View style={styles.statsGrid}>
                <Stat label="Usuarios" value={stats.total_users} />
                <Stat label="Mensajes" value={stats.total_messages} />
                <Stat label="Imágenes" value={stats.total_images} />
                <Stat label="Premium" value={stats.premium_users} />
                <Stat label="Pro" value={stats.pro_users} />
                <Stat label="Bloqueados" value={stats.blocked_users} />
                <Stat label="Tickets" value={stats.open_tickets} />
              </View>
              <View style={styles.revenueCard}>
                <Text style={styles.revLabel}>INGRESOS MENSUALES</Text>
                <Text style={styles.revValue}>${stats.estimated_revenue_usd}</Text>
                <Text style={styles.revAnnual}>≈ ${(stats.estimated_revenue_usd * 12).toFixed(2)}/año</Text>
                <Text style={styles.revDate}>Hoy: {stats.today}</Text>
              </View>
            </>
          )}
        </ScrollView>
      ) : tab === "users" ? (
        <FlatList
          data={users}
          keyExtractor={(u) => u.user_id}
          contentContainerStyle={{ padding: Spacing.md, gap: 10 }}
          renderItem={({ item }) => (
            <View style={styles.userCard} testID={`admin-user-${item.user_id}`}>
              <Text style={styles.userName}>
                {item.name} {item.is_admin && "🛡️"} {item.is_blocked && "🚫"}
              </Text>
              <Text style={styles.userEmail}>{item.email}</Text>
              <Text style={styles.userStats}>Plan: {item.plan} · Msgs: {item.messages_used} · Imgs: {item.images_used}</Text>
              <View style={styles.actions}>
                {(["free", "premium", "pro"] as const).map((p) => (
                  <TouchableOpacity
                    key={p}
                    style={[styles.planBtn, item.plan === p && styles.planBtnActive]}
                    onPress={() => setPlan(item.user_id, p)}
                  >
                    <Text style={[styles.planBtnText, item.plan === p && { color: "#000" }]}>{p}</Text>
                  </TouchableOpacity>
                ))}
                <TouchableOpacity style={styles.blockBtn} onPress={() => toggleBlock(item)}>
                  <Text style={{ color: item.is_blocked ? Colors.success : Colors.error, fontWeight: "700", fontSize: 12 }}>
                    {item.is_blocked ? "Desbloquear" : "Bloquear"}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          )}
        />
      ) : tab === "subs" ? (
        <FlatList
          ListHeaderComponent={
            subs && (
              <View style={styles.revenueCard}>
                <Text style={styles.revLabel}>SUSCRIPCIONES ACTIVAS</Text>
                <Text style={styles.revValue}>{subs.total_active}</Text>
                <Text style={styles.revAnnual}>${subs.monthly_revenue_usd} /mes · ${subs.annual_projection_usd} /año</Text>
                <Text style={styles.revDate}>📌 Configura tu procesador de pagos al publicar para recibir pagos</Text>
              </View>
            )
          }
          data={subs?.subscriptions || []}
          keyExtractor={(s) => s.user_id}
          contentContainerStyle={{ padding: Spacing.md, gap: 8 }}
          renderItem={({ item }) => (
            <View style={styles.subCard}>
              <View style={{ flex: 1 }}>
                <Text style={styles.userName}>{item.name}</Text>
                <Text style={styles.userEmail}>{item.email}</Text>
                <Text style={styles.userStats}>
                  Desde: {new Date(item.since).toLocaleDateString()}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={[styles.planBadge, { color: item.plan === "pro" ? Colors.neonGreen : Colors.electricBlue }]}>
                  {item.plan.toUpperCase()}
                </Text>
                <Text style={styles.subPrice}>${item.monthly_price_usd}/mes</Text>
              </View>
            </View>
          )}
          ListEmptyComponent={
            <Text style={{ color: Colors.textMuted, textAlign: "center", padding: 30 }}>
              Sin suscripciones activas todavía
            </Text>
          }
        />
      ) : (
        <ScrollView contentContainerStyle={{ padding: Spacing.md }}>
          <Text style={styles.label}>Tema actual: {theme?.preset || "default"}</Text>
          <View style={styles.themeGrid}>
            {PRESETS.map((p) => (
              <TouchableOpacity
                key={p.id}
                testID={`theme-${p.id}`}
                style={[
                  styles.themeCard,
                  { borderColor: p.primary },
                  theme?.preset === p.id && { borderWidth: 3 },
                ]}
                onPress={() => applyPreset(p)}
              >
                <View style={[styles.themeSwatch, { backgroundColor: p.primary }]} />
                <View style={[styles.themeSwatch2, { backgroundColor: p.accent }]} />
                <Text style={styles.themeName}>{p.name}</Text>
                <Text style={styles.themeHex}>{p.primary}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <Text style={[styles.userStats, { marginTop: 16, textAlign: "center" }]}>
            💡 El tema cambia los colores de acento en toda la app
          </Text>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <View style={styles.statCard}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 16, fontWeight: "800" },
  tabBar: { flexDirection: "row", padding: 8, gap: 6, backgroundColor: Colors.surface },
  tab: { flex: 1, paddingVertical: 8, borderRadius: Radius.pill, backgroundColor: Colors.surfaceElevated, alignItems: "center", borderWidth: 1, borderColor: Colors.border },
  tabActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  tabText: { color: Colors.textPrimary, fontWeight: "600", fontSize: 11 },
  supportBtn: { flexDirection: "row", alignItems: "center", gap: 8, padding: 12, marginHorizontal: Spacing.md, marginTop: 10, borderRadius: Radius.md, backgroundColor: "#000", borderWidth: 1, borderColor: Colors.neonGreen },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: Spacing.md },
  statCard: { width: "31%", backgroundColor: Colors.surface, borderRadius: Radius.md, padding: 10, borderWidth: 1, borderColor: Colors.border, alignItems: "center" },
  statValue: { color: Colors.electricBlue, fontSize: 22, fontWeight: "800" },
  statLabel: { color: Colors.textSecondary, fontSize: 11, marginTop: 2 },
  revenueCard: { padding: Spacing.lg, borderRadius: Radius.lg, backgroundColor: "#000", borderWidth: 1, borderColor: Colors.neonGreen, alignItems: "center", marginBottom: Spacing.md },
  revLabel: { color: Colors.textSecondary, fontSize: 11, letterSpacing: 2, fontWeight: "700" },
  revValue: { color: Colors.neonGreen, fontSize: 42, fontWeight: "900", marginTop: 6 },
  revAnnual: { color: Colors.textPrimary, fontSize: 13, marginTop: 4 },
  revDate: { color: Colors.textMuted, fontSize: 11, marginTop: 10 },
  userCard: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: Spacing.md, borderWidth: 1, borderColor: Colors.border },
  userName: { color: Colors.textPrimary, fontWeight: "700" },
  userEmail: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  userStats: { color: Colors.textMuted, fontSize: 11, marginTop: 4 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 10 },
  planBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: Radius.pill, backgroundColor: Colors.surfaceElevated, borderWidth: 1, borderColor: Colors.border },
  planBtnActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  planBtnText: { color: Colors.textPrimary, fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  blockBtn: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: Radius.pill, backgroundColor: Colors.surfaceElevated, borderWidth: 1, borderColor: Colors.border },
  subCard: { flexDirection: "row", alignItems: "center", gap: 10, padding: Spacing.md, borderRadius: Radius.md, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border },
  planBadge: { fontSize: 12, fontWeight: "800", letterSpacing: 1 },
  subPrice: { color: Colors.textPrimary, fontWeight: "700", marginTop: 4 },
  label: { color: Colors.textSecondary, fontSize: 12, letterSpacing: 1, marginBottom: 12, textTransform: "uppercase" },
  themeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  themeCard: { width: "48%", padding: 14, borderRadius: Radius.md, backgroundColor: Colors.surface, borderWidth: 1, alignItems: "center" },
  themeSwatch: { width: 60, height: 60, borderRadius: 30 },
  themeSwatch2: { width: 36, height: 36, borderRadius: 18, marginTop: -18, marginLeft: 40 },
  themeName: { color: Colors.textPrimary, fontWeight: "700", marginTop: 10 },
  themeHex: { color: Colors.textMuted, fontSize: 11, marginTop: 2 },
});
