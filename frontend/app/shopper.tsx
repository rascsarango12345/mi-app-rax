import { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, TextInput, Image, ActivityIndicator, Platform, Alert, KeyboardAvoidingView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

export default function ShopperScreen() {
  const router = useRouter();
  const { t, lang } = useT();
  const [query, setQuery] = useState("");
  const [budget, setBudget] = useState("");
  const [image, setImage] = useState<string | null>(null);
  const [b64, setB64] = useState<string | null>(null);
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [used, setUsed] = useState<number | null>(null);
  const [limit, setLimit] = useState<number | null>(null);

  const showErr = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX", m));

  const pick = async () => {
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) return;
      const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7, base64: true });
      if (!r.canceled && r.assets[0]?.base64) {
        setImage(`data:image/jpeg;base64,${r.assets[0].base64}`);
        setB64(r.assets[0].base64);
      }
    } catch (e: any) { showErr(e?.message || "Error"); }
  };

  const search = async () => {
    if (!query.trim() && !b64) { showErr("Describe lo que buscas o sube una foto"); return; }
    setLoading(true); setResult("");
    try {
      const payload: any = { query: query.trim(), locale: lang };
      if (budget) payload.budget_usd = parseFloat(budget);
      if (b64) payload.image_base64 = b64;
      const r = await apiPost("/shopper/recommend", payload);
      setResult(r.recommendations); setUsed(r.used_today); setLimit(r.limit);
    } catch (e: any) { showErr(e?.message || "Error"); }
    finally { setLoading(false); }
  };

  const reset = () => { setQuery(""); setBudget(""); setImage(null); setB64(null); setResult(""); };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}><Ionicons name="chevron-back" size={26} color={Colors.electricBlue} /></TouchableOpacity>
          <Text style={styles.title}>{t("shopper_title")}</Text>
          <View style={{ width: 26 }} />
        </View>
        <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
          {!result && !loading && (
            <View style={styles.intro}>
              <Text style={styles.introEmoji}>🛍️</Text>
              <Text style={styles.introTitle}>{t("shopper_sub")}</Text>
              <Text style={styles.introDesc}>{t("shopper_card_desc")}</Text>
            </View>
          )}
          <TextInput
            testID="shopper-query"
            style={styles.input}
            placeholder={t("shopper_query_placeholder")}
            placeholderTextColor={Colors.textMuted}
            value={query}
            onChangeText={setQuery}
            multiline
          />
          <View style={styles.row}>
            <TextInput
              testID="shopper-budget"
              style={[styles.input, { flex: 1 }]}
              placeholder={`$ ${t("shopper_budget")}`}
              placeholderTextColor={Colors.textMuted}
              keyboardType="numeric"
              value={budget}
              onChangeText={setBudget}
            />
            <TouchableOpacity style={styles.imgBtn} onPress={pick}>
              {image ? <Image source={{ uri: image }} style={styles.imgPreview} /> : <Ionicons name="image-outline" size={26} color={Colors.electricBlue} />}
            </TouchableOpacity>
          </View>
          <TouchableOpacity
            testID="shopper-search"
            style={[styles.cta, { backgroundColor: "#00C853" }]}
            onPress={search}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaTxt}>{t("shopper_search")}</Text>}
          </TouchableOpacity>
          {loading && (
            <View style={styles.loadingBox}>
              <ActivityIndicator color="#00C853" size="large" />
              <Text style={styles.loadingTxt}>{t("shopper_searching")}</Text>
            </View>
          )}
          {result ? (
            <View style={styles.resultBox}>
              <Text style={styles.resultText}>{result}</Text>
              <TouchableOpacity style={styles.linkBtn} onPress={reset}>
                <Text style={styles.linkTxt}>↻ {t("shopper_search_again")}</Text>
              </TouchableOpacity>
            </View>
          ) : null}
          {used !== null && limit !== null && (
            <Text style={styles.limit}>{t("daily_limit_label")}: {used}/{limit}</Text>
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
  intro: { alignItems: "center", padding: 20, gap: 8 },
  introEmoji: { fontSize: 64 },
  introTitle: { color: Colors.textPrimary, fontSize: 16, fontWeight: "700", textAlign: "center" },
  introDesc: { color: Colors.textSecondary, textAlign: "center", fontSize: 13 },
  input: { backgroundColor: Colors.surface, borderRadius: Radius.md, padding: 12, color: Colors.textPrimary, borderWidth: 1, borderColor: Colors.border, fontSize: 14, minHeight: 50 },
  row: { flexDirection: "row", gap: 8 },
  imgBtn: { width: 60, height: 60, borderRadius: Radius.md, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, alignItems: "center", justifyContent: "center", overflow: "hidden" },
  imgPreview: { width: "100%", height: "100%" },
  cta: { paddingVertical: 14, borderRadius: Radius.pill, alignItems: "center" },
  ctaTxt: { color: "#000", fontWeight: "800", fontSize: 15 },
  loadingBox: { alignItems: "center", padding: 24, gap: 10 },
  loadingTxt: { color: "#00C853", fontWeight: "700" },
  resultBox: { backgroundColor: Colors.surface, padding: 16, borderRadius: Radius.lg, borderWidth: 1, borderColor: "#00C853" },
  resultText: { color: Colors.textPrimary, fontSize: 14, lineHeight: 22 },
  linkBtn: { alignItems: "center", marginTop: 14 },
  linkTxt: { color: Colors.electricBlue, fontWeight: "600" },
  limit: { color: Colors.textMuted, textAlign: "center", fontSize: 12 },
});
