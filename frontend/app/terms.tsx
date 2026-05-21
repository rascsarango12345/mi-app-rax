import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { Colors, Radius, Spacing } from "@/src/theme";

export default function TermsScreen() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.container} edges={["top"]}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Ionicons name="chevron-back" size={26} color={Colors.electricBlue} />
        </TouchableOpacity>
        <Text style={styles.title}>Términos y Privacidad</Text>
        <View style={{ width: 26 }} />
      </View>
      <ScrollView contentContainerStyle={{ padding: Spacing.md, gap: Spacing.md }}>
        <Section title="📋 Términos de Servicio">
          <P><B>1. Aceptación.</B> Al usar RAX AI ("la App"), aceptas estos Términos y nuestra Política de Privacidad. Si no estás de acuerdo, no uses la App.</P>
          <P><B>2. Servicios.</B> RAX AI es un asistente conversacional de IA creado por RASC (Sarango Cabrera) que ofrece chat, generación de imágenes, voz, creación de contenido y herramientas adicionales.</P>
          <P><B>3. Cuentas.</B> Eres responsable de la seguridad de tu cuenta y contraseña. Notifícanos de inmediato si sospechas un uso no autorizado.</P>
          <P><B>4. Planes y pagos.</B> Ofrecemos plan Gratis (30 msgs, 5 imágenes, 10 fotos por chat al día), Premium ($5.99/mes: 1,000 msgs, 200 imágenes, 40 fotos por chat al día) y Pro ($9.99/mes: uso ilimitado). Pagos procesados de forma segura por la tienda de aplicaciones correspondiente.</P>
          <P><B>5. Reembolsos.</B> Puedes cancelar tu suscripción desde tu Perfil. El reembolso del último cobro se procesa al instante y aparece en tu método de pago en 5-10 días hábiles.</P>
          <P><B>6. Uso aceptable.</B> No utilices la App para: actividades ilegales, contenido que incite al odio, violencia o pornografía infantil, spam, ingeniería inversa, suplantación o explotar vulnerabilidades. Nos reservamos el derecho de bloquear cuentas que infrinjan estas reglas.</P>
          <P><B>7. Propiedad intelectual.</B> El contenido generado por la IA pertenece al usuario que lo solicitó, pero RAX AI y su tecnología son propiedad de RASC. No reclamas derechos sobre el código, marca ni infraestructura.</P>
          <P><B>8. Limitación de responsabilidad.</B> RAX AI puede cometer errores. No nos hacemos responsables de decisiones que tomes basadas en respuestas de la IA, especialmente en temas médicos, legales o financieros. Consulta a un profesional cualificado.</P>
          <P><B>9. Modificaciones.</B> Podemos actualizar estos términos. Te notificaremos cambios importantes. El uso continuado significa aceptación.</P>
          <P><B>10. Ley aplicable.</B> Estos términos se rigen por las leyes aplicables al país de residencia de RASC.</P>
        </Section>

        <Section title="🔒 Política de Privacidad">
          <P><B>Datos que recolectamos:</B> email, nombre, contraseña encriptada (bcrypt), mensajes y contenido que envías, fotos que subes para análisis, plan de suscripción, datos de uso (cantidad de mensajes/imágenes/fotos), y datos de pago procesados de forma segura por la tienda de aplicaciones.</P>
          <P><B>Cómo usamos tus datos:</B> Para proveer la IA, mejorar el servicio, procesar pagos, prevenir abuso y soporte. NO vendemos tus datos a terceros.</P>
          <P><B>Compartir datos:</B> Solo con: (a) los procesadores de pago de la tienda de aplicaciones, (b) Anthropic/Google/OpenAI para procesar consultas de IA (los proveedores tienen sus propias políticas), (c) autoridades cuando legalmente sea requerido.</P>
          <P><B>Almacenamiento:</B> Tus conversaciones se guardan en MongoDB cifrado. Las imágenes generadas se guardan como base64 en tu cuenta.</P>
          <P><B>Tus derechos:</B> Puedes solicitar acceso, rectificación o eliminación de tus datos escribiendo desde la sección de Soporte. Cancelar tu cuenta elimina tu información personal.</P>
          <P><B>Seguridad:</B> Usamos HTTPS, JWT, bcrypt para contraseñas, y prácticas de seguridad estándar. Sin embargo, ningún sistema es 100% inviolable.</P>
          <P><B>Menores:</B> RAX AI no está dirigido a menores de 13 años. Si descubrimos que un menor creó una cuenta, la eliminaremos.</P>
          <P><B>Cookies/Web:</B> Usamos localStorage para mantener tu sesión iniciada. No usamos cookies de rastreo de terceros.</P>
          <P><B>Contacto:</B> rascsarango12345@gmail.com</P>
        </Section>

        <Text style={styles.footer}>Última actualización: 19 de mayo de 2026 · © RASC (Sarango Cabrera)</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function Section({ title, children }: any) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}
function P({ children }: any) { return <Text style={styles.p}>{children}</Text>; }
function B({ children }: any) { return <Text style={styles.b}>{children}</Text>; }

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  header: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  title: { color: Colors.textPrimary, fontSize: 18, fontWeight: "800" },
  section: { backgroundColor: Colors.surface, borderRadius: Radius.lg, padding: Spacing.md, borderWidth: 1, borderColor: Colors.border, gap: 10 },
  sectionTitle: { color: Colors.electricBlue, fontSize: 16, fontWeight: "800" },
  p: { color: Colors.textPrimary, lineHeight: 20, fontSize: 13 },
  b: { fontWeight: "800", color: Colors.neonGreen },
  footer: { color: Colors.textMuted, textAlign: "center", fontSize: 11 },
});
