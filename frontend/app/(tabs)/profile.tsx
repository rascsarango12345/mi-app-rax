import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image, Platform, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/src/auth";
import { Colors, LOGO_URL, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";
import { useState } from "react";

const PLAN_COLORS: Record<string, string> = { free: "#666", premium: Colors.electricBlue, pro: Colors.neonGreen };

export default function Profile() {
  const router = useRouter();
  const { user, logout, refresh } = useAuth();
  const { t, lang } = useT();
  const [cancelling, setCancelling] = useState(false);
  if (!user) return null;

  const confirmCancel = async () => {
    const msg = t("cancel_confirm");
    const doCancel = async () => {
      setCancelling(true);
      try {
        const r = await apiPost("/stripe/cancel-subscription", {});
        const note = r.refund?.refunded
          ? `Reembolso emitido: $${r.refund.amount_usd}. ${r.message}`
          : r.message || "Suscripción cancelada.";
        if (Platform.OS === "web") window.alert(note);
        else Alert.alert("Cancelación completada", note);
        await refresh();
      } catch (e: any) {
        const err = e?.message || "Error al cancelar";
        if (Platform.OS === "web") window.alert(err);
        else Alert.alert("Error", err);
      } finally {
        setCancelling(false);
      }
    };
    if (Platform.OS === "web") {
      if (window.confirm(msg)) await doCancel();
    } else {
      Alert.alert(t("cancel_sub"), msg, [
        { text: t("no"), style: "cancel" },
        { text: t("yes"), style: "destructive", onPress: doCancel },
      ]);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        <View style={styles.card}>
          {user.picture ? (
            <Image source={{ uri: user.picture }} style={styles.avatar} />
          ) : (
            <Image source={{ uri: LOGO_URL }} style={styles.avatar} resizeMode="contain" />
          )}
          <Text style={styles.name}>{user.name}</Text>
          <Text style={styles.email}>{user.email}</Text>
          <View style={[styles.planBadge, { borderColor: PLAN_COLORS[user.plan] }]}>
            <Text style={[styles.planText, { color: PLAN_COLORS[user.plan] }]}>
              PLAN {user.plan.toUpperCase()}
            </Text>
          </View>
          {user.is_guest && (
            <Text style={{ color: Colors.warning, fontSize: 12, marginTop: 6 }}>
              ⚠️ {t("guest_warning")}
            </Text>
          )}
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statValue}>{user.messages_used}</Text>
            <Text style={styles.statLabel}>{t("messages_label")}</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statValue}>{user.images_used}</Text>
            <Text style={styles.statLabel}>{t("images_label")}</Text>
          </View>
        </View>

        <TouchableOpacity testID="btn-settings" style={styles.row} onPress={() => router.push("/settings")}>
          <Ionicons name="settings-outline" size={20} color={Colors.electricBlue} />
          <Text style={styles.rowText}>{t("settings_sub")}</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        <TouchableOpacity testID="btn-premium" style={styles.row} onPress={() => router.push("/premium")}>
          <Ionicons name="diamond-outline" size={20} color={Colors.neonGreen} />
          <Text style={styles.rowText}>{t("upgrade_plan")}</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        {user.plan !== "free" && (
          <TouchableOpacity
            testID="btn-cancel-sub"
            style={[styles.row, { borderColor: Colors.warning }]}
            onPress={confirmCancel}
            disabled={cancelling}
          >
            <Ionicons name="close-circle-outline" size={20} color={Colors.warning} />
            <Text style={[styles.rowText, { color: Colors.warning }]}>
              {cancelling ? t("cancel_processing") : t("cancel_sub")}
            </Text>
            <View style={{ width: 20 }} />
          </TouchableOpacity>
        )}

        <TouchableOpacity testID="btn-support" style={styles.row} onPress={() => router.push("/support")}>
          <Ionicons name="headset-outline" size={20} color={Colors.electricBlue} />
          <Text style={styles.rowText}>{t("support")}</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        {user.is_admin && (
          <TouchableOpacity testID="btn-admin" style={styles.row} onPress={() => router.push("/admin")}>
            <Ionicons name="shield-checkmark-outline" size={20} color={Colors.electricBlue} />
            <Text style={styles.rowText}>{t("admin_panel")}</Text>
            <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.row}
          onPress={() => router.push("/terms")}
        >
          <Ionicons name="document-text-outline" size={20} color={Colors.textSecondary} />
          <Text style={styles.rowText}>{t("terms_privacy")}</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        <TouchableOpacity
          testID="btn-logout"
          style={[styles.row, { borderColor: Colors.error }]}
          onPress={async () => {
            await logout();
            router.replace("/login");
          }}
        >
          <Ionicons name="log-out-outline" size={20} color={Colors.error} />
          <Text style={[styles.rowText, { color: Colors.error }]}>{t("logout")}</Text>
          <View style={{ width: 20 }} />
        </TouchableOpacity>

        <Text style={styles.footer}>RAX AI v1.1 · Powered by RASC · {new Date().toLocaleDateString(lang === "es" ? "es" : lang === "zh" ? "zh-CN" : lang === "hi" ? "hi-IN" : lang === "ru" ? "ru-RU" : "en-US")}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  avatar: { width: 80, height: 80, borderRadius: 40, backgroundColor: Colors.surfaceElevated },
  name: { color: Colors.textPrimary, fontSize: 18, fontWeight: "700", marginTop: 10 },
  email: { color: Colors.textSecondary, fontSize: 13, marginTop: 2 },
  planBadge: {
    marginTop: 10,
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: Radius.pill,
    borderWidth: 1,
  },
  planText: { fontWeight: "700", fontSize: 11, letterSpacing: 1 },
  statsRow: { flexDirection: "row", gap: 10 },
  statBox: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.md,
    alignItems: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  statValue: { color: Colors.electricBlue, fontSize: 24, fontWeight: "800" },
  statLabel: { color: Colors.textSecondary, fontSize: 12, marginTop: 4 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  rowText: { color: Colors.textPrimary, flex: 1, fontSize: 15 },
  footer: { color: Colors.textMuted, textAlign: "center", fontSize: 11, marginTop: 20 },
});
