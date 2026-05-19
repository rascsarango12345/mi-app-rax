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
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost } from "@/src/api";

type Msg = { message_id: string; role: "user" | "assistant"; content: string; created_at: string };

export default function ChatThread() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const listRef = useRef<FlatList>(null);

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
    if (!text.trim()) return;
    const userMsg: Msg = {
      message_id: `tmp_${Date.now()}`,
      role: "user",
      content: text.trim(),
      created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    const prompt = text.trim();
    setText("");
    setSending(true);
    try {
      const user_tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const locale = (typeof navigator !== "undefined" && navigator.language) || "es";
      const r = await apiPost("/chat/send", { conversation_id: id, text: prompt, user_tz, locale });
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
          <TextInput
            testID="chat-input"
            style={styles.input}
            placeholder="Escribe un mensaje..."
            placeholderTextColor={Colors.textMuted}
            value={text}
            onChangeText={setText}
            multiline
            maxLength={4000}
            onSubmitEditing={send}
          />
          <TouchableOpacity testID="chat-send" style={styles.sendBtn} onPress={send} disabled={sending || !text.trim()}>
            <Ionicons name="arrow-up" size={20} color="#000" />
          </TouchableOpacity>
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
    flexDirection: "row",
    padding: Spacing.md,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.surface,
    alignItems: "flex-end",
  },
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
