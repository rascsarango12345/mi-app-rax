import { useState } from "react";
import { View, Text, StyleSheet, TouchableOpacity, TextInput, ScrollView, Platform, ActivityIndicator, Alert } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";
import { useAuth } from "@/src/auth";
import { apiPatch, apiPost } from "@/src/api";

const EMOJIS = ["🤖","👨","👩","🦸","🧑‍💻","🦄","🐱","🐶","🦊","🐉","⚡","🔥","🌟","💎","🎮","🎨","🚀","🌈","🎯","👑"];

export default function SettingsScreen() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [emoji, setEmoji] = useState((user as any)?.avatar_emoji || "🤖");
  const [savingProfile, setSavingProfile] = useState(false);

  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [changingPwd, setChangingPwd] = useState(false);

  if (!user) return null;
  const showMsg = (m: string) => (Platform.OS === "web" ? window.alert(m) : Alert.alert("RAX AI", m));

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await apiPatch("/users/me", { name: name.trim(), avatar_emoji: emoji });
      await refresh();
      showMsg("✅ Perfil actualizado");
    } catch (e: any) {
      showMsg(e?.message || "Error");
    } finally {
      setSavingProfile(false);
    }
  };

  const changePassword = async () => {
    if (newPwd !== confirmPwd) {
      showMsg("Las contraseñas nuevas no coinciden");
      return;
    }
    if (newPwd.length < 6) {
      showMsg("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    setChangingPwd(true);
    try {
      await apiPost("/users/me/password", { current_password: currentPwd, new_password: newPwd });
      setCurrentPwd(""); setNewPwd(""); setConfirmPwd("");
      showMsg("✅ Contraseña cambiada");
    } catch (e: any) {
      showMsg(e?.message || "Error");
    } finally {
      setChangingPwd(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>Configuración</Text>
        <View style={{ width: 26 }} />
      </View>

      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.lg }}>
        {/* Profile */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Perfil</Text>

          <Text style={styles.label}>Tu emoji</Text>
          <View style={styles.emojiGrid}>
            {EMOJIS.map((e) => (
              <TouchableOpacity
                key={e}
                testID={`emoji-${e}`}
                style={[styles.emojiBox, emoji === e && styles.emojiBoxActive]}
                onPress={() => setEmoji(e)}
              >
                <Text style={styles.emoji}>{e}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.label}>Tu nombre</Text>
          <TextInput
            testID="input-name"
            style={styles.input}
            value={name}
            onChangeText={setName}
            placeholder="Tu nombre"
            placeholderTextColor={Colors.textMuted}
          />

          <TouchableOpacity testID="btn-save-profile" style={styles.cta} onPress={saveProfile} disabled={savingProfile}>
            {savingProfile ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaText}>Guardar perfil</Text>}
          </TouchableOpacity>
        </View>

        {/* Password */}
        {!user.is_guest && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Cambiar contraseña</Text>
            <TextInput
              testID="input-current-pwd"
              style={styles.input}
              placeholder="Contraseña actual"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
              value={currentPwd}
              onChangeText={setCurrentPwd}
            />
            <TextInput
              testID="input-new-pwd"
              style={styles.input}
              placeholder="Nueva contraseña (mínimo 6 caracteres)"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
              value={newPwd}
              onChangeText={setNewPwd}
            />
            <TextInput
              testID="input-confirm-pwd"
              style={styles.input}
              placeholder="Confirmar nueva contraseña"
              placeholderTextColor={Colors.textMuted}
              secureTextEntry
              value={confirmPwd}
              onChangeText={setConfirmPwd}
            />
            <TouchableOpacity testID="btn-change-pwd" style={styles.cta} onPress={changePassword} disabled={changingPwd}>
              {changingPwd ? <ActivityIndicator color="#000" /> : <Text style={styles.ctaText}>Cambiar contraseña</Text>}
            </TouchableOpacity>
          </View>
        )}

        <TouchableOpacity testID="btn-terms" style={styles.row} onPress={() => router.push("/terms")}>
          <Ionicons name="document-text-outline" size={20} color={Colors.electricBlue} />
          <Text style={styles.rowText}>Términos y Política de Privacidad</Text>
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  section: { backgroundColor: Colors.surface, borderRadius: Radius.lg, padding: Spacing.md, borderWidth: 1, borderColor: Colors.border, gap: 10 },
  sectionTitle: { color: Colors.electricBlue, fontSize: 14, fontWeight: "800", letterSpacing: 1, marginBottom: 4 },
  label: { color: Colors.textSecondary, fontSize: 11, letterSpacing: 1, textTransform: "uppercase" },
  input: { backgroundColor: Colors.surfaceElevated, borderRadius: Radius.md, padding: 12, color: Colors.textPrimary, borderWidth: 1, borderColor: Colors.border },
  cta: { backgroundColor: Colors.electricBlue, paddingVertical: 12, borderRadius: Radius.pill, alignItems: "center", marginTop: 4 },
  ctaText: { color: "#000", fontWeight: "800" },
  emojiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  emojiBox: { width: 44, height: 44, borderRadius: Radius.md, backgroundColor: Colors.surfaceElevated, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: Colors.border },
  emojiBoxActive: { borderColor: Colors.electricBlue, backgroundColor: "rgba(0,229,255,0.15)" },
  emoji: { fontSize: 22 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, padding: Spacing.md, backgroundColor: Colors.surface, borderRadius: Radius.md, borderWidth: 1, borderColor: Colors.border },
  rowText: { color: Colors.textPrimary, flex: 1, fontSize: 15 },
});
