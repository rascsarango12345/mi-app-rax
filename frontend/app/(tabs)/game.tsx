import { useEffect, useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ScrollView, ActivityIndicator, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { apiGet, apiPost } from "@/src/api";

type Game = { game_id: string; scrambled: string; length: number; category: string; hint: string; answer_hash: string };

export default function GameScreen() {
  const [game, setGame] = useState<Game | null>(null);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ ok: boolean; msg: string } | null>(null);
  const [score, setScore] = useState(0);
  const [showHint, setShowHint] = useState(false);

  const newGame = async () => {
    setLoading(true);
    setFeedback(null);
    setAnswer("");
    setShowHint(false);
    try {
      const g = await apiGet("/game/word");
      setGame(g);
    } catch (e: any) {
      if (Platform.OS === "web") window.alert(e?.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { newGame(); }, []);

  const check = async () => {
    if (!game || !answer.trim()) return;
    setLoading(true);
    try {
      const r = await apiPost("/game/check", { answer: answer.trim().toUpperCase(), answer_hash: game.answer_hash });
      if (r.correct) {
        setScore((s) => s + (showHint ? 5 : 10));
        setFeedback({ ok: true, msg: `¡Correcto! 🎉 +${showHint ? 5 : 10} puntos` });
        setTimeout(() => newGame(), 1800);
      } else {
        setFeedback({ ok: false, msg: "❌ No es esa. ¡Sigue intentando!" });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Juego · Desestrésate 🧠</Text>
          <Text style={styles.sub}>Adivina la palabra desordenada</Text>
        </View>
        <View style={styles.scoreBadge}>
          <Ionicons name="trophy" size={16} color={Colors.neonGreen} />
          <Text style={styles.scoreText}>{score}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        {game ? (
          <>
            <View style={styles.scrambleCard}>
              <Text style={styles.categoryLabel}>{game.category}</Text>
              <Text style={styles.scrambledText} testID="scrambled">{game.scrambled}</Text>
              <Text style={styles.lengthHint}>{game.length} letras</Text>
            </View>

            {!showHint ? (
              <TouchableOpacity testID="show-hint" style={styles.hintBtn} onPress={() => setShowHint(true)}>
                <Ionicons name="bulb-outline" size={16} color={Colors.warning} />
                <Text style={{ color: Colors.warning, fontWeight: "700" }}>Ver pista (-5 puntos)</Text>
              </TouchableOpacity>
            ) : (
              <View style={styles.hintCard}>
                <Ionicons name="bulb" size={16} color={Colors.warning} />
                <Text style={styles.hintText}>💡 {game.hint}</Text>
              </View>
            )}

            <TextInput
              testID="answer-input"
              style={styles.input}
              placeholder="Tu respuesta..."
              placeholderTextColor={Colors.textMuted}
              value={answer}
              onChangeText={(t) => setAnswer(t.toUpperCase())}
              autoCapitalize="characters"
              onSubmitEditing={check}
              maxLength={game.length + 2}
            />

            {feedback && (
              <View style={[styles.feedback, feedback.ok ? styles.feedbackOk : styles.feedbackBad]} testID="feedback">
                <Text style={styles.feedbackText}>{feedback.msg}</Text>
              </View>
            )}

            <View style={{ flexDirection: "row", gap: 8 }}>
              <TouchableOpacity testID="btn-check" style={[styles.cta, { flex: 1 }]} onPress={check} disabled={loading}>
                {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaText}>✓ Verificar</Text>}
              </TouchableOpacity>
              <TouchableOpacity testID="btn-skip" style={[styles.skipBtn]} onPress={newGame}>
                <Ionicons name="play-skip-forward" size={18} color={Colors.electricBlue} />
                <Text style={{ color: Colors.electricBlue, fontWeight: "700" }}>Saltar</Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.footer}>🌟 Toma un descanso y desestrésate jugando</Text>
          </>
        ) : (
          <ActivityIndicator color={Colors.electricBlue} />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: {
    flexDirection: "row", justifyContent: "space-between", alignItems: "center",
    padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  title: { color: Colors.textPrimary, fontSize: 20, fontWeight: "800" },
  sub: { color: Colors.textSecondary, marginTop: 2, fontSize: 12 },
  scoreBadge: {
    flexDirection: "row", alignItems: "center", gap: 6,
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: Radius.pill,
    backgroundColor: "#000", borderWidth: 1, borderColor: Colors.neonGreen,
  },
  scoreText: { color: Colors.neonGreen, fontWeight: "800" },
  scrambleCard: {
    padding: Spacing.lg, borderRadius: Radius.lg,
    backgroundColor: "#000", borderWidth: 1, borderColor: Colors.electricBlue,
    alignItems: "center",
  },
  categoryLabel: { color: Colors.textSecondary, fontSize: 11, letterSpacing: 2, fontWeight: "700" },
  scrambledText: {
    color: Colors.electricBlue, fontSize: 38, fontWeight: "900",
    letterSpacing: 8, marginTop: 14, fontFamily: Platform.select({ ios: "Courier-Bold", android: "monospace", default: "monospace" }),
    textShadowColor: Colors.glowBlue, textShadowOffset: { width: 0, height: 0 }, textShadowRadius: 16,
  },
  lengthHint: { color: Colors.textMuted, fontSize: 12, marginTop: 8 },
  hintBtn: {
    flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 6,
    paddingVertical: 10, borderRadius: Radius.pill,
    borderWidth: 1, borderColor: Colors.warning, backgroundColor: "rgba(255,184,0,0.08)",
  },
  hintCard: {
    flexDirection: "row", alignItems: "center", gap: 8, padding: 12,
    borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.warning,
    backgroundColor: "rgba(255,184,0,0.08)",
  },
  hintText: { color: Colors.warning, flex: 1, fontWeight: "600" },
  input: {
    backgroundColor: Colors.surface, borderRadius: Radius.md, padding: 14,
    color: Colors.electricBlue, fontSize: 22, fontWeight: "700",
    borderWidth: 1, borderColor: Colors.border, textAlign: "center",
    letterSpacing: 4,
  },
  feedback: { padding: 12, borderRadius: Radius.md, alignItems: "center" },
  feedbackOk: { backgroundColor: "rgba(0,255,102,0.15)", borderWidth: 1, borderColor: Colors.success },
  feedbackBad: { backgroundColor: "rgba(255,51,102,0.15)", borderWidth: 1, borderColor: Colors.error },
  feedbackText: { color: Colors.textPrimary, fontWeight: "700", fontSize: 14 },
  cta: { backgroundColor: Colors.electricBlue, paddingVertical: 14, borderRadius: Radius.pill, alignItems: "center" },
  ctaText: { color: "#000", fontWeight: "800", fontSize: 15 },
  skipBtn: {
    flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 14, paddingHorizontal: 18,
    borderRadius: Radius.pill, borderWidth: 1, borderColor: Colors.electricBlue,
  },
  footer: { color: Colors.textMuted, textAlign: "center", fontSize: 11, marginTop: 8 },
});
