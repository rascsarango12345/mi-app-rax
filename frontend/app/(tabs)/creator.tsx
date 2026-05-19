import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";

const TYPES = [
  { id: "tiktok", label: "TikTok Captions", icon: "logo-tiktok" as const },
  { id: "facebook", label: "Facebook Posts", icon: "logo-facebook" as const },
  { id: "youtube", label: "YouTube Titles", icon: "logo-youtube" as const },
  { id: "viral_ideas", label: "Ideas Virales", icon: "trending-up-outline" as const },
  { id: "script", label: "Guiones", icon: "videocam-outline" as const },
  { id: "logo_idea", label: "Ideas de Logo", icon: "color-palette-outline" as const },
  { id: "business_idea", label: "Ideas de Negocio", icon: "rocket-outline" as const },
];

export default function CreatorScreen() {
  const [type, setType] = useState("tiktok");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const gen = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await apiPost("/content/generate", { type, topic: topic.trim(), language: "es" });
      setResult(r.content);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>Creador de Contenido</Text>
        <Text style={styles.sub}>Genera contenido viral en segundos</Text>
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.md }}>
        <Text style={styles.label}>Tipo</Text>
        <View style={styles.grid}>
          {TYPES.map((t) => (
            <TouchableOpacity
              key={t.id}
              testID={`type-${t.id}`}
              style={[styles.tile, type === t.id && styles.tileActive]}
              onPress={() => setType(t.id)}
            >
              <Ionicons name={t.icon} size={22} color={type === t.id ? "#000" : Colors.electricBlue} />
              <Text style={[styles.tileText, type === t.id && { color: "#000", fontWeight: "700" }]}>
                {t.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[styles.label, { marginTop: Spacing.md }]}>Tema</Text>
        <TextInput
          testID="topic-input"
          style={styles.input}
          placeholder="Ej: Recetas saludables, fitness para principiantes..."
          placeholderTextColor={Colors.textMuted}
          value={topic}
          onChangeText={setTopic}
        />

        <TouchableOpacity testID="btn-content" style={styles.cta} onPress={gen} disabled={loading}>
          {loading ? <ActivityIndicator color="#000" /> : <>
            <Ionicons name="sparkles" size={18} color="#000" />
            <Text style={styles.ctaText}>Generar contenido</Text>
          </>}
        </TouchableOpacity>

        {result && (
          <View style={styles.resultBox}>
            <Text style={styles.resultText} selectable>{result}</Text>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 22, fontWeight: "800" },
  sub: { color: Colors.textSecondary, marginTop: 4 },
  label: { color: Colors.textSecondary, fontSize: 12, letterSpacing: 1, marginBottom: 8, textTransform: "uppercase" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tile: {
    width: "48%",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    padding: 12,
    borderRadius: Radius.md,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tileActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  tileText: { color: Colors.textPrimary, fontSize: 13, flex: 1 },
  input: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: 14,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cta: {
    marginTop: Spacing.md,
    backgroundColor: Colors.electricBlue,
    paddingVertical: 16,
    borderRadius: Radius.pill,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
  },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 16 },
  resultBox: {
    marginTop: Spacing.md,
    padding: Spacing.md,
    backgroundColor: "#000",
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.electricBlue,
  },
  resultText: { color: Colors.textPrimary, lineHeight: 22, fontSize: 14 },
});
