import { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  Image,
  ActivityIndicator,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

const STYLES = [
  { id: "realista", labelKey: "style_realistic", icon: "camera-outline" as const },
  { id: "anime", labelKey: "style_anime", icon: "sparkles-outline" as const },
  { id: "futurista", labelKey: "style_futuristic", icon: "planet-outline" as const },
  { id: "gamer", label: "Gamer", icon: "game-controller-outline" as const },
  { id: "caricatura", label: "Caricatura", icon: "happy-outline" as const },
  { id: "cinematico", labelKey: "style_cinematic", icon: "film-outline" as const },
];

export default function ImageScreen() {
  const { t } = useT();
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("realista");
  const [loading, setLoading] = useState(false);
  const [image, setImage] = useState<{ data: string; mime: string } | null>(null);

  const generate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setImage(null);
    try {
      const r = await apiPost("/images/generate", { prompt: prompt.trim(), style });
      setImage({ data: r.data_base64, mime: r.mime_type });
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>{t("image_generator_title")}</Text>
        <Text style={styles.sub}>{t("image_generator_sub")}</Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.md }}>
        <Text style={styles.label}>{t("style_label")}</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 4 }}>
          {STYLES.map((s) => (
            <TouchableOpacity
              key={s.id}
              testID={`style-${s.id}`}
              style={[styles.chip, style === s.id && styles.chipActive]}
              onPress={() => setStyle(s.id)}
            >
              <Ionicons name={s.icon} size={14} color={style === s.id ? "#000" : Colors.electricBlue} />
              <Text style={[styles.chipText, style === s.id && { color: "#000", fontWeight: "700" }]}>
                {t(s.labelKey as any)}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Text style={[styles.label, { marginTop: Spacing.md }]}>{t("description_label")}</Text>
        <TextInput
          testID="image-prompt"
          style={styles.input}
          placeholder={t("image_placeholder")}
          placeholderTextColor={Colors.textMuted}
          value={prompt}
          onChangeText={setPrompt}
          multiline
        />

        <TouchableOpacity testID="btn-generate" style={styles.cta} onPress={generate} disabled={loading}>
          {loading ? <ActivityIndicator color="#000" /> : <>
            <Ionicons name="flash" size={18} color="#000" />
            <Text style={styles.ctaText}>{t("generate_btn")}</Text>
          </>}
        </TouchableOpacity>

        {loading && (
          <View style={styles.skeleton}>
            <ActivityIndicator color={Colors.electricBlue} />
            <Text style={{ color: Colors.textSecondary, marginTop: 8 }}>Creando tu obra de arte...</Text>
          </View>
        )}

        {image && (
          <View style={styles.imageWrap}>
            <Image
              source={{ uri: `data:${image.mime};base64,${image.data}` }}
              style={styles.image}
              resizeMode="contain"
            />
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
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: Radius.pill,
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  chipActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  chipText: { color: Colors.textPrimary, fontSize: 13 },
  input: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: 14,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
    minHeight: 90,
    textAlignVertical: "top",
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
  skeleton: { padding: 40, alignItems: "center" },
  imageWrap: {
    marginTop: Spacing.md,
    borderRadius: Radius.lg,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: Colors.electricBlue,
    backgroundColor: Colors.surface,
  },
  image: { width: "100%", aspectRatio: 1 },
});
