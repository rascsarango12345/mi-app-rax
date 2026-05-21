import { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Platform,
  Alert,
  Animated,
  Easing,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Audio } from "expo-av";
import { LinearGradient } from "expo-linear-gradient";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";
import { useT } from "@/src/i18n";

type VoiceId = "thalia" | "jennifer" | "alexander" | "steven";
type Voice = { id: VoiceId; name: string; emoji: string; gender: string; description: string; gradient: [string, string] };

const VOICES: Voice[] = [
  { id: "thalia",    name: "Thalia",    emoji: "👩‍🦱", gender: "Mujer",  description: "Cálida y amigable",    gradient: ["#FF6E40", "#D81B60"] },
  { id: "jennifer",  name: "Jennifer",  emoji: "👩",   gender: "Mujer",  description: "Brillante y juvenil",  gradient: ["#7C4DFF", "#3949AB"] },
  { id: "alexander", name: "Alexander", emoji: "👨",   gender: "Hombre", description: "Profunda y serena",    gradient: ["#1E88E5", "#0D47A1"] },
  { id: "steven",    name: "Steven",    emoji: "👨‍💼", gender: "Hombre", description: "Clara y profesional",  gradient: ["#00C853", "#00897B"] },
];

type Turn = { id: string; role: "user" | "assistant"; content: string };

export default function VoiceScreen() {
  const { t, lang } = useT();
  const [voice, setVoice] = useState<VoiceId>("thalia");
  const [history, setHistory] = useState<Turn[]>([]);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [state, setState] = useState<"idle" | "recording" | "processing" | "speaking">("idle");
  const [stage, setStage] = useState<string>("");
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const scrollRef = useRef<ScrollView>(null);

  const persona = VOICES.find((v) => v.id === voice) || VOICES[0];

  const showError = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("Voz", m));

  // Pulse animation while recording
  useEffect(() => {
    if (state === "recording") {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.3, duration: 600, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
        ])
      ).start();
    } else {
      pulseAnim.stopAnimation();
      pulseAnim.setValue(1);
    }
  }, [state]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (sound) sound.unloadAsync();
      if (recording) recording.stopAndUnloadAsync().catch(() => {});
    };
  }, []);

  // Reset history when changing persona
  const switchVoice = async (newVoice: VoiceId) => {
    if (newVoice === voice) return;
    if (sound) await sound.unloadAsync().catch(() => {});
    setSound(null);
    setVoice(newVoice);
    setHistory([]);
    setState("idle");
    setStage("");
  };

  const startRecording = async () => {
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) { showError("Necesitamos permiso del micrófono"); return; }

      // Stop any playing audio
      if (sound) { await sound.unloadAsync().catch(() => {}); setSound(null); }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });
      const rec = new Audio.Recording();
      await rec.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await rec.startAsync();
      setRecording(rec);
      setState("recording");
    } catch (e: any) {
      showError("Error iniciando grabación: " + (e?.message || ""));
      setState("idle");
    }
  };

  const stopAndSend = async () => {
    if (!recording) return;
    setState("processing");
    setStage("Procesando tu voz...");
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) { showError("No se generó el audio"); setState("idle"); return; }

      // Read audio as base64 using universal fetch + FileReader (works on iOS, Android, Web)
      let audioBase64 = "";
      let mimeType = "audio/m4a";
      try {
        const response = await fetch(uri);
        const blob = await response.blob();
        mimeType = blob.type || (Platform.OS === "web" ? "audio/webm" : "audio/m4a");
        audioBase64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            const idx = result.indexOf(",");
            resolve(idx >= 0 ? result.substring(idx + 1) : result);
          };
          reader.onerror = () => reject(new Error("No pude leer el audio"));
          reader.readAsDataURL(blob);
        });
      } catch (readErr: any) {
        // Fallback: try the legacy FileSystem API on native
        if (Platform.OS !== "web") {
          try {
            const FileSystem = await import("expo-file-system/legacy");
            audioBase64 = await FileSystem.readAsStringAsync(uri, { encoding: "base64" as any });
            mimeType = uri.endsWith(".m4a") ? "audio/m4a" : (uri.endsWith(".webm") ? "audio/webm" : "audio/m4a");
          } catch (fsErr: any) {
            throw new Error("No pude convertir el audio: " + (readErr?.message || fsErr?.message || "error desconocido"));
          }
        } else {
          throw readErr;
        }
      }
      if (!audioBase64 || audioBase64.length < 100) {
        throw new Error("Audio vacío. Asegúrate de haber grabado al menos 1 segundo.");
      }

      setStage(`${persona.name} está pensando...`);
      // Call unified converse endpoint
      const user_tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const historyForApi = history.slice(-6).map((t) => ({ role: t.role, content: t.content }));
      const r = await apiPost("/voice/converse", {
        audio_base64: audioBase64,
        mime_type: mimeType,
        voice,
        history: historyForApi,
        locale: lang,
        user_tz,
      });

      // Update conversation
      const userTurn: Turn = { id: `u_${Date.now()}`, role: "user", content: r.user_text };
      const aiTurn: Turn = { id: `a_${Date.now()}`, role: "assistant", content: r.ai_text };
      setHistory((h) => [...h, userTurn, aiTurn]);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);

      // Play TTS response
      if (r.audio_base64) {
        setState("speaking");
        setStage(`${persona.name} habla...`);
        const audioUri = `data:${r.mime_type || "audio/mp3"};base64,${r.audio_base64}`;
        const { sound: s } = await Audio.Sound.createAsync({ uri: audioUri }, { shouldPlay: true });
        setSound(s);
        s.setOnPlaybackStatusUpdate((status: any) => {
          if (status.didJustFinish) {
            setState("idle");
            setStage("");
          }
        });
      } else {
        setState("idle");
        setStage("");
      }
    } catch (e: any) {
      const msg = e?.message || "Error desconocido";
      showError("Error: " + msg);
      setState("idle");
      setStage("");
    }
  };

  const clearChat = () => {
    if (sound) sound.unloadAsync().catch(() => {});
    setSound(null);
    setHistory([]);
    setState("idle");
    setStage("");
  };

  const mainBtnIcon = state === "recording" ? "stop" : state === "processing" ? "hourglass" : state === "speaking" ? "volume-high" : "mic";
  const mainBtnAction = state === "idle" ? startRecording : state === "recording" ? stopAndSend : undefined;

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>🎙️ Conversación por voz</Text>
        {history.length > 0 && (
          <TouchableOpacity onPress={clearChat}>
            <Ionicons name="refresh" size={22} color={Colors.electricBlue} />
          </TouchableOpacity>
        )}
      </View>

      {/* Persona selector */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.personasRow}>
        {VOICES.map((v) => {
          const active = v.id === voice;
          return (
            <TouchableOpacity
              key={v.id}
              testID={`voice-persona-${v.id}`}
              onPress={() => switchVoice(v.id)}
              activeOpacity={0.85}
              style={[styles.personaCardWrap, active && { transform: [{ scale: 1.05 }] }]}
            >
              <LinearGradient
                colors={active ? v.gradient : ["#1A1A1A", "#2A2A2A"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={[styles.personaCard, active && styles.personaCardActive]}
              >
                <Text style={styles.personaEmoji}>{v.emoji}</Text>
                <Text style={[styles.personaName, active && { color: "#fff" }]}>{v.name}</Text>
                <Text style={[styles.personaDesc, active && { color: "rgba(255,255,255,0.85)" }]}>{v.description}</Text>
              </LinearGradient>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Conversation history */}
      <ScrollView
        ref={scrollRef}
        style={{ flex: 1 }}
        contentContainerStyle={{ padding: Spacing.md, gap: 10 }}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {history.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>{persona.emoji}</Text>
            <Text style={styles.emptyTitle}>Habla con {persona.name}</Text>
            <Text style={styles.emptyDesc}>
              Toca el micrófono y hazle cualquier pregunta. {persona.name} sabe TODO y te responderá con voz.
            </Text>
          </View>
        ) : (
          history.map((turn) => (
            <View
              key={turn.id}
              style={[styles.bubble, turn.role === "user" ? styles.userBubble : styles.aiBubble]}
            >
              {turn.role === "assistant" && (
                <Text style={[styles.aiLabel, { color: persona.gradient[0] }]}>{persona.emoji} {persona.name}</Text>
              )}
              <Text style={[styles.bubbleText, turn.role === "user" && { color: "#fff" }]}>{turn.content}</Text>
            </View>
          ))
        )}
        {(state === "processing" || state === "speaking") && (
          <View style={styles.stageBox}>
            <ActivityIndicator color={persona.gradient[0]} size="small" />
            <Text style={[styles.stageText, { color: persona.gradient[0] }]}>{stage}</Text>
          </View>
        )}
      </ScrollView>

      {/* Recording footer */}
      <View style={styles.footer}>
        <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
          <TouchableOpacity
            testID="voice-record-btn"
            disabled={state === "processing" || state === "speaking"}
            onPress={mainBtnAction}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={state === "recording" ? ["#FF3D00", "#D50000"] : persona.gradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.mainBtn}
            >
              <Ionicons name={mainBtnIcon as any} size={42} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </Animated.View>
        <Text style={styles.hint}>
          {state === "idle" && `Toca para hablar con ${persona.name}`}
          {state === "recording" && "🔴 Grabando... toca para enviar"}
          {state === "processing" && "Procesando..."}
          {state === "speaking" && "Escuchando..."}
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  personasRow: { padding: Spacing.md, gap: 10 },
  personaCardWrap: { borderRadius: Radius.lg },
  personaCard: { width: 130, padding: 12, borderRadius: Radius.lg, alignItems: "center", borderWidth: 1, borderColor: Colors.border },
  personaCardActive: { borderColor: "rgba(255,255,255,0.3)", borderWidth: 2 },
  personaEmoji: { fontSize: 38, marginBottom: 6 },
  personaName: { color: Colors.textPrimary, fontSize: 14, fontWeight: "800" },
  personaDesc: { color: Colors.textSecondary, fontSize: 10, marginTop: 4, textAlign: "center" },
  empty: { padding: 40, alignItems: "center", gap: 10 },
  emptyEmoji: { fontSize: 80 },
  emptyTitle: { color: Colors.textPrimary, fontSize: 20, fontWeight: "800", marginTop: 8 },
  emptyDesc: { color: Colors.textSecondary, textAlign: "center", fontSize: 14, lineHeight: 21, paddingHorizontal: 20 },
  bubble: { padding: 14, borderRadius: Radius.md, maxWidth: "85%" },
  userBubble: { backgroundColor: Colors.electricBlue, alignSelf: "flex-end" },
  aiBubble: { backgroundColor: Colors.surface, alignSelf: "flex-start", borderWidth: 1, borderColor: Colors.border },
  aiLabel: { fontSize: 11, fontWeight: "800", letterSpacing: 1, marginBottom: 6 },
  bubbleText: { color: Colors.textPrimary, fontSize: 15, lineHeight: 22 },
  stageBox: { flexDirection: "row", gap: 8, padding: 12, alignItems: "center", alignSelf: "center" },
  stageText: { fontSize: 13, fontWeight: "700" },
  footer: { padding: Spacing.md, alignItems: "center", gap: 10, borderTopWidth: 1, borderTopColor: Colors.border },
  mainBtn: { width: 90, height: 90, borderRadius: 45, alignItems: "center", justifyContent: "center" },
  hint: { color: Colors.textSecondary, fontSize: 13, fontWeight: "600" },
});
