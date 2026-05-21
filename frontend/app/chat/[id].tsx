import { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Image,
  Alert,
  Share,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

type Msg = {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  has_image?: boolean;
  image_preview?: string;
  has_pdf?: boolean;
  pdf_name?: string;
  generated_pdf?: { filename: string; base64: string } | null;
};

export default function ChatThread() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { t, lang } = useT();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const listRef = useRef<FlatList>(null);
  const [pendingImage, setPendingImage] = useState<string | null>(null);
  const [pendingPdf, setPendingPdf] = useState<{ base64: string; name: string } | null>(null);

  const showMsg = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX AI", m));

  const takePhoto = async () => {
    try {
      const perm = await ImagePicker.requestCameraPermissionsAsync();
      if (!perm.granted) { showMsg("Necesitamos permiso para usar la cámara"); return; }
      const r = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.7,
        base64: true,
        allowsEditing: false,
      });
      if (!r.canceled && r.assets[0]?.base64) {
        setPendingImage(r.assets[0].base64);
        setPendingPdf(null);
      }
    } catch (e: any) { showMsg(e?.message || "Error"); }
  };

  const pickImage = async () => {
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) { showMsg("Necesitamos permiso para tu galería"); return; }
      const r = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.7,
        base64: true,
      });
      if (!r.canceled && r.assets[0]?.base64) {
        setPendingImage(r.assets[0].base64);
        setPendingPdf(null);
      }
    } catch (e: any) { showMsg(e?.message || "Error"); }
  };

  const pickPdf = async () => {
    try {
      const r = await DocumentPicker.getDocumentAsync({
        type: "application/pdf",
        copyToCacheDirectory: true,
        multiple: false,
      });
      if (r.canceled || !r.assets?.[0]) return;
      const asset = r.assets[0];
      let b64 = "";
      if (asset.uri.startsWith("data:")) {
        b64 = asset.uri.split(",", 2)[1] || "";
      } else if (Platform.OS === "web" && (asset as any).file) {
        const file: File = (asset as any).file;
        const buf = await file.arrayBuffer();
        let bin = "";
        const bytes = new Uint8Array(buf);
        for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
        b64 = btoa(bin);
      } else {
        b64 = await FileSystem.readAsStringAsync(asset.uri, { encoding: FileSystem.EncodingType.Base64 });
      }
      if (!b64 || b64.length < 200) { showMsg("PDF vacío o demasiado pequeño"); return; }
      setPendingPdf({ base64: b64, name: asset.name || "documento.pdf" });
      setPendingImage(null);
    } catch (e: any) { showMsg(e?.message || "Error abriendo PDF"); }
  };

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const data = await apiGet(`/conversations/${id}/messages`);
        setMessages(data);
      } catch (e) {
        // new conversation
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handlePdfGenerationTag = async (aiText: string, msgId: string) => {
    // Look for [GENERATE_PDF:title] in AI response
    const m = aiText.match(/\[GENERATE_PDF:([^\]]+)\]/);
    if (!m) return;
    const title = m[1].trim() || "Documento RAX AI";
    // Remove the tag from displayed text
    const cleaned = aiText.replace(/\[GENERATE_PDF:[^\]]+\]/g, "").trim();
    try {
      const r = await apiPost("/pdf/generate", { title, content: cleaned, author: "RAX AI" });
      setMessages((all) => all.map((mm) =>
        mm.message_id === msgId
          ? { ...mm, content: cleaned, generated_pdf: { filename: r.filename, base64: r.pdf_base64 } }
          : mm
      ));
    } catch (e: any) {
      showMsg("⚠️ No pude generar el PDF: " + (e?.message || ""));
    }
  };

  const downloadOrSharePdf = async (filename: string, base64: string) => {
    try {
      if (Platform.OS === "web") {
        const link = document.createElement("a");
        link.href = `data:application/pdf;base64,${base64}`;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
      }
      const path = `${FileSystem.cacheDirectory}${filename}`;
      await FileSystem.writeAsStringAsync(path, base64, { encoding: FileSystem.EncodingType.Base64 });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(path, { mimeType: "application/pdf", dialogTitle: filename });
      } else {
        await Share.share({ url: path, title: filename });
      }
    } catch (e: any) { showMsg("Error compartiendo: " + (e?.message || "")); }
  };

  const send = async () => {
    if (!text.trim() && !pendingImage && !pendingPdf) return;
    const userPrompt = text.trim();
    const imgB64 = pendingImage;
    const pdfData = pendingPdf;
    const userMsg: Msg = {
      message_id: `tmp_${Date.now()}`,
      role: "user",
      content: userPrompt || (imgB64 ? "📷 Foto enviada" : pdfData ? `📄 ${pdfData.name}` : ""),
      created_at: new Date().toISOString(),
      has_image: !!imgB64,
      image_preview: imgB64 ? `data:image/jpeg;base64,${imgB64}` : undefined,
      has_pdf: !!pdfData,
      pdf_name: pdfData?.name,
    };
    setMessages((m) => [...m, userMsg]);
    setText("");
    setPendingImage(null);
    setPendingPdf(null);
    setSending(true);
    try {
      const user_tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const payload: any = { conversation_id: id, text: userPrompt, user_tz, language: lang, locale: lang };
      if (imgB64) payload.image_base64 = imgB64;
      if (pdfData) { payload.pdf_base64 = pdfData.base64; payload.pdf_filename = pdfData.name; }
      const r = await apiPost("/chat/send", payload);
      setMessages((m) => [...m, r.message]);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
      // If AI asked to generate a PDF, do it
      if (r.message?.content?.includes("[GENERATE_PDF:")) {
        await handlePdfGenerationTag(r.message.content, r.message.message_id);
      }
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        {
          message_id: `err_${Date.now()}`,
          role: "assistant",
          content: `⚠️ Error: ${e?.message || "Algo salió mal"}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} testID="btn-back">
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>RAX AI</Text>
        <View style={{ width: 26 }} />
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 80 : 0}
        style={{ flex: 1 }}
      >
        {loading ? (
          <ActivityIndicator color={Colors.electricBlue} style={{ marginTop: 40 }} />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(m) => m.message_id}
            contentContainerStyle={{ padding: Spacing.md, gap: 10 }}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
            renderItem={({ item }) => (
              <View
                testID={`msg-${item.role}`}
                style={[styles.bubble, item.role === "user" ? styles.userBubble : styles.aiBubble]}
              >
                {item.role === "assistant" && <Text style={styles.aiLabel}>RAX AI</Text>}
                {item.image_preview && (
                  <Image source={{ uri: item.image_preview }} style={styles.msgImage} />
                )}
                {item.has_pdf && (
                  <View style={styles.pdfChip}>
                    <Ionicons name="document-text" size={18} color={Colors.electricBlue} />
                    <Text style={styles.pdfChipTxt} numberOfLines={1}>{item.pdf_name || "documento.pdf"}</Text>
                  </View>
                )}
                <Text style={[styles.bubbleText, item.role === "user" && { color: "#fff" }]}>
                  {item.content}
                </Text>
                {item.generated_pdf && (
                  <TouchableOpacity
                    style={styles.pdfBtn}
                    onPress={() => downloadOrSharePdf(item.generated_pdf!.filename, item.generated_pdf!.base64)}
                  >
                    <Ionicons name="download" size={18} color="#000" />
                    <Text style={styles.pdfBtnTxt}>{Platform.OS === "web" ? "Descargar" : "Compartir"} {item.generated_pdf.filename}</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
            ListEmptyComponent={
              <View style={{ padding: 40, alignItems: "center" }}>
                <Text style={{ color: Colors.textSecondary }}>{t("type_message")} 👇</Text>
              </View>
            }
          />
        )}

        {sending && (
          <View style={styles.typingRow}>
            <ActivityIndicator color={Colors.electricBlue} size="small" />
            <Text style={styles.typing}>RAX AI está pensando...</Text>
          </View>
        )}

        <View style={styles.inputBar}>
          {(pendingImage || pendingPdf) && (
            <View style={styles.previewWrap}>
              {pendingImage ? (
                <Image source={{ uri: `data:image/jpeg;base64,${pendingImage}` }} style={styles.preview} />
              ) : (
                <View style={styles.pdfPreview}>
                  <Ionicons name="document-text" size={32} color={Colors.electricBlue} />
                  <Text style={styles.pdfPreviewTxt} numberOfLines={1}>{pendingPdf?.name || "PDF"}</Text>
                </View>
              )}
              <TouchableOpacity style={styles.removePreview} onPress={() => { setPendingImage(null); setPendingPdf(null); }}>
                <Ionicons name="close-circle" size={22} color={Colors.error} />
              </TouchableOpacity>
            </View>
          )}
          <View style={{ flexDirection: "row", gap: 6, alignItems: "flex-end" }}>
            <TouchableOpacity testID="btn-camera" style={styles.attachBtn} onPress={takePhoto}>
              <Ionicons name="camera" size={20} color={Colors.electricBlue} />
            </TouchableOpacity>
            <TouchableOpacity testID="btn-gallery" style={styles.attachBtn} onPress={pickImage}>
              <Ionicons name="image" size={20} color={Colors.electricBlue} />
            </TouchableOpacity>
            <TouchableOpacity testID="btn-pdf" style={styles.attachBtn} onPress={pickPdf}>
              <Ionicons name="document-text" size={20} color={Colors.electricBlue} />
            </TouchableOpacity>
            <TextInput
              testID="chat-input"
              style={styles.input}
              placeholder={pendingImage ? "Pregúntame algo sobre la foto..." : pendingPdf ? "Pregúntame sobre el PDF..." : t("type_message")}
              placeholderTextColor={Colors.textMuted}
              value={text}
              onChangeText={setText}
              multiline
              maxLength={4000}
              onSubmitEditing={send}
            />
            <TouchableOpacity testID="chat-send" style={styles.sendBtn} onPress={send} disabled={sending || (!text.trim() && !pendingImage && !pendingPdf)}>
              <Ionicons name="arrow-up" size={20} color="#000" />
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
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
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  bubble: { padding: 14, borderRadius: Radius.md, maxWidth: "85%" },
  userBubble: { backgroundColor: Colors.electricBlue, alignSelf: "flex-end" },
  aiBubble: { backgroundColor: Colors.surface, alignSelf: "flex-start", borderWidth: 1, borderColor: Colors.border },
  aiLabel: { color: Colors.electricBlue, fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 6 },
  bubbleText: { color: Colors.textPrimary, fontSize: 15, lineHeight: 22 },
  typingRow: { flexDirection: "row", gap: 8, padding: Spacing.md, alignItems: "center" },
  typing: { color: Colors.electricBlue, fontSize: 12, fontWeight: "600" },
  inputBar: { padding: Spacing.md, gap: 8, borderTopWidth: 1, borderTopColor: Colors.border, backgroundColor: Colors.bg },
  attachBtn: {
    width: 40, height: 44, borderRadius: 12, backgroundColor: Colors.surfaceElevated,
    borderWidth: 1, borderColor: Colors.electricBlue, alignItems: "center", justifyContent: "center",
  },
  previewWrap: { alignSelf: "flex-start", position: "relative" },
  preview: { width: 80, height: 80, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.electricBlue },
  pdfPreview: { width: 200, height: 60, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.electricBlue, flexDirection: "row", alignItems: "center", paddingHorizontal: 10, gap: 8, backgroundColor: Colors.surfaceElevated },
  pdfPreviewTxt: { color: Colors.textPrimary, fontSize: 12, flex: 1 },
  removePreview: { position: "absolute", top: -8, right: -8, backgroundColor: "#000", borderRadius: 12 },
  msgImage: { width: 220, height: 160, borderRadius: Radius.md, marginBottom: 6 },
  pdfChip: { flexDirection: "row", alignItems: "center", gap: 6, padding: 8, backgroundColor: Colors.surfaceElevated, borderRadius: Radius.md, marginBottom: 6 },
  pdfChipTxt: { color: Colors.textPrimary, fontSize: 13, flex: 1 },
  pdfBtn: { flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "center", marginTop: 12, backgroundColor: Colors.neonGreen, paddingVertical: 10, borderRadius: 999, paddingHorizontal: 14 },
  pdfBtnTxt: { color: "#000", fontWeight: "800", fontSize: 13 },
  input: {
    flex: 1, backgroundColor: Colors.surfaceElevated, borderRadius: Radius.md,
    paddingHorizontal: 14, paddingVertical: 10, color: Colors.textPrimary,
    borderWidth: 1, borderColor: Colors.border, maxHeight: 120, minHeight: 44,
  },
  sendBtn: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.electricBlue,
    alignItems: "center", justifyContent: "center",
  },
});
