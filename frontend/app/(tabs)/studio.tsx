import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing, LOGO_URL } from "@/src/theme";
import { useT } from "@/src/i18n";

type Tool = { id: string; emoji: string; titleKey: any; descKey: any; route: string; gradient: [string, string] };

export default function Studio() {
  const router = useRouter();
  const { t } = useT();
  const tools: Tool[] = [
    { id: "lens",     emoji: "📸", titleKey: "lens_title",    descKey: "lens_card_desc",    route: "/lens",    gradient: ["#00E5FF", "#1E88E5"] },
    { id: "journal",  emoji: "🌙", titleKey: "journal_title", descKey: "journal_card_desc", route: "/journal", gradient: ["#7C4DFF", "#3949AB"] },
    { id: "roast",    emoji: "🔥", titleKey: "roast_title",   descKey: "roast_card_desc",   route: "/roast",   gradient: ["#FF6E40", "#D81B60"] },
    { id: "shopper",  emoji: "🛍️", titleKey: "shopper_title", descKey: "shopper_card_desc", route: "/shopper", gradient: ["#00C853", "#00897B"] },
    { id: "game",     emoji: "🎮", titleKey: "tab_game",      descKey: "empty_chat_sub",     route: "/(tabs)/game", gradient: ["#FFB300", "#F57C00"] },
  ];
  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        <View style={styles.header}>
          <Image source={{ uri: LOGO_URL }} style={styles.logo} resizeMode="contain" />
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>{t("studio_title")}</Text>
            <Text style={styles.sub}>{t("studio_sub")}</Text>
          </View>
        </View>
        {tools.map((tool) => (
          <TouchableOpacity
            key={tool.id}
            testID={`studio-${tool.id}`}
            activeOpacity={0.85}
            onPress={() => router.push(tool.route as any)}
          >
            <LinearGradient
              colors={tool.gradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.card}
            >
              <Text style={styles.cardEmoji}>{tool.emoji}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.cardTitle}>{t(tool.titleKey)}</Text>
                <Text style={styles.cardDesc} numberOfLines={3}>{t(tool.descKey)}</Text>
              </View>
              <Ionicons name="chevron-forward" size={26} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 8 },
  logo: { width: 48, height: 48 },
  title: { color: Colors.textPrimary, fontSize: 22, fontWeight: "800" },
  sub: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  card: { flexDirection: "row", alignItems: "center", padding: 18, borderRadius: Radius.lg, gap: 14, minHeight: 110 },
  cardEmoji: { fontSize: 44 },
  cardTitle: { color: "#fff", fontSize: 18, fontWeight: "800" },
  cardDesc: { color: "rgba(255,255,255,0.92)", fontSize: 12, marginTop: 4, lineHeight: 17 },
});
