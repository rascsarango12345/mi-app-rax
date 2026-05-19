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
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost } from "@/src/api";

type Msg = { message_id: string; role: "user" | "assistant"; content: string; created_at: string; has_image?: boolean; image_preview?: string };

export default function ChatThread() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const listRef = useRef<FlatList>(null);
  const [pendingImage, setPendingImage] = useState<string | null>(null);

  const pickImage = async () => {
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        if (Platform.OS === "web") window.alert("Necesitamos permiso para tu galería");
        return;
      }
      const r = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.7,
        base64: true,
      });
      if (!r.canceled && r.assets[0]?.base64) {
        setPendingImage(r.assets[0].base64);
      }
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    }
  };

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const data = await apiGet(`/conversations/${id}/messages`);
        setMessages(data);
      } catch (e) {
        // new conversation, ignore
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const send = async () => {
    if (!text.trim() && !pendingImage) return;
    const userMsg: Msg = {
      message_id: `tmp_${Date.now()}`,
      role: "user",
      content: text.trim() || "(imagen)",
      created_at: new Date().toISOString(),
      has_image: !!pendingImage,
      image_preview: pendingImage ? `data:image/jpeg;base64,${pendingImage}` : undefined,
    };
    setMessages((m) => [...m, userMsg]);
    const prompt = text.trim() || "Analiza esta imagen en detalle";
    const imgB64 = pendingImage;
    setText("");
    setPendingImage(null);
    setSending(true);
    try {
      const user_tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const locale = (typeof navigator !== "undefined" && navigator.language) || "es";
      const r = await apiPost("/chat/send", { conversation_id: id, text: prompt, user_tz, locale, image_base64: imgB64 || undefined });
      setMessages((m) => [...m, r.message]);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
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
                {item.role === "assistant" && (
                  <Text style={styles.aiLabel}>RAX AI</Text>
                )}
                {item.image_preview && (
                  <Image source={{ uri: item.image_preview }} style={styles.msgImage} />
                )}
                <Text style={[styles.bubbleText, item.role === "user" && { color: "#fff" }]}>
                  {item.content}
                </Text>
              </View>
            )}
            ListEmptyComponent={
              <View style={{ padding: 40, alignItems: "center" }}>
                <Text style={{ color: Colors.textSecondary }}>Escribe tu primer mensaje 👇</Text>
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
          {pendingImage && (
            <View style={styles.previewWrap}>
              <Image source={{ uri: `data:image/jpeg;base64,${pendingImage}` }} style={styles.preview} />
              <TouchableOpacity style={styles.removePreview} onPress={() => setPendingImage(null)}>
                <Ionicons name="close-circle" size={20} color={Colors.error} />
              </TouchableOpacity>
            </View>
          )}
          <View style={{ flexDirection: "row", gap: 8, alignItems: "flex-end" }}>
            <TouchableOpacity testID="btn-attach" style={styles.attachBtn} onPress={pickImage}>
              <Ionicons name="image" size={22} color={Colors.electricBlue} />
            </TouchableOpacity>
            <TextInput
              testID="chat-input"
              style={styles.input}
              placeholder={pendingImage ? "Describe lo que quieres saber..." : "Escribe un mensaje..."}
              placeholderTextColor={Colors.textMuted}
              value={text}
              onChangeText={setText}
              multiline
              maxLength={4000}
              onSubmitEditing={send}
            />
            <TouchableOpacity testID="chat-send" style={styles.sendBtn} onPress={send} disabled={sending || (!text.trim() && !pendingImage)}>
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
  bubble: {
    padding: 14,
    borderRadius: Radius.md,
    maxWidth: "85%",
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: Colors.surfaceElevated,
    borderBottomRightRadius: 4,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  aiBubble: {
    alignSelf: "flex-start",
    backgroundColor: "#000",
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: Colors.electricBlue,
    shadowColor: Colors.electricBlue,
    shadowOpacity: 0.25,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 0 },
  },
  aiLabel: { color: Colors.electricBlue, fontSize: 11, fontWeight: "700", marginBottom: 4, letterSpacing: 1 },
  bubbleText: { color: Colors.textPrimary, fontSize: 15, lineHeight: 22 },
  typingRow: { flexDirection: "row", alignItems: "center", padding: 8, paddingLeft: 16, gap: 8 },
  typing: { color: Colors.textSecondary, fontSize: 12 },
  inputBar: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.surface,
    gap: 6,
  },
  attachBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.surfaceElevated,
    borderWidth: 1,
    borderColor: Colors.electricBlue,
    alignItems: "center",
    justifyContent: "center",
  },
  previewWrap: { alignSelf: "flex-start", position: "relative" },
  preview: { width: 80, height: 80, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.electricBlue },
  removePreview: { position: "absolute", top: -8, right: -8, backgroundColor: "#000", borderRadius: 10 },
  msgImage: { width: 220, height: 160, borderRadius: Radius.md, marginBottom: 6 },
  input: {
    flex: 1,
    backgroundColor: Colors.surfaceElevated,
    borderRadius: Radius.md,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
    maxHeight: 120,
    minHeight: 44,
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.electricBlue,
    alignItems: "center",
    justifyContent: "center",
  },
});
