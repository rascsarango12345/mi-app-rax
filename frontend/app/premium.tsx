import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";

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
    price: "$9.99/mes",
    color: Colors.electricBlue,
    perks: ["500 mensajes/día", "100 imágenes/día", "Voces premium", "Sin anuncios", "Soporte prioritario"],
    featured: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$19.99/mes",
    color: Colors.neonGreen,
    perks: ["Ilimitado todo", "API privada", "Análisis avanzado", "Acceso anticipado", "Soporte 24/7"],
  },
];

export default function PremiumScreen() {
  const router = useRouter();

  const onChoose = () => {
    if (Platform.OS === "web") {
      window.alert("Los pagos (Apple Pay, Google Pay, Stripe, PayPal) se habilitarán al publicar la app.");
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
        <Text style={styles.intro}>
          Desbloquea todo el poder de RAX AI: respuestas ilimitadas, imágenes en HD, voces premium y mucho más.
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
                onPress={onChoose}
              >
                <Text style={styles.ctaText}>Elegir {p.name}</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}

        <Text style={styles.payments}>
          💳 Apple Pay · Google Pay · Tarjetas · PayPal (disponibles tras publicar)
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: Spacing.md,
  },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  intro: { color: Colors.textSecondary, textAlign: "center", lineHeight: 20 },
  planCard: {
    backgroundColor: "rgba(18,18,18,0.85)",
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    borderWidth: 1,
  },
  badge: {
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.pill,
    marginBottom: 8,
  },
  badgeText: { color: "#000", fontWeight: "800", fontSize: 10, letterSpacing: 1 },
  planName: { fontSize: 20, fontWeight: "800", letterSpacing: 0.5 },
  price: { color: Colors.textPrimary, fontSize: 26, fontWeight: "800", marginTop: 4 },
  perkRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  perkText: { color: Colors.textPrimary, fontSize: 14 },
  cta: {
    marginTop: Spacing.md,
    paddingVertical: 14,
    borderRadius: Radius.pill,
    alignItems: "center",
  },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 15 },
  payments: { color: Colors.textMuted, textAlign: "center", fontSize: 11, marginTop: 8 },
});
