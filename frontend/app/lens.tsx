import { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image, ActivityIndicator, Platform, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

export default function LensScreen() {
  const router = useRouter();
  const { t, lang } = useT();
  const [image, setImage] = useState<string | null>(null);
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [used, setUsed] = useState<number | null>(null);
  const [limit, setLimit] = useState<number | null>(null);

  const showErr = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX", m));

  const launch = async (fromCamera: boolean) => {
    try {
      const perm = fromCamera
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) { showErr("Permiso requerido"); return; }
      const fn = fromCamera ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
      const r = await fn({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.75, base64: true });
      if (!r.canceled && r.assets[0]?.base64) {
        setImage(`data:image/jpeg;base64,${r.assets[0].base64}`);
        await scan(r.assets[0].base64);
      }
    } catch (e: any) { showErr(e?.message || "Error"); }
  };

  const scan = async (b64: string) => {
    setLoading(true); setResult("");
    try {
      const r = await apiPost("/lens/scan", { image_base64: b64, locale: lang });
      setResult(r.result);
      setUsed(r.used_today); setLimit(r.limit);
    } catch (e: any) { showErr(e?.message || "Error"); }
    finally { setLoading(false); }
  };

  const reset = () => { setImage(null); setResult(""); };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><Ionicons name="chevron-back" size={26} color={Colors.electricBlue} /></TouchableOpacity>
        <Text style={styles.title}>{t("lens_title")}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        {!image && (
          <View style={styles.intro}>
            <Text style={styles.introEmoji}>📸</Text>
            <Text style={styles.introTitle}>{t("lens_sub")}</Text>
            <Text style={styles.introDesc}>{t("lens_card_desc")}</Text>
          </View>
        )}
        {image && <Image source={{ uri: image }} style={styles.preview} />}
        {loading && (
          <View style={styles.loadingBox}>
            <ActivityIndicator color={Colors.electricBlue} size="large" />
            <Text style={styles.loadingText}>{t("lens_analyzing")}</Text>
          </View>
        )}
        {result ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultText}>{result}</Text>
          </View>
        ) : null}
        <View style={styles.btnRow}>
          <TouchableOpacity testID="btn-camera" style={styles.primary} onPress={() => launch(true)} disabled={loading}>
            <Ionicons name="camera" size={20} color="#000" />
            <Text style={styles.primaryTxt}>{t("lens_take_photo")}</Text>
          </TouchableOpacity>
          <TouchableOpacity testID="btn-gallery" style={styles.secondary} onPress={() => launch(false)} disabled={loading}>
            <Ionicons name="images" size={20} color={Colors.electricBlue} />
            <Text style={styles.secondaryTxt}>{t("lens_pick_gallery")}</Text>
          </TouchableOpacity>
        </View>
        {(result || image) && (
          <TouchableOpacity style={styles.linkBtn} onPress={reset}>
            <Text style={styles.linkTxt}>↻ {t("lens_scan_again")}</Text>
          </TouchableOpacity>
        )}
        {used !== null && limit !== null && (
          <Text style={styles.limit}>{t("daily_limit_label")}: {used}/{limit}</Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  intro: { alignItems: "center", padding: 30, gap: 8 },
  introEmoji: { fontSize: 72 },
  introTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: "700", marginTop: 12 },
  introDesc: { color: Colors.textSecondary, textAlign: "center", fontSize: 14 },
  preview: { width: "100%", height: 280, borderRadius: Radius.lg, backgroundColor: Colors.surfaceElevated },
  loadingBox: { alignItems: "center", padding: 28, gap: 12, backgroundColor: Colors.surface, borderRadius: Radius.lg, borderWidth: 1, borderColor: Colors.border },
  loadingText: { color: Colors.electricBlue, fontSize: 14, fontWeight: "700", letterSpacing: 0.5 },
  resultBox: { backgroundColor: Colors.surface, padding: 16, borderRadius: Radius.lg, borderWidth: 1, borderColor: Colors.border },
  resultText: { color: Colors.textPrimary, fontSize: 14, lineHeight: 22 },
  btnRow: { flexDirection: "row", gap: 8 },
  primary: { flex: 1, flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", backgroundColor: Colors.electricBlue, paddingVertical: 14, borderRadius: Radius.pill },
  primaryTxt: { color: "#000", fontWeight: "800" },
  secondary: { flex: 1, flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.electricBlue, paddingVertical: 14, borderRadius: Radius.pill },
  secondaryTxt: { color: Colors.electricBlue, fontWeight: "700" },
  linkBtn: { alignItems: "center", padding: 8 },
  linkTxt: { color: Colors.electricBlue, fontWeight: "600" },
  limit: { color: Colors.textMuted, textAlign: "center", fontSize: 12, marginTop: 8 },
});
