import { useEffect } from "react";
import { View, Text, Image, StyleSheet, Platform } from "react-native";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSequence,
  withDelay,
  Easing,
  withRepeat,
} from "react-native-reanimated";
import { Colors, LOGO_URL } from "@/src/theme";
import { useAuth } from "@/src/auth";

export default function Splash() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const scale = useSharedValue(0.6);
  const opacity = useSharedValue(0);
  const taglineOpacity = useSharedValue(0);
  const glow = useSharedValue(0.3);

  useEffect(() => {
    scale.value = withTiming(1, { duration: 1100, easing: Easing.out(Easing.exp) });
    opacity.value = withTiming(1, { duration: 900 });
    taglineOpacity.value = withDelay(1100, withTiming(1, { duration: 800 }));
    glow.value = withRepeat(
      withSequence(
        withTiming(0.9, { duration: 1600, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.3, { duration: 1600, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );
  }, [glow, opacity, scale, taglineOpacity]);

  useEffect(() => {
    if (loading) return;
    const t = setTimeout(() => {
      if (user) router.replace("/(tabs)/chat");
      else router.replace("/login");
    }, 2400);
    return () => clearTimeout(t);
  }, [loading, user, router]);

  const logoStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }], opacity: opacity.value }));
  const taglineStyle = useAnimatedStyle(() => ({ opacity: taglineOpacity.value }));
  const glowStyle = useAnimatedStyle(() => ({ opacity: glow.value }));

  return (
    <View style={styles.container} testID="splash-screen">
      <LinearGradient
        colors={["#050505", "#08111F", "#0a0726"]}
        style={StyleSheet.absoluteFill}
      />
      <Animated.View style={[styles.glow, glowStyle]} pointerEvents="none">
        <LinearGradient
          colors={["transparent", "rgba(61, 90, 254, 0.5)", "transparent"]}
          start={{ x: 0, y: 0.5 }}
          end={{ x: 1, y: 0.5 }}
          style={{ flex: 1 }}
        />
      </Animated.View>

      <Animated.View style={[styles.logoWrap, logoStyle]}>
        <Image source={{ uri: LOGO_URL }} style={styles.logo} resizeMode="contain" />
      </Animated.View>

      <Animated.View style={[styles.taglineWrap, taglineStyle]}>
        <Text style={styles.poweredBy}>POWERED BY</Text>
        <Text style={styles.rasc}>R · A · S · C</Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    alignItems: "center",
    justifyContent: "center",
  },
  glow: {
    position: "absolute",
    left: 0,
    right: 0,
    top: "40%",
    height: 200,
  },
  logoWrap: {
    width: Platform.OS === "web" ? 420 : 320,
    height: Platform.OS === "web" ? 420 : 320,
    alignItems: "center",
    justifyContent: "center",
  },
  logo: { width: "100%", height: "100%" },
  taglineWrap: {
    position: "absolute",
    bottom: 80,
    alignItems: "center",
  },
  poweredBy: {
    color: Colors.textSecondary,
    fontSize: 11,
    letterSpacing: 6,
    fontWeight: "600",
  },
  rasc: {
    color: Colors.electricBlue,
    fontSize: 38,
    fontWeight: "900",
    marginTop: 10,
    letterSpacing: 8,
    fontFamily: Platform.select({ ios: "Courier-Bold", android: "monospace", default: "monospace" }),
    textShadowColor: Colors.glowBlue,
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 20,
  },
});
