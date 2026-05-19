import { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Image,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useRouter } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "@/src/auth";
import { Colors, LOGO_URL, Radius, Spacing } from "@/src/theme";
import { useT, LANGUAGES, Lang } from "@/src/i18n";

export default function LoginScreen() {
  const router = useRouter();
  const { login, register, guest, loginWithGoogleSession, user } = useAuth();
  const { lang, setLang, t } = useT();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) router.replace("/(tabs)/chat");
  }, [user, router]);

  // Web: handle Google session_id from URL on mount
  useEffect(() => {
    if (Platform.OS !== "web") return;
    const hash = window.location.hash || "";
    const search = window.location.search || "";
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const session_id = params.get("session_id") || new URLSearchParams(search).get("session_id");
    if (session_id) {
      (async () => {
        try {
          await loginWithGoogleSession(session_id);
          window.history.replaceState(null, "", window.location.pathname);
          router.replace("/(tabs)/chat");
        } catch (e: any) {
          Alert.alert("Error", e?.message || "Google login failed");
        }
      })();
    }
  }, [loginWithGoogleSession, router]);

  const showError = (msg: string) => {
    if (Platform.OS === "web") window.alert(msg);
    else Alert.alert("Error", msg);
  };

  const submit = async () => {
    if (!email || !password) {
      showError(t("email_pwd_required"));
      return;
    }
    setLoading(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password, name);
      router.replace("/(tabs)/chat");
    } catch (e: any) {
      showError(e?.message || t("auth_error"));
    } finally {
      setLoading(false);
    }
  };

  const onGuest = async () => {
    setLoading(true);
    try {
      await guest();
      router.replace("/(tabs)/chat");
    } catch (e: any) {
      showError(e?.message || "Error");
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = async () => {
    try {
      if (Platform.OS === "web") {
        const redirect = window.location.origin + "/login";
        window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
        return;
      }
      const redirect = Linking.createURL("login");
      const url = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirect)}`;
      const result = await WebBrowser.openAuthSessionAsync(url, redirect);
      if (result.type === "success" && result.url) {
        const parsed = Linking.parse(result.url);
        const session_id =
          (parsed.queryParams?.session_id as string) ||
          extractFromFragment(result.url, "session_id");
        if (session_id) {
          await loginWithGoogleSession(session_id);
          router.replace("/(tabs)/chat");
        }
      }
    } catch (e: any) {
      showError(e?.message || "Google sign-in failed");
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={{ flex: 1, backgroundColor: Colors.bg }}
    >
      <LinearGradient
        colors={["#050505", "#080820", "#050505"]}
        style={StyleSheet.absoluteFill}
      />
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Language quick picker */}
        <View style={styles.langRow}>
          {LANGUAGES.map((L) => (
            <TouchableOpacity
              key={L.code}
              testID={`login-lang-${L.code}`}
              style={[styles.langPill, lang === L.code && styles.langPillActive]}
              onPress={() => setLang(L.code as Lang)}
            >
              <Text style={styles.langPillFlag}>{L.flag}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.header}>
          <Image source={{ uri: LOGO_URL }} style={styles.logo} resizeMode="contain" />
          <Text style={styles.tag}>{t("app_tagline")}</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.tabs}>
            <TouchableOpacity
              testID="tab-login"
              style={[styles.tab, mode === "login" && styles.tabActive]}
              onPress={() => setMode("login")}
            >
              <Text style={[styles.tabText, mode === "login" && styles.tabTextActive]}>{t("sign_in")}</Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="tab-register"
              style={[styles.tab, mode === "register" && styles.tabActive]}
              onPress={() => setMode("register")}
            >
              <Text style={[styles.tabText, mode === "register" && styles.tabTextActive]}>{t("create_account")}</Text>
            </TouchableOpacity>
          </View>

          {mode === "register" && (
            <TextInput
              testID="input-name"
              style={styles.input}
              placeholder={t("your_name")}
              placeholderTextColor={Colors.textMuted}
              value={name}
              onChangeText={setName}
            />
          )}

          <TextInput
            testID="input-email"
            style={styles.input}
            placeholder={t("email")}
            placeholderTextColor={Colors.textMuted}
            keyboardType="email-address"
            autoCapitalize="none"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            testID="input-password"
            style={styles.input}
            placeholder={t("password")}
            placeholderTextColor={Colors.textMuted}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          <TouchableOpacity testID="btn-submit" style={styles.primaryBtn} onPress={submit} disabled={loading}>
            {loading ? (
              <ActivityIndicator color="#000" />
            ) : (
              <Text style={styles.primaryBtnText}>{mode === "login" ? t("enter") : t("create_account")}</Text>
            )}
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>{t("continue_with")}</Text>
            <View style={styles.dividerLine} />
          </View>

          <TouchableOpacity testID="btn-google" style={styles.socialBtn} onPress={onGoogle}>
            <Ionicons name="logo-google" size={20} color="#fff" />
            <Text style={styles.socialText}>Google</Text>
          </TouchableOpacity>

          <TouchableOpacity testID="btn-guest" style={styles.guestBtn} onPress={onGuest} disabled={loading}>
            <Ionicons name="person-outline" size={18} color={Colors.electricBlue} />
            <Text style={styles.guestText}>{t("continue_guest")}</Text>
          </TouchableOpacity>

          <Text style={styles.terms}>{t("terms_accept")}</Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function extractFromFragment(url: string, key: string): string | null {
  const idx = url.indexOf("#");
  if (idx < 0) return null;
  const frag = url.slice(idx + 1);
  const params = new URLSearchParams(frag);
  return params.get(key);
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1, padding: Spacing.lg, justifyContent: "center" },
  langRow: { flexDirection: "row", justifyContent: "center", flexWrap: "wrap", gap: 6, marginBottom: 8 },
  langPill: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 999, backgroundColor: Colors.surfaceElevated, borderWidth: 1, borderColor: Colors.border },
  langPillActive: { backgroundColor: "rgba(0,229,255,0.18)", borderColor: Colors.electricBlue },
  langPillFlag: { fontSize: 18 },
  header: { alignItems: "center", marginBottom: Spacing.lg },
  logo: { width: 200, height: 200 },
  tag: { color: Colors.textSecondary, fontSize: 13, letterSpacing: 1, marginTop: -10 },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.md,
    maxWidth: 460,
    width: "100%",
    alignSelf: "center",
  },
  tabs: { flexDirection: "row", gap: Spacing.sm },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: Radius.pill,
    backgroundColor: Colors.surfaceElevated,
  },
  tabActive: { backgroundColor: "rgba(0,229,255,0.12)", borderWidth: 1, borderColor: Colors.electricBlue },
  tabText: { color: Colors.textSecondary, fontWeight: "600" },
  tabTextActive: { color: Colors.electricBlue },
  input: {
    backgroundColor: Colors.surfaceElevated,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 14,
    color: Colors.textPrimary,
    fontSize: 15,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  primaryBtn: {
    backgroundColor: Colors.electricBlue,
    paddingVertical: 16,
    borderRadius: Radius.pill,
    alignItems: "center",
    shadowColor: Colors.electricBlue,
    shadowOpacity: 0.5,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 0 },
  },
  primaryBtnText: { color: "#000", fontWeight: "800", fontSize: 16, letterSpacing: 0.5 },
  divider: { flexDirection: "row", alignItems: "center", gap: 12, marginVertical: 4 },
  dividerLine: { flex: 1, height: 1, backgroundColor: Colors.border },
  dividerText: { color: Colors.textMuted, fontSize: 12 },
  socialBtn: {
    flexDirection: "row",
    gap: 10,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    borderRadius: Radius.pill,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.surfaceElevated,
  },
  socialText: { color: Colors.textPrimary, fontWeight: "600", fontSize: 15 },
  guestBtn: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 14,
    borderRadius: Radius.pill,
    borderWidth: 1,
    borderColor: Colors.electricBlue,
  },
  guestText: { color: Colors.electricBlue, fontWeight: "600" },
  terms: { color: Colors.textMuted, fontSize: 11, textAlign: "center", marginTop: 4 },
});
