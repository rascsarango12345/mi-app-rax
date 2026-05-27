import { useCallback, useEffect, useState, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Modal,
  Keyboard,
  Animated,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost } from "@/src/api";
import { useT } from "@/src/i18n";
import { useAuth } from "@/src/auth";

type Ticket = {
  ticket_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  subject: string;
  status: "open" | "answered" | "closed";
  created_at: string;
  updated_at: string;
  last_sender: "user" | "admin";
};

type TicketMsg = {
  ticket_message_id: string;
  sender_role: "user" | "admin" | "bot";
  sender_name: string;
  message: string;
  created_at: string;
};

export default function SupportScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const { t } = useT();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [creating, setCreating] = useState(false);

  // Selected ticket conversation
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<TicketMsg[]>([]);
  const [replyText, setReplyText] = useState("");
  const [replying, setReplying] = useState(false);

  // Bulletproof keyboard tracking for Modal (iOS Modal doesn't auto-adjust)
  const kbHeight = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const showEvt = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvt = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";
    const showSub = Keyboard.addListener(showEvt, (e) => {
      const h = e?.endCoordinates?.height ?? 0;
      const dur = (e as any)?.duration ?? 250;
      Animated.timing(kbHeight, { toValue: h, duration: dur, useNativeDriver: false }).start();
    });
    const hideSub = Keyboard.addListener(hideEvt, (e) => {
      const dur = (e as any)?.duration ?? 200;
      Animated.timing(kbHeight, { toValue: 0, duration: dur, useNativeDriver: false }).start();
    });
    return () => { showSub.remove(); hideSub.remove(); };
  }, [kbHeight]);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiGet("/support/tickets");
      setTickets(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const openTicket = async (tid: string) => {
    setSelectedId(tid);
    try {
      const r = await apiGet(`/support/tickets/${tid}`);
      setMsgs(r.messages);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    }
  };

  const createTicket = async () => {
    if (!subject.trim() || !message.trim()) return;
    setCreating(true);
    try {
      await apiPost("/support/tickets", { subject: subject.trim(), message: message.trim() });
      setSubject("");
      setMessage("");
      setShowNew(false);
      await load();
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setCreating(false);
    }
  };

  const reply = async () => {
    if (!replyText.trim() || !selectedId) return;
    setReplying(true);
    try {
      const r = await apiPost(`/support/tickets/${selectedId}/reply`, { message: replyText.trim() });
      const msgs_to_add: TicketMsg[] = [r];
      if (r.bot_reply) msgs_to_add.push(r.bot_reply);
      setMsgs((m) => [...m, ...msgs_to_add]);
      setReplyText("");
      await load();
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setReplying(false);
    }
  };

  const requestHuman = async () => {
    if (!selectedId) return;
    try {
      await apiPost(`/support/tickets/${selectedId}/request-human`, {});
      // Reload ticket to see notice
      const r = await apiGet(`/support/tickets/${selectedId}`);
      setMsgs(r.messages);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    }
  };

  const isAdmin = user?.is_admin;

  if (selectedId) {
    return (
      <SafeAreaView style={styles.container} edges={["top"]}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => { setSelectedId(null); setMsgs([]); }}>
            <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
          </TouchableOpacity>
          <Text style={styles.title}>Conversación</Text>
          <View style={{ width: 26 }} />
        </View>
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : "height"}
          style={{ flex: 1 }}
          keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
        >
          <FlatList
            data={msgs}
            keyExtractor={(m) => m.ticket_message_id}
            contentContainerStyle={{ padding: Spacing.md, gap: 10 }}
            renderItem={({ item }) => (
              <View
                testID={`tmsg-${item.sender_role}`}
                style={[
                  styles.bubble,
                  item.sender_role === "user" ? styles.userBubble : item.sender_role === "bot" ? styles.botBubble : styles.adminBubble,
                ]}
              >
                <Text style={styles.bubbleLabel}>
                  {item.sender_role === "admin"
                    ? "🛡️ Soporte (RASC)"
                    : item.sender_role === "bot"
                    ? "🤖 Bot RAX AI"
                    : item.sender_name}
                </Text>
                <Text style={styles.bubbleText}>{item.message}</Text>
              </View>
            )}
          />
          {!isAdmin && (
            <TouchableOpacity testID="btn-request-human" style={styles.humanBtn} onPress={requestHuman}>
              <Ionicons name="person" size={16} color={Colors.warning} />
              <Text style={{ color: Colors.warning, fontWeight: "700", fontSize: 13 }}>Hablar con agente humano (RASC)</Text>
            </TouchableOpacity>
          )}
          <View style={styles.inputBar}>
            <TextInput
              testID="ticket-reply-input"
              style={styles.input}
              placeholder={isAdmin ? "Responde al cliente..." : "Escribe tu respuesta..."}
              placeholderTextColor={Colors.textMuted}
              value={replyText}
              onChangeText={setReplyText}
              multiline
            />
            <TouchableOpacity testID="ticket-reply-send" style={styles.sendBtn} onPress={reply} disabled={replying || !replyText.trim()}>
              {replying ? <ActivityIndicator color="#000" /> : <Ionicons name="arrow-up" size={20} color="#000" />}
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>{isAdmin ? t("support_manager") : t("support_technical")}</Text>
        <TouchableOpacity testID="btn-new-ticket" onPress={() => setShowNew(true)}>
          <Ionicons name="add" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator color={Colors.electricBlue} style={{ marginTop: 40 }} />
      ) : tickets.length === 0 ? (
        <View style={styles.empty}>
          <Ionicons name="chatbubble-ellipses-outline" size={64} color={Colors.electricBlue} />
          <Text style={styles.emptyTitle}>
            {isAdmin ? t("no_tickets_yet") : t("need_help_question")}
          </Text>
          <Text style={styles.emptySub}>
            {isAdmin
              ? t("tickets_users_note")
              : "Abre un ticket y te responderemos lo antes posible."}
          </Text>
          {!isAdmin && (
            <TouchableOpacity testID="btn-new-ticket-empty" style={styles.cta} onPress={() => setShowNew(true)}>
              <Text style={styles.ctaText}>Crear ticket</Text>
            </TouchableOpacity>
          )}
        </View>
      ) : (
        <FlatList
          data={tickets}
          keyExtractor={(t) => t.ticket_id}
          contentContainerStyle={{ padding: Spacing.md, gap: 8 }}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`ticket-${item.ticket_id}`}
              style={styles.ticket}
              onPress={() => openTicket(item.ticket_id)}
            >
              <View style={[styles.statusDot, { backgroundColor: item.status === "open" ? Colors.warning : item.status === "answered" ? Colors.success : Colors.textMuted }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.ticketSubject} numberOfLines={1}>{item.subject}</Text>
                {isAdmin && (
                  <Text style={styles.ticketUser}>👤 {item.user_name} · {item.user_email}</Text>
                )}
                <Text style={styles.ticketMeta}>
                  {item.status.toUpperCase()} · {new Date(item.updated_at).toLocaleString()}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
            </TouchableOpacity>
          )}
        />
      )}

      <Modal visible={showNew} transparent animationType="slide" onRequestClose={() => setShowNew(false)} statusBarTranslucent>
        <View style={styles.modalBg}>
          <TouchableOpacity
            style={{ flex: 1 }}
            activeOpacity={1}
            onPress={() => { Keyboard.dismiss(); setShowNew(false); }}
          />
          <Animated.View style={[styles.modalCard, { paddingBottom: kbHeight }]}>
            <View style={styles.modalHeaderRow}>
              <Text style={styles.modalTitle}>Nuevo ticket</Text>
              <TouchableOpacity
                testID="ticket-close"
                onPress={() => { Keyboard.dismiss(); setShowNew(false); }}
                hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
              >
                <Ionicons name="close" size={28} color={Colors.textPrimary} />
              </TouchableOpacity>
            </View>
            <TextInput
              testID="ticket-subject"
              style={styles.input}
              placeholder="Asunto (ej: Problema con el pago)"
              placeholderTextColor={Colors.textMuted}
              value={subject}
              onChangeText={setSubject}
              returnKeyType="next"
            />
            <TextInput
              testID="ticket-message"
              style={[styles.input, { minHeight: 100, textAlignVertical: "top" }]}
              placeholder="Describe tu problema en detalle..."
              placeholderTextColor={Colors.textMuted}
              value={message}
              onChangeText={setMessage}
              multiline
            />
            <View style={{ flexDirection: "row", gap: 8, marginTop: 4 }}>
              <TouchableOpacity style={[styles.cta, { flex: 1, backgroundColor: Colors.surfaceElevated }]} onPress={() => { Keyboard.dismiss(); setShowNew(false); }}>
                <Text style={[styles.ctaText, { color: Colors.textPrimary }]}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity testID="ticket-create" style={[styles.cta, { flex: 1 }]} onPress={createTicket} disabled={creating}>
                {creating ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaText}>Enviar</Text>}
              </TouchableOpacity>
            </View>
          </Animated.View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  empty: { alignItems: "center", padding: 40, gap: 10 },
  emptyTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: "700", marginTop: 12 },
  emptySub: { color: Colors.textSecondary, textAlign: "center" },
  ticket: {
    flexDirection: "row", alignItems: "center", gap: 12,
    padding: Spacing.md, borderRadius: Radius.md,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
  },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  ticketSubject: { color: Colors.textPrimary, fontWeight: "600" },
  ticketUser: { color: Colors.electricBlue, fontSize: 12, marginTop: 2 },
  ticketMeta: { color: Colors.textMuted, fontSize: 11, marginTop: 4 },
  bubble: { padding: 12, borderRadius: Radius.md, maxWidth: "85%" },
  userBubble: { alignSelf: "flex-end", backgroundColor: Colors.surfaceElevated, borderBottomRightRadius: 4, borderWidth: 1, borderColor: Colors.border },
  adminBubble: { alignSelf: "flex-start", backgroundColor: "#000", borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.neonGreen },
  botBubble: { alignSelf: "flex-start", backgroundColor: "#0a0826", borderBottomLeftRadius: 4, borderWidth: 1, borderColor: Colors.electricBlue },
  humanBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 12, marginHorizontal: Spacing.md, marginBottom: 8, borderRadius: Radius.pill, borderWidth: 1, borderColor: Colors.warning, backgroundColor: "rgba(255,184,0,0.08)" },
  bubbleLabel: { color: Colors.electricBlue, fontSize: 11, fontWeight: "700", marginBottom: 4 },
  bubbleText: { color: Colors.textPrimary, fontSize: 14, lineHeight: 20 },
  inputBar: {
    flexDirection: "row", padding: Spacing.md, gap: 8,
    borderTopWidth: 1, borderTopColor: Colors.border, backgroundColor: Colors.surface,
  },
  input: {
    backgroundColor: Colors.surfaceElevated, borderRadius: Radius.md,
    paddingHorizontal: 14, paddingVertical: 10, color: Colors.textPrimary,
    borderWidth: 1, borderColor: Colors.border, flex: 1, marginBottom: 8,
  },
  sendBtn: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.electricBlue,
    alignItems: "center", justifyContent: "center",
  },
  modalBg: { flex: 1, backgroundColor: "rgba(0,0,0,0.8)", justifyContent: "flex-end" },
  modalCard: {
    backgroundColor: Colors.surface, padding: Spacing.lg,
    borderTopLeftRadius: Radius.lg, borderTopRightRadius: Radius.lg, gap: 8,
  },
  modalHeaderRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 6 },
  modalTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  cta: { backgroundColor: Colors.electricBlue, paddingVertical: 14, borderRadius: Radius.pill, alignItems: "center" },
  ctaText: { color: "#000", fontWeight: "800" },
});
