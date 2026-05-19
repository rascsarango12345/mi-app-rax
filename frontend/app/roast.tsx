import { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image, ActivityIndicator, Platform, Alert, Share } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as Clipboard from "expo-clipboard";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

type Intensity = "suave" | "medio" | "brutal";

export default function RoastScreen() {
  const router = useRouter();
  const { t, lang } = useT();
  const [image, setImage] = useState<string | null>(null);
  const [b64, setB64] = useState<string | null>(null);
  const [intensity, setIntensity] = useState<Intensity>("medio");
  const [roast, setRoast] = useState("");
  const [loading, setLoading] = useState(false);
  const [used, setUsed] = useState<number | null>(null);
  const [limit, setLimit] = useState<number | null>(null);

  const showErr = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX", m));

  const pick = async (fromCamera: boolean) => {
    try {
      const perm = fromCamera
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) { showErr("Permiso requerido"); return; }
      const fn = fromCamera ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
      const r = await fn({ mediaTypes: ImagePicker.MediaTypeOptions.Images, quality: 0.7, base64: true });
      if (!r.canceled && r.assets[0]?.base64) {
        setImage(`data:image/jpeg;base64,${r.assets[0].base64}`);
        setB64(r.assets[0].base64);
        setRoast("");
      }
    } catch (e: any) { showErr(e?.message || "Error"); }
  };

  const generate = async () => {
    if (!b64) { showErr("Sube una foto primero"); return; }
    setLoading(true); setRoast("");
    try {
      const r = await apiPost("/roast", { image_base64: b64, intensity, locale: lang });
      setRoast(r.roast); setUsed(r.used_today); setLimit(r.limit);
    } catch (e: any) { showErr(e?.message || "Error"); }
    finally { setLoading(false); }
  };

  const share = async () => {
    try {
      const txt = `🔥 RAX Roast 🔥\n\n${roast}\n\n— Generado con RAX AI`;
      if (Platform.OS === "web") {
        await Clipboard.setStringAsync(txt);
        showErr("Roast copiado al portapapeles ✅");
      } else {
        await Share.share({ message: txt });
      }
    } catch {}
  };

  const intensities: { id: Intensity; label: string; color: string }[] = [
    { id: "suave",  label: t("roast_soft"),   color: "#FFB300" },
    { id: "medio",  label: t("roast_medium"), color: "#FF6E40" },
    { id: "brutal", label: t("roast_brutal"), color: "#E53935" },
  ];

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}><Ionicons name="chevron-back" size={26} color={Colors.electricBlue} /></TouchableOpacity>
        <Text style={styles.title}>{t("roast_title")}</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        {!image && (
          <View style={styles.intro}>
            <Text style={styles.introEmoji}>🔥</Text>
            <Text style={styles.introTitle}>{t("roast_sub")}</Text>
            <Text style={styles.introDesc}>{t("roast_card_desc")}</Text>
          </View>
        )}
        {image && <Image source={{ uri: image }} style={styles.preview} />}
        <View style={styles.intensityRow}>
          <Text style={styles.label}>{t("roast_intensity")}:</Text>
          {intensities.map((it) => (
            <TouchableOpacity
              key={it.id}
              testID={`intensity-${it.id}`}
              style={[styles.intensityBtn, intensity === it.id && { backgroundColor: it.color, borderColor: it.color }]}
              onPress={() => setIntensity(it.id)}
            >
              <Text style={[styles.intensityTxt, intensity === it.id && { color: "#000", fontWeight: "800" }]}>{it.label}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={styles.btnRow}>
          <TouchableOpacity style={styles.secondary} onPress={() => pick(true)}>
            <Ionicons name="camera" size={18} color={Colors.electricBlue} />
            <Text style={styles.secondaryTxt}>{t("lens_take_photo")}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.secondary} onPress={() => pick(false)}>
            <Ionicons name="images" size={18} color={Colors.electricBlue} />
            <Text style={styles.secondaryTxt}>{t("lens_pick_gallery")}</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          testID="btn-generate-roast"
          style={[styles.primary, { backgroundColor: "#FF6E40" }]}
          onPress={generate}
          disabled={loading || !b64}
        >
          {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.primaryTxt}>{t("roast_generate")}</Text>}
        </TouchableOpacity>
        {roast ? (
          <View style={styles.roastCard}>
            <Text style={styles.roastText}>{roast}</Text>
            <View style={styles.actionsRow}>
              <TouchableOpacity style={styles.action} onPress={share}>
                <Ionicons name="share-social" size={18} color={Colors.electricBlue} />
                <Text style={styles.actionTxt}>{t("share")}</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.action} onPress={generate}>
                <Ionicons name="refresh" size={18} color={Colors.electricBlue} />
                <Text style={styles.actionTxt}>{t("roast_again")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : null}
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
  intro: { alignItems: "center", padding: 24, gap: 8 },
  introEmoji: { fontSize: 72 },
  introTitle: { color: Colors.textPrimary, fontSize: 17, fontWeight: "700", marginTop: 8, textAlign: "center" },
  introDesc: { color: Colors.textSecondary, textAlign: "center", fontSize: 13 },
  preview: { width: "100%", height: 260, borderRadius: Radius.lg, backgroundColor: Colors.surfaceElevated },
  intensityRow: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap" },
  label: { color: Colors.textSecondary, fontSize: 13, marginRight: 4 },
  intensityBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, backgroundColor: Colors.surfaceElevated, borderWidth: 1, borderColor: Colors.border },
  intensityTxt: { color: Colors.textPrimary, fontWeight: "600", fontSize: 13 },
  btnRow: { flexDirection: "row", gap: 8 },
  primary: { paddingVertical: 16, borderRadius: Radius.pill, alignItems: "center" },
  primaryTxt: { color: "#000", fontWeight: "800", fontSize: 15 },
  secondary: { flex: 1, flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.electricBlue, paddingVertical: 12, borderRadius: Radius.pill },
  secondaryTxt: { color: Colors.electricBlue, fontWeight: "600" },
  roastCard: { backgroundColor: "rgba(255,110,64,0.10)", padding: 18, borderRadius: Radius.lg, borderWidth: 1, borderColor: "#FF6E40" },
  roastText: { color: Colors.textPrimary, fontSize: 15, lineHeight: 23, fontStyle: "italic" },
  actionsRow: { flexDirection: "row", justifyContent: "flex-end", gap: 16, marginTop: 14 },
  action: { flexDirection: "row", gap: 6, alignItems: "center" },
  actionTxt: { color: Colors.electricBlue, fontWeight: "600" },
  limit: { color: Colors.textMuted, textAlign: "center", fontSize: 12 },
});
