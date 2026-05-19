import { useEffect, useState, useCallback } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, ActivityIndicator, Platform, Alert, KeyboardAvoidingView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost, apiDelete } from "@/src/api";
import { useT } from "@/src/i18n";

type Entry = { entry_id: string; content: string; mood: string; ai_insight?: string; date: string; created_at: string };
const MOODS = ["feliz", "motivado", "agradecido", "neutral", "ansioso", "triste", "enojado"] as const;

export default function JournalScreen() {
  const router = useRouter();
  const { t, lang } = useT();
  const [content, setContent] = useState("");
  const [mood, setMood] = useState<typeof MOODS[number]>("neutral");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [insights, setInsights] = useState<any>(null);
  const [tab, setTab] = useState<"new" | "history" | "insights">("new");
  const [saving, setSaving] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);

  const showErr = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX", m));

  const load = useCallback(async () => {
    try { const data = await apiGet("/journal/history"); setEntries(data); } catch (e) {}
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  const save = async () => {
    if (content.trim().length < 3) { showErr("Escribe al menos 3 caracteres"); return; }
    setSaving(true);
    try {
      const r = await apiPost("/journal/entry", { content: content.trim(), mood, locale: lang });
      setEntries((x) => [r, ...x]);
      setContent(""); setMood("neutral");
      showErr("✨ " + (r.ai_insight || "Guardado"));
      setTab("history");
    } catch (e: any) { showErr(e?.message || "Error"); }
    finally { setSaving(false); }
  };

  const removeEntry = async (id: string) => {
    await apiDelete(`/journal/entry/${id}`);
    setEntries((x) => x.filter((e) => e.entry_id !== id));
  };

  const loadInsights = async () => {
    setLoadingInsights(true);
    try { const r = await apiGet("/journal/insights"); setInsights(r); }
    catch (e: any) { showErr(e?.message || "Error"); }
    finally { setLoadingInsights(false); }
  };

  useEffect(() => { if (tab === "insights" && !insights) loadInsights(); }, [tab]);

  const moodEmojis: Record<string, string> = {
    feliz: "😊", motivado: "💪", agradecido: "🙏", neutral: "😐",
    ansioso: "😰", triste: "😢", enojado: "😡",
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}><Ionicons name="chevron-back" size={26} color={Colors.electricBlue} /></TouchableOpacity>
          <Text style={styles.title}>{t("journal_title")}</Text>
          <View style={{ width: 26 }} />
        </View>

        <View style={styles.tabs}>
          {([["new", "+"], ["history", t("journal_history")], ["insights", t("journal_insights")]] as const).map(([id, label]) => (
            <TouchableOpacity
              key={id}
              style={[styles.tabBtn, tab === id && styles.tabActive]}
              onPress={() => setTab(id as any)}
              testID={`journal-tab-${id}`}
            >
              <Text style={[styles.tabTxt, tab === id && styles.tabTxtActive]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
          {tab === "new" && (
            <>
              <Text style={styles.q}>{t("journal_today_question")}</Text>
              <Text style={styles.label}>{t("journal_mood")}</Text>
              <View style={styles.moodRow}>
                {MOODS.map((m) => (
                  <TouchableOpacity
                    key={m}
                    style={[styles.moodBtn, mood === m && styles.moodActive]}
                    onPress={() => setMood(m)}
                  >
                    <Text style={styles.moodEmoji}>{moodEmojis[m]}</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <TextInput
                testID="journal-input"
                style={styles.textarea}
                placeholder={t("journal_placeholder")}
                placeholderTextColor={Colors.textMuted}
                multiline
                value={content}
                onChangeText={setContent}
              />
              <TouchableOpacity testID="journal-save" style={styles.cta} onPress={save} disabled={saving}>
                {saving ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaTxt}>{t("journal_save")}</Text>}
              </TouchableOpacity>
            </>
          )}

          {tab === "history" && (
            entries.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyEmoji}>🌙</Text>
                <Text style={styles.emptyTxt}>{t("journal_empty")}</Text>
              </View>
            ) : (
              entries.map((e) => (
                <View key={e.entry_id} style={styles.entry}>
                  <View style={styles.entryHeader}>
                    <Text style={styles.entryMood}>{moodEmojis[e.mood] || "😐"} {e.mood}</Text>
                    <Text style={styles.entryDate}>{e.date}</Text>
                    <TouchableOpacity onPress={() => removeEntry(e.entry_id)} hitSlop={10}>
                      <Ionicons name="trash-outline" size={16} color={Colors.textMuted} />
                    </TouchableOpacity>
                  </View>
                  <Text style={styles.entryContent}>{e.content}</Text>
                  {e.ai_insight ? (
                    <View style={styles.insightBox}>
                      <Text style={styles.insightLabel}>✨ RAX</Text>
                      <Text style={styles.insightTxt}>{e.ai_insight}</Text>
                    </View>
                  ) : null}
                </View>
              ))
            )
          )}

          {tab === "insights" && (
            loadingInsights ? (
              <View style={styles.loading}>
                <ActivityIndicator color={Colors.electricBlue} size="large" />
                <Text style={styles.loadingTxt}>{t("loading")}</Text>
              </View>
            ) : insights ? (
              <View style={styles.insightCard}>
                <Text style={styles.insightCardTitle}>✨ {t("journal_insights")}</Text>
                <Text style={styles.insightCardTxt}>{insights.summary}</Text>
                {Object.keys(insights.mood_counts || {}).length > 0 && (
                  <View style={styles.moodStats}>
                    {Object.entries<number>(insights.mood_counts).map(([m, c]) => (
                      <View key={m} style={styles.statChip}>
                        <Text style={styles.statChipTxt}>{moodEmojis[m] || "😐"} {m}: {c}</Text>
                      </View>
                    ))}
                  </View>
                )}
                <Text style={styles.totalLabel}>Total: {insights.total} entradas</Text>
              </View>
            ) : null
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  tabs: { flexDirection: "row", padding: Spacing.md, gap: 6 },
  tabBtn: { flex: 1, paddingVertical: 10, borderRadius: Radius.pill, backgroundColor: Colors.surfaceElevated, alignItems: "center", borderWidth: 1, borderColor: Colors.border },
  tabActive: { backgroundColor: "rgba(124,77,255,0.18)", borderColor: "#7C4DFF" },
  tabTxt: { color: Colors.textSecondary, fontWeight: "600", fontSize: 13 },
  tabTxtActive: { color: "#7C4DFF" },
  q: { color: Colors.textPrimary, fontSize: 20, fontWeight: "700" },
  label: { color: Colors.textSecondary, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", marginTop: 4 },
  moodRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  moodBtn: { width: 50, height: 50, borderRadius: 25, backgroundColor: Colors.surfaceElevated, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.border },
  moodActive: { borderColor: "#7C4DFF", backgroundColor: "rgba(124,77,255,0.15)", borderWidth: 2 },
  moodEmoji: { fontSize: 24 },
  textarea: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: 14, color: Colors.textPrimary, borderWidth: 1, borderColor: Colors.border, minHeight: 140, textAlignVertical: "top", fontSize: 15 },
  cta: { backgroundColor: "#7C4DFF", paddingVertical: 14, borderRadius: Radius.pill, alignItems: "center" },
  ctaTxt: { color: "#fff", fontWeight: "800", fontSize: 15 },
  empty: { alignItems: "center", padding: 40, gap: 12 },
  emptyEmoji: { fontSize: 64 },
  emptyTxt: { color: Colors.textSecondary, fontSize: 14, textAlign: "center" },
  entry: { backgroundColor: Colors.surface, padding: 14, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.border, gap: 8 },
  entryHeader: { flexDirection: "row", alignItems: "center", gap: 10 },
  entryMood: { color: Colors.textPrimary, fontSize: 13, fontWeight: "600", flex: 1 },
  entryDate: { color: Colors.textMuted, fontSize: 11 },
  entryContent: { color: Colors.textPrimary, fontSize: 14, lineHeight: 21 },
  insightBox: { backgroundColor: "rgba(124,77,255,0.10)", padding: 10, borderRadius: Radius.md, borderLeftWidth: 3, borderLeftColor: "#7C4DFF" },
  insightLabel: { color: "#7C4DFF", fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 4 },
  insightTxt: { color: Colors.textPrimary, fontSize: 13, lineHeight: 19 },
  loading: { alignItems: "center", padding: 40, gap: 12 },
  loadingTxt: { color: Colors.textSecondary },
  insightCard: { backgroundColor: Colors.surface, padding: 18, borderRadius: Radius.lg, borderWidth: 1, borderColor: "#7C4DFF" },
  insightCardTitle: { color: "#7C4DFF", fontSize: 16, fontWeight: "800", marginBottom: 10 },
  insightCardTxt: { color: Colors.textPrimary, fontSize: 14, lineHeight: 22 },
  moodStats: { flexDirection: "row", flexWrap: "wrap", gap: 6, marginTop: 14 },
  statChip: { backgroundColor: Colors.surfaceElevated, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999 },
  statChipTxt: { color: Colors.textPrimary, fontSize: 12 },
  totalLabel: { color: Colors.textMuted, fontSize: 12, marginTop: 12, textAlign: "center" },
});
