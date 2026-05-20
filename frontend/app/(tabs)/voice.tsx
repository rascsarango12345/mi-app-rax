import { useEffect, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Platform,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Audio } from "expo-av";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiPost } from "@/src/api";

type Voice = { id: "thalia" | "jennifer" | "alexander" | "steven" | "rasc"; name: string; gender: string; description: string; premium_only?: boolean };

const VOICES: Voice[] = [
  { id: "thalia",    name: "Thalia",    gender: "Mujer",  description: "Cálida y amigable" },
  { id: "jennifer",  name: "Jennifer",  gender: "Mujer",  description: "Brillante y juvenil" },
  { id: "alexander", name: "Alexander", gender: "Hombre", description: "Profunda y serena" },
  { id: "steven",    name: "Steven",    gender: "Hombre", description: "Clara y profesional" },
  { id: "rasc",      name: "RASC (Tu voz)", gender: "Tú", description: "Clon de tu voz", premium_only: true },
];

export default function VoiceScreen() {
  const [voice, setVoice] = useState<Voice["id"]>("thalia");
  const [text, setText] = useState("Hola, soy RAX AI. La inteligencia que piensa contigo.");
  const [loading, setLoading] = useState(false);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [recState, setRecState] = useState<"idle" | "recording" | "transcribing">("idle");

  useEffect(() => {
    return () => {
      if (sound) sound.unloadAsync();
    };
  }, [sound]);

  const showError = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("Error", m));

  const speak = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const r = await apiPost("/voice/tts", { text: text.trim(), voice });
      const uri = `data:${r.mime_type};base64,${r.audio_base64}`;
      if (sound) await sound.unloadAsync();
      const { sound: s } = await Audio.Sound.createAsync({ uri }, { shouldPlay: true });
      setSound(s);
    } catch (e: any) {
      showError(e?.message || "TTS error");
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        showError("Necesitamos permiso del micrófono");
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: r } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(r);
      setRecState("recording");
    } catch (e: any) {
      showError(e?.message || "Error al grabar");
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setRecState("transcribing");
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecording(null);
      if (!uri) return;

      let base64: string;
      let mime = "audio/m4a";
      if (Platform.OS === "web") {
        const blob = await (await fetch(uri)).blob();
        mime = blob.type || "audio/webm";
        base64 = await new Promise<string>((resolve, reject) => {
          const fr = new FileReader();
          fr.onloadend = () => resolve(String(fr.result).split(",")[1] || "");
          fr.onerror = reject;
          fr.readAsDataURL(blob);
        });
      } else {
        const FS = await import("expo-file-system/legacy");
        base64 = await FS.readAsStringAsync(uri, { encoding: FS.EncodingType.Base64 });
      }

      const r = await apiPost("/voice/transcribe", { audio_base64: base64, mime_type: mime });
      setText(r.text);
    } catch (e: any) {
      showError(e?.message || "Error al transcribir");
    } finally {
      setRecState("idle");
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <Text style={styles.title}>Voz IA</Text>
        <Text style={styles.sub}>4 voces realistas · STT + TTS</Text>
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.md }}>
        <Text style={styles.label}>Elige una voz</Text>
        <View style={styles.voicesGrid}>
          {VOICES.map((v) => (
            <TouchableOpacity
              key={v.id}
              testID={`voice-${v.id}`}
              style={[styles.voiceCard, voice === v.id && styles.voiceActive]}
              onPress={() => setVoice(v.id)}
            >
              <Ionicons
                name={v.gender === "Mujer" ? "woman-outline" : "man-outline"}
                size={24}
                color={voice === v.id ? "#000" : Colors.electricBlue}
              />
              <Text style={[styles.voiceName, voice === v.id && { color: "#000" }]}>{v.name}</Text>
              <Text style={[styles.voiceDesc, voice === v.id && { color: "#000" }]}>{v.description}</Text>
              <Text style={[styles.voiceGender, voice === v.id && { color: "#000" }]}>{v.gender}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={[styles.label, { marginTop: Spacing.lg }]}>Texto a decir</Text>
        <TextInput
          testID="tts-input"
          style={styles.input}
          value={text}
          onChangeText={setText}
          multiline
          placeholder="Escribe lo que quieras escuchar..."
          placeholderTextColor={Colors.textMuted}
        />

        <View style={styles.row}>
          <TouchableOpacity testID="btn-speak" style={[styles.cta, { flex: 1 }]} onPress={speak} disabled={loading}>
            {loading ? <ActivityIndicator color="#000" /> : <>
              <Ionicons name="volume-high" size={18} color="#000" />
              <Text style={styles.ctaText}>Hablar</Text>
            </>}
          </TouchableOpacity>
        </View>

        <View style={{ marginTop: Spacing.lg, alignItems: "center" }}>
          <Text style={styles.label}>O dictá con micrófono</Text>
          <TouchableOpacity
            testID="btn-record"
            style={[styles.micBtn, recState === "recording" && styles.micRecording]}
            onPress={recState === "recording" ? stopRecording : startRecording}
            disabled={recState === "transcribing"}
          >
            {recState === "transcribing" ? (
              <ActivityIndicator color="#fff" size="large" />
            ) : (
              <Ionicons
                name={recState === "recording" ? "stop" : "mic"}
                size={36}
                color="#fff"
              />
            )}
          </TouchableOpacity>
          <Text style={styles.micLabel}>
            {recState === "recording"
              ? "Grabando... toca para parar"
              : recState === "transcribing"
              ? "Transcribiendo..."
              : "Toca para grabar"}
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 22, fontWeight: "800" },
  sub: { color: Colors.textSecondary, marginTop: 4 },
  label: { color: Colors.textSecondary, fontSize: 12, letterSpacing: 1, marginBottom: 8, textTransform: "uppercase" },
  voicesGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  voiceCard: {
    width: "48%",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  voiceActive: { backgroundColor: Colors.electricBlue, borderColor: Colors.electricBlue },
  voiceName: { color: Colors.textPrimary, fontWeight: "700", fontSize: 16, marginTop: 6 },
  voiceDesc: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  voiceGender: { color: Colors.textMuted, fontSize: 11, marginTop: 6, letterSpacing: 1 },
  input: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: 14,
    color: Colors.textPrimary,
    borderWidth: 1,
    borderColor: Colors.border,
    minHeight: 90,
    textAlignVertical: "top",
  },
  row: { flexDirection: "row", gap: 10, marginTop: Spacing.md },
  cta: {
    backgroundColor: Colors.electricBlue,
    paddingVertical: 14,
    borderRadius: Radius.pill,
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
  },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 15 },
  micBtn: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: Colors.electricBlue,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 10,
    shadowColor: Colors.electricBlue,
    shadowOpacity: 0.5,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 0 },
  },
  micRecording: { backgroundColor: Colors.error },
  micLabel: { color: Colors.textSecondary, marginTop: 12, fontSize: 13 },
});
