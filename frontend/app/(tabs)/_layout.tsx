import { Tabs, useRouter } from "expo-router";
import { useEffect } from "react";
import { Ionicons } from "@expo/vector-icons";
import { Colors } from "@/src/theme";
import { useAuth } from "@/src/auth";
import { useT } from "@/src/i18n";
import { View, ActivityIndicator } from "react-native";

export default function TabsLayout() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { t } = useT();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <View style={{ flex: 1, backgroundColor: Colors.bg, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator color={Colors.electricBlue} />
      </View>
    );
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.surface,
          borderTopColor: Colors.border,
          height: 64,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarActiveTintColor: Colors.electricBlue,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen
        name="chat"
        options={{
          title: t("tab_chat"),
          tabBarIcon: ({ color, size }) => <Ionicons name="chatbubbles-outline" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="image"
        options={{
          title: t("tab_image"),
          tabBarIcon: ({ color, size }) => <Ionicons name="image-outline" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="voice"
        options={{
          title: t("tab_voice"),
          tabBarIcon: ({ color, size }) => <Ionicons name="mic-outline" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="creator"
        options={{
          title: t("tab_creator"),
          tabBarIcon: ({ color, size }) => <Ionicons name="sparkles-outline" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="game"
        options={{
          title: t("tab_game"),
          tabBarIcon: ({ color, size }) => <Ionicons name="game-controller-outline" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t("tab_profile"),
          tabBarIcon: ({ color, size }) => <Ionicons name="person-outline" color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}
