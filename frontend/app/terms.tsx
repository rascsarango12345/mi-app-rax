import { View, Text, StyleSheet, TouchableOpacity, ActivityIndicator, Platform, Linking } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { WebView } from "react-native-webview";
import { useState } from "react";
import { Colors, Spacing } from "@/src/theme";
import { useT } from "@/src/i18n";

// Pull base URL from env; if missing fall back to relative /api which works on web.
const BACKEND = process.env.EXPO_PUBLIC_BACKEND_URL || "";

export default function TermsScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ doc?: string }>();
  const { lang, t } = useT();
  const [loading, setLoading] = useState(true);
  const doc = params.doc === "privacy" ? "privacy" : "terms";
  const url = `${BACKEND}/api/legal/${doc}?lang=${lang}`;
  const title = doc === "privacy" ? t("privacy_policy") : t("terms_privacy");

  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>{title}</Text>
        <TouchableOpacity onPress={() => Linking.openURL(url)} hitSlop={10}>
          <Ionicons name="open-outline" size={22} color={Colors.electricBlue} />
        </TouchableOpacity>
      </View>
      {Platform.OS === "web" ? (
        // On web, an iframe works perfectly and follows light/dark mode
        <iframe
          src={url}
          style={{ flex: 1, border: 0, width: "100%", height: "100%", background: Colors.bg } as any}
          onLoad={() => setLoading(false)}
        />
      ) : (
        <WebView
          source={{ uri: url }}
          style={{ flex: 1, backgroundColor: Colors.bg }}
          originWhitelist={["*"]}
          onLoadEnd={() => setLoading(false)}
          startInLoadingState
          renderLoading={() => (
            <View style={styles.loader}>
              <ActivityIndicator color={Colors.electricBlue} size="large" />
            </View>
          )}
        />
      )}
      {loading && Platform.OS === "web" && (
        <View style={styles.loader} pointerEvents="none">
          <ActivityIndicator color={Colors.electricBlue} size="large" />
        </View>
      )}
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
  title: { color: Colors.textPrimary, fontSize: 17, fontWeight: "800", flex: 1, textAlign: "center" },
  loader: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: Colors.bg,
  },
});
