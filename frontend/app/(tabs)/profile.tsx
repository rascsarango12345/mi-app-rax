import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/src/auth";
import { Colors, LOGO_URL, Radius, Spacing } from "@/src/theme";

const PLAN_COLORS: Record<string, string> = { free: "#666", premium: Colors.electricBlue, pro: Colors.neonGreen };

export default function Profile() {
  const router = useRouter();
  const { user, logout } = useAuth();
  if (!user) return null;

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
              ⚠️ Cuenta invitado · crea una cuenta para guardar tu progreso
            </Text>
          )}
        </View>

        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statValue}>{user.messages_used}</Text>
            <Text style={styles.statLabel}>Mensajes</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statValue}>{user.images_used}</Text>
            <Text style={styles.statLabel}>Imágenes</Text>
          </View>
        </View>

        <TouchableOpacity testID="btn-premium" style={styles.row} onPress={() => router.push("/premium")}>
          <Ionicons name="diamond-outline" size={20} color={Colors.neonGreen} />
          <Text style={styles.rowText}>Mejora a Premium / Pro</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        {user.is_admin && (
          <TouchableOpacity testID="btn-admin" style={styles.row} onPress={() => router.push("/admin")}>
            <Ionicons name="shield-checkmark-outline" size={20} color={Colors.electricBlue} />
            <Text style={styles.rowText}>Panel de Administrador</Text>
            <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.row}
          onPress={() => {
            if (Platform.OS === "web") {
              window.alert("Términos: Esta app utiliza IA. Privacidad: solo guardamos lo necesario. © AlexSarango 2026.");
            }
          }}
        >
          <Ionicons name="document-text-outline" size={20} color={Colors.textSecondary} />
          <Text style={styles.rowText}>Términos y Privacidad</Text>
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
          <Text style={[styles.rowText, { color: Colors.error }]}>Cerrar sesión</Text>
          <View style={{ width: 20 }} />
        </TouchableOpacity>

        <Text style={styles.footer}>RAX AI v1.0 · Powered by AlexSarango</Text>
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
