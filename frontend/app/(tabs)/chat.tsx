import { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Image,
  Platform,
  KeyboardAvoidingView,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors, LOGO_URL, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost, apiDelete } from "@/src/api";
import { useT } from "@/src/i18n";

type Conv = { conversation_id: string; title: string; updated_at: string };

export default function ChatList() {
  const router = useRouter();
  const { t, lang } = useT();
  const [convs, setConvs] = useState<Conv[]>([]);
  const [loading, setLoading] = useState(true);
  const [quick, setQuick] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiGet("/conversations");
      setConvs(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const startNew = async () => {
    const c = await apiPost("/conversations", {});
    router.push(`/chat/${c.conversation_id}`);
  };

  const sendQuick = async () => {
    if (!quick.trim()) return;
    setSending(true);
    try {
      const user_tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const r = await apiPost("/chat/send", { text: quick.trim(), user_tz, locale: lang });
      setQuick("");
      router.push(`/chat/${r.conversation_id}`);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setSending(false);
    }
  };

  const del = async (id: string) => {
    await apiDelete(`/conversations/${id}`);
    setConvs((x) => x.filter((c) => c.conversation_id !== id));
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Image source={{ uri: LOGO_URL }} style={styles.logoSmall} resizeMode="contain" />
        <Text style={styles.title}>RAX AI</Text>
        <TouchableOpacity testID="btn-new-chat" onPress={startNew} style={styles.newBtn}>
          <Ionicons name="add" size={22} color={Colors.electricBlue} />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
        keyboardVerticalOffset={Platform.OS === "ios" ? 90 : 0}
      >
        {loading ? (
          <ActivityIndicator color={Colors.electricBlue} style={{ marginTop: 40 }} />
        ) : convs.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="chatbubbles-outline" size={64} color={Colors.electricBlue} />
            <Text style={styles.emptyTitle}>{t("empty_chat_title")}</Text>
            <Text style={styles.emptySub}>{t("empty_chat_sub")}</Text>
          </View>
        ) : (
          <FlatList
            data={convs}
            keyExtractor={(c) => c.conversation_id}
            contentContainerStyle={{ padding: Spacing.md, gap: Spacing.sm }}
            renderItem={({ item }) => (
              <TouchableOpacity
                testID={`conv-${item.conversation_id}`}
                style={styles.convItem}
                onPress={() => router.push(`/chat/${item.conversation_id}`)}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.convTitle} numberOfLines={1}>{item.title}</Text>
                  <Text style={styles.convDate}>{new Date(item.updated_at).toLocaleString()}</Text>
                </View>
                <TouchableOpacity onPress={() => del(item.conversation_id)} hitSlop={10}>
                  <Ionicons name="trash-outline" size={18} color={Colors.textMuted} />
                </TouchableOpacity>
              </TouchableOpacity>
            )}
          />
        )}

        <View style={styles.quickBar}>
          <TextInput
            testID="quick-input"
            style={styles.quickInput}
            placeholder={t("ask_anything")}
            placeholderTextColor={Colors.textMuted}
            value={quick}
            onChangeText={setQuick}
            onSubmitEditing={sendQuick}
          />
          <TouchableOpacity testID="quick-send" style={styles.sendBtn} onPress={sendQuick} disabled={sending}>
            {sending ? <ActivityIndicator color="#000" /> : <Ionicons name="arrow-up" size={20} color="#000" />}
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
    padding: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: 10,
  },
  logoSmall: { width: 36, height: 36 },
  title: { color: Colors.textPrimary, fontSize: 20, fontWeight: "800", flex: 1 },
  newBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Colors.surfaceElevated,
    borderWidth: 1,
    borderColor: Colors.electricBlue,
    alignItems: "center",
    justifyContent: "center",
  },
  empty: { alignItems: "center", padding: 40, gap: 8 },
  emptyTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: "700", marginTop: 12 },
  emptySub: { color: Colors.textSecondary, textAlign: "center" },
  convItem: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 12,
  },
  convTitle: { color: Colors.textPrimary, fontWeight: "600", fontSize: 15 },
  convDate: { color: Colors.textMuted, fontSize: 11, marginTop: 4 },
  quickBar: {
    flexDirection: "row",
    padding: Spacing.md,
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.surface,
  },
  quickInput: {
    flex: 1,
    backgroundColor: Colors.surfaceElevated,
    borderRadius: Radius.pill,
    paddingHorizontal: 16,
    paddingVertical: 12,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
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
