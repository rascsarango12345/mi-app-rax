import { useCallback, useEffect, useState } from "react";
import { View, Text, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPatch } from "@/src/api";

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

export default function AdminScreen() {
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [u, s] = await Promise.all([apiGet("/admin/users"), apiGet("/admin/stats")]);
      setUsers(u);
      setStats(s);
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
  };

  const toggleBlock = async (u: AdminUser) => {
    await apiPatch(`/admin/users/${u.user_id}/block`, { blocked: !u.is_blocked });
    setUsers((x) => x.map((v) => (v.user_id === u.user_id ? { ...v, is_blocked: !u.is_blocked } : v)));
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>Panel Admin</Text>
        <TouchableOpacity onPress={load}>
          <Ionicons name="refresh" size={22} color={Colors.electricBlue} />
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={Colors.electricBlue} style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          ListHeaderComponent={
            stats && (
              <View style={styles.statsGrid}>
                <Stat label="Usuarios" value={stats.total_users} />
                <Stat label="Mensajes" value={stats.total_messages} />
                <Stat label="Imágenes" value={stats.total_images} />
                <Stat label="Premium" value={stats.premium_users} />
                <Stat label="Pro" value={stats.pro_users} />
                <Stat label="Bloqueados" value={stats.blocked_users} />
                <Stat label="Ingresos est." value={`$${stats.estimated_revenue_usd}`} highlight />
              </View>
            )
          }
          data={users}
          keyExtractor={(u) => u.user_id}
          contentContainerStyle={{ padding: Spacing.md, gap: 10 }}
          renderItem={({ item }) => (
            <View style={styles.userCard} testID={`admin-user-${item.user_id}`}>
              <View style={{ flex: 1 }}>
                <Text style={styles.userName}>
                  {item.name} {item.is_admin && "🛡️"} {item.is_blocked && "🚫"}
                </Text>
                <Text style={styles.userEmail}>{item.email}</Text>
                <Text style={styles.userStats}>
                  Plan: {item.plan} · Msgs: {item.messages_used} · Imgs: {item.images_used}
                </Text>
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
            </View>
          )}
        />
      )}
    </SafeAreaView>
  );
}

function Stat({ label, value, highlight }: { label: string; value: any; highlight?: boolean }) {
  return (
    <View style={[styles.statCard, highlight && { borderColor: Colors.neonGreen }]}>
      <Text style={[styles.statValue, highlight && { color: Colors.neonGreen }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: Spacing.md },
  statCard: {
    width: "31%",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
  },
  statValue: { color: Colors.electricBlue, fontSize: 18, fontWeight: "800" },
  statLabel: { color: Colors.textSecondary, fontSize: 11, marginTop: 2 },
  userCard: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  userName: { color: Colors.textPrimary, fontWeight: "700" },
  userEmail: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  userStats: { color: Colors.textMuted, fontSize: 11, marginTop: 4 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 10 },
  planBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radius.pill,
    backgroundColor: Colors.surfaceElevated,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  planBtnActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  planBtnText: { color: Colors.textPrimary, fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  blockBtn: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radius.pill,
    backgroundColor: Colors.surfaceElevated,
    borderWidth: 1,
    borderColor: Colors.border,
  },
});
