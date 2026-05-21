import { useEffect, useState } from "react";
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Platform, ActivityIndicator, Linking, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost, apiGet } from "@/src/api";
import { useAuth } from "@/src/auth";

const PLANS = [
  {
    id: "free",
    name: "Gratis",
    price: "$0",
    color: Colors.textMuted,
    perks: ["30 mensajes/día", "5 imágenes/día", "Voces básicas", "Acceso al chat"],
  },
  {
    id: "premium",
    name: "Premium",
    price: "$5.99/mes",
    color: Colors.electricBlue,
    perks: ["1,000 mensajes/día", "200 imágenes/día", "4 voces premium", "Sin anuncios", "Soporte prioritario"],
    featured: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$15.99/mes",
    color: Colors.neonGreen,
    perks: ["Ilimitado todo", "API privada", "Análisis avanzado", "Acceso anticipado", "Soporte 24/7"],
  },
];

export default function PremiumScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ session_id?: string; status?: string }>();
  const { user, refresh } = useAuth();
  const [loading, setLoading] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Handle return from Stripe Checkout
  useEffect(() => {
    if (params.status === "success" && params.session_id) {
      (async () => {
        try {
          const r = await apiGet(`/stripe/session-status?session_id=${params.session_id}`);
          if (r.paid) {
            setStatusMsg(`✅ ¡Pago exitoso! Ahora eres ${r.plan?.toUpperCase()}.`);
            await refresh();
          } else {
            setStatusMsg(`⏳ Pago en proceso: ${r.payment_status}`);
          }
        } catch (e: any) {
          setStatusMsg(`Error al verificar: ${e?.message}`);
        }
      })();
    } else if (params.status === "cancel") {
      setStatusMsg("Pago cancelado. Puedes intentarlo de nuevo cuando quieras.");
    }
  }, [params.status, params.session_id, refresh]);

  const showError = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("Aviso", m));

  const onChoose = async (planId: "premium" | "pro") => {
    if (!user) {
      showError("Inicia sesión para suscribirte");
      return;
    }
    if (user.is_guest) {
      showError("Crea una cuenta (no invitado) para suscribirte");
      return;
    }
    setLoading(planId);
    try {
      const origin = Platform.OS === "web" ? window.location.origin : (process.env.EXPO_PUBLIC_BACKEND_URL || "");
      const r = await apiPost("/stripe/create-checkout-session", { plan: planId, origin_url: origin });
      if (Platform.OS === "web") {
        window.location.href = r.checkout_url;
      } else {
        await Linking.openURL(r.checkout_url);
      }
    } catch (e: any) {
      showError(e?.message || "Error al iniciar pago");
    } finally {
      setLoading(null);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <LinearGradient colors={["#000", "#0a0826", "#000"]} style={StyleSheet.absoluteFill} />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>Mejora tu plan</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: 14 }}>
        {statusMsg && (
          <View style={styles.statusBox} testID="payment-status">
            <Text style={styles.statusText}>{statusMsg}</Text>
          </View>
        )}
        <Text style={styles.intro}>
          Desbloquea todo el poder de RAX AI. Cancela cuando quieras.
        </Text>
        {PLANS.map((p) => (
          <View
            key={p.id}
            testID={`plan-${p.id}`}
            style={[
              styles.planCard,
              { borderColor: p.color },
              p.featured && { shadowColor: p.color, shadowOpacity: 0.5, shadowRadius: 24, shadowOffset: { width: 0, height: 0 } },
            ]}
          >
            {p.featured && (
              <View style={[styles.badge, { backgroundColor: p.color }]}>
                <Text style={styles.badgeText}>MÁS POPULAR</Text>
              </View>
            )}
            <Text style={[styles.planName, { color: p.color }]}>{p.name}</Text>
            <Text style={styles.price}>{p.price}</Text>
            <View style={{ gap: 6, marginTop: 8 }}>
              {p.perks.map((perk) => (
                <View key={perk} style={styles.perkRow}>
                  <Ionicons name="checkmark-circle" size={16} color={p.color} />
                  <Text style={styles.perkText}>{perk}</Text>
                </View>
              ))}
            </View>
            {p.id !== "free" && (
              <TouchableOpacity
                testID={`choose-${p.id}`}
                style={[styles.cta, { backgroundColor: p.color }]}
                onPress={() => onChoose(p.id as "premium" | "pro")}
                disabled={loading !== null || user?.plan === p.id}
              >
                {loading === p.id ? (
                  <ActivityIndicator color="#000" />
                ) : (
                  <Text style={styles.ctaText}>
                    {user?.plan === p.id ? `✓ Ya tienes ${p.name}` : `Suscribirse a ${p.name}`}
                  </Text>
                )}
              </TouchableOpacity>
            )}
          </View>
        ))}

        <Text style={styles.payments}>
          🔒 Cancela cuando quieras
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  statusBox: { padding: Spacing.md, borderRadius: Radius.md, backgroundColor: "rgba(0,255,102,0.1)", borderWidth: 1, borderColor: Colors.success },
  statusText: { color: Colors.success, fontWeight: "700", textAlign: "center" },
  intro: { color: Colors.textSecondary, textAlign: "center", lineHeight: 20 },
  planCard: { backgroundColor: "rgba(18,18,18,0.85)", borderRadius: Radius.lg, padding: Spacing.lg, borderWidth: 1 },
  badge: { alignSelf: "flex-start", paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.pill, marginBottom: 8 },
  badgeText: { color: "#000", fontWeight: "800", fontSize: 10, letterSpacing: 1 },
  planName: { fontSize: 20, fontWeight: "800", letterSpacing: 0.5 },
  price: { color: Colors.textPrimary, fontSize: 26, fontWeight: "800", marginTop: 4 },
  perkRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  perkText: { color: Colors.textPrimary, fontSize: 14 },
  cta: { marginTop: Spacing.md, paddingVertical: 14, borderRadius: Radius.pill, alignItems: "center" },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 15 },
  payments: { color: Colors.textMuted, textAlign: "center", fontSize: 11, marginTop: 8 },
});
