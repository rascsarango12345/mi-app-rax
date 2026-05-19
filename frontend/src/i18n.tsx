import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import * as Localization from "expo-localization";
import { storage } from "@/src/utils/storage";

export type Lang = "es" | "en" | "hi" | "zh" | "ru";

export const LANGUAGES: { code: Lang; name: string; flag: string; native: string }[] = [
  { code: "es", name: "Spanish", flag: "🇪🇸", native: "Español" },
  { code: "en", name: "English", flag: "🇺🇸", native: "English" },
  { code: "hi", name: "Hindi", flag: "🇮🇳", native: "हिन्दी" },
  { code: "zh", name: "Chinese", flag: "🇨🇳", native: "中文" },
  { code: "ru", name: "Russian", flag: "🇷🇺", native: "Русский" },
];

const T = {
  // App
  app_tagline: { es: "La Inteligencia que Piensa Contigo", en: "The Intelligence That Thinks With You", hi: "वह बुद्धिमत्ता जो आपके साथ सोचती है", zh: "与您一起思考的智能", ru: "Интеллект, который думает с вами" },
  powered_by: { es: "DESARROLLADO POR", en: "POWERED BY", hi: "द्वारा संचालित", zh: "技术支持", ru: "ОТ" },

  // Auth / Login
  sign_in: { es: "Iniciar sesión", en: "Sign in", hi: "साइन इन", zh: "登录", ru: "Войти" },
  create_account: { es: "Crear cuenta", en: "Create account", hi: "खाता बनाएं", zh: "创建账户", ru: "Создать аккаунт" },
  email: { es: "Email", en: "Email", hi: "ईमेल", zh: "电子邮件", ru: "Эл. почта" },
  password: { es: "Contraseña", en: "Password", hi: "पासवर्ड", zh: "密码", ru: "Пароль" },
  your_name: { es: "Tu nombre", en: "Your name", hi: "आपका नाम", zh: "你的名字", ru: "Ваше имя" },
  enter: { es: "Entrar", en: "Enter", hi: "प्रवेश करें", zh: "进入", ru: "Войти" },
  continue_with: { es: "o continúa con", en: "or continue with", hi: "या जारी रखें", zh: "或继续使用", ru: "или продолжить с" },
  continue_guest: { es: "Continuar como invitado", en: "Continue as guest", hi: "अतिथि के रूप में जारी रखें", zh: "以访客身份继续", ru: "Продолжить как гость" },
  terms_accept: { es: "Al continuar aceptas los Términos y la Política de Privacidad de RAX AI.", en: "By continuing you accept the Terms and Privacy Policy of RAX AI.", hi: "जारी रखकर आप RAX AI की शर्तें और गोपनीयता नीति स्वीकार करते हैं।", zh: "继续即表示您接受 RAX AI 的条款和隐私政策。", ru: "Продолжая, вы принимаете Условия и Политику конфиденциальности RAX AI." },
  email_pwd_required: { es: "Email y contraseña son obligatorios", en: "Email and password are required", hi: "ईमेल और पासवर्ड आवश्यक हैं", zh: "电子邮件和密码为必填项", ru: "Электронная почта и пароль обязательны" },
  auth_error: { es: "Error de autenticación", en: "Authentication error", hi: "प्रमाणीकरण त्रुटि", zh: "认证错误", ru: "Ошибка авторизации" },

  // Tabs
  tab_chat: { es: "Chat", en: "Chat", hi: "चैट", zh: "聊天", ru: "Чат" },
  tab_image: { es: "Imagen", en: "Image", hi: "छवि", zh: "图像", ru: "Изображение" },
  tab_voice: { es: "Voz", en: "Voice", hi: "आवाज़", zh: "语音", ru: "Голос" },
  tab_creator: { es: "Creador", en: "Creator", hi: "क्रिएटर", zh: "创作者", ru: "Создатель" },
  tab_game: { es: "Juego", en: "Game", hi: "खेल", zh: "游戏", ru: "Игра" },
  tab_profile: { es: "Perfil", en: "Profile", hi: "प्रोफ़ाइल", zh: "个人资料", ru: "Профиль" },

  // Chat
  ask_anything: { es: "Pregunta cualquier cosa a RAX AI...", en: "Ask RAX AI anything...", hi: "RAX AI से कुछ भी पूछें...", zh: "向 RAX AI 询问任何事情...", ru: "Спросите RAX AI о чём угодно..." },
  type_message: { es: "Escribe un mensaje...", en: "Type a message...", hi: "एक संदेश लिखें...", zh: "输入消息...", ru: "Введите сообщение..." },
  thinking: { es: "RAX AI está pensando...", en: "RAX AI is thinking...", hi: "RAX AI सोच रहा है...", zh: "RAX AI 正在思考...", ru: "RAX AI думает..." },
  empty_chat_title: { es: "Empieza tu primera conversación", en: "Start your first conversation", hi: "अपनी पहली बातचीत शुरू करें", zh: "开始你的第一次对话", ru: "Начните первый разговор" },
  empty_chat_sub: { es: "RAX AI está lista para responder cualquier pregunta.", en: "RAX AI is ready to answer any question.", hi: "RAX AI किसी भी प्रश्न का उत्तर देने के लिए तैयार है।", zh: "RAX AI 已准备好回答任何问题。", ru: "RAX AI готов ответить на любой вопрос." },
  attach_photo: { es: "Adjuntar foto", en: "Attach photo", hi: "फ़ोटो संलग्न करें", zh: "附加照片", ru: "Прикрепить фото" },

  // Image generator
  image_prompt_placeholder: { es: "Describe la imagen que quieres crear...", en: "Describe the image you want to create...", hi: "उस छवि का वर्णन करें जिसे आप बनाना चाहते हैं...", zh: "描述您想要创建的图像...", ru: "Опишите изображение, которое вы хотите создать..." },
  generate: { es: "Generar", en: "Generate", hi: "उत्पन्न करें", zh: "生成", ru: "Создать" },
  generating: { es: "Generando...", en: "Generating...", hi: "उत्पन्न हो रहा है...", zh: "生成中...", ru: "Создание..." },
  style: { es: "Estilo", en: "Style", hi: "शैली", zh: "风格", ru: "Стиль" },

  // Voice
  speak_now: { es: "Habla ahora...", en: "Speak now...", hi: "अभी बोलें...", zh: "现在说话...", ru: "Говорите..." },
  start_recording: { es: "Iniciar grabación", en: "Start recording", hi: "रिकॉर्डिंग शुरू करें", zh: "开始录音", ru: "Начать запись" },
  stop_recording: { es: "Detener", en: "Stop", hi: "रोकें", zh: "停止", ru: "Остановить" },
  choose_voice: { es: "Elige una voz", en: "Choose a voice", hi: "एक आवाज़ चुनें", zh: "选择语音", ru: "Выберите голос" },

  // Creator
  creator_title: { es: "Herramientas de Creador", en: "Creator Tools", hi: "क्रिएटर टूल्स", zh: "创作者工具", ru: "Инструменты создателя" },

  // Profile
  upgrade_plan: { es: "Mejora a Premium / Pro", en: "Upgrade to Premium / Pro", hi: "Premium / Pro में अपग्रेड करें", zh: "升级到 Premium / Pro", ru: "Перейти на Premium / Pro" },
  cancel_sub: { es: "Cancelar suscripción · Reembolso instantáneo", en: "Cancel subscription · Instant refund", hi: "सदस्यता रद्द करें · तत्काल वापसी", zh: "取消订阅 · 即时退款", ru: "Отменить подписку · Мгновенный возврат" },
  cancel_processing: { es: "Procesando...", en: "Processing...", hi: "प्रोसेस हो रहा है...", zh: "处理中...", ru: "Обработка..." },
  cancel_confirm: { es: "¿Cancelar tu suscripción? Te devolveremos el dinero de inmediato y pasarás al plan Gratis.", en: "Cancel your subscription? You will be refunded immediately and downgraded to the Free plan.", hi: "क्या आप अपनी सदस्यता रद्द करना चाहते हैं? आपको तुरंत पैसा वापस मिल जाएगा।", zh: "取消订阅？您将立即获得退款并降级至免费计划。", ru: "Отменить подписку? Вам сразу вернут деньги и переведут на бесплатный план." },
  support: { es: "Soporte técnico", en: "Technical support", hi: "तकनीकी सहायता", zh: "技术支持", ru: "Техподдержка" },
  settings: { es: "Configuración", en: "Settings", hi: "सेटिंग्स", zh: "设置", ru: "Настройки" },
  settings_sub: { es: "Configuración (nombre, contraseña, emoji)", en: "Settings (name, password, emoji)", hi: "सेटिंग्स (नाम, पासवर्ड, इमोजी)", zh: "设置（姓名、密码、表情）", ru: "Настройки (имя, пароль, эмодзи)" },
  admin_panel: { es: "Panel Manager (RASC)", en: "Manager Panel (RASC)", hi: "मैनेजर पैनल (RASC)", zh: "管理面板 (RASC)", ru: "Панель менеджера (RASC)" },
  terms_privacy: { es: "Términos y Privacidad", en: "Terms and Privacy", hi: "नियम और गोपनीयता", zh: "条款和隐私", ru: "Условия и конфиденциальность" },
  logout: { es: "Cerrar sesión", en: "Log out", hi: "लॉग आउट", zh: "登出", ru: "Выйти" },
  language: { es: "Idioma", en: "Language", hi: "भाषा", zh: "语言", ru: "Язык" },
  choose_language: { es: "Elige tu idioma", en: "Choose your language", hi: "अपनी भाषा चुनें", zh: "选择您的语言", ru: "Выберите язык" },
  save: { es: "Guardar", en: "Save", hi: "सहेजें", zh: "保存", ru: "Сохранить" },
  save_profile: { es: "Guardar perfil", en: "Save profile", hi: "प्रोफ़ाइल सहेजें", zh: "保存资料", ru: "Сохранить профиль" },
  saved: { es: "Guardado", en: "Saved", hi: "सहेजा गया", zh: "已保存", ru: "Сохранено" },
  saved_profile: { es: "Perfil actualizado", en: "Profile updated", hi: "प्रोफ़ाइल अपडेट किया गया", zh: "资料已更新", ru: "Профиль обновлён" },
  guest_warning: { es: "Cuenta invitado · crea una cuenta para guardar tu progreso", en: "Guest account · create an account to save your progress", hi: "अतिथि खाता · प्रगति सहेजने के लिए खाता बनाएं", zh: "访客账户 · 创建账户以保存进度", ru: "Гостевой аккаунт · создайте аккаунт, чтобы сохранить прогресс" },
  messages_label: { es: "Mensajes", en: "Messages", hi: "संदेश", zh: "消息", ru: "Сообщения" },
  images_label: { es: "Imágenes", en: "Images", hi: "छवियाँ", zh: "图像", ru: "Изображения" },

  // Settings
  profile_section: { es: "Perfil", en: "Profile", hi: "प्रोफ़ाइल", zh: "个人资料", ru: "Профиль" },
  your_emoji: { es: "Tu emoji", en: "Your emoji", hi: "आपका इमोजी", zh: "你的表情", ru: "Ваш эмодзи" },
  change_password: { es: "Cambiar contraseña", en: "Change password", hi: "पासवर्ड बदलें", zh: "更改密码", ru: "Изменить пароль" },
  current_password: { es: "Contraseña actual", en: "Current password", hi: "वर्तमान पासवर्ड", zh: "当前密码", ru: "Текущий пароль" },
  new_password: { es: "Nueva contraseña (mínimo 6 caracteres)", en: "New password (min 6 chars)", hi: "नया पासवर्ड (कम से कम 6 अक्षर)", zh: "新密码（至少6个字符）", ru: "Новый пароль (мин. 6 символов)" },
  confirm_new_password: { es: "Confirmar nueva contraseña", en: "Confirm new password", hi: "नए पासवर्ड की पुष्टि करें", zh: "确认新密码", ru: "Подтвердите новый пароль" },
  pwd_mismatch: { es: "Las contraseñas nuevas no coinciden", en: "Passwords do not match", hi: "पासवर्ड मेल नहीं खाते", zh: "密码不匹配", ru: "Пароли не совпадают" },
  pwd_short: { es: "La contraseña debe tener al menos 6 caracteres", en: "Password must be at least 6 characters", hi: "पासवर्ड कम से कम 6 अक्षर का होना चाहिए", zh: "密码至少需要6个字符", ru: "Пароль должен содержать минимум 6 символов" },
  pwd_changed: { es: "Contraseña cambiada", en: "Password changed", hi: "पासवर्ड बदला गया", zh: "密码已更改", ru: "Пароль изменён" },

  // Common
  error: { es: "Error", en: "Error", hi: "त्रुटि", zh: "错误", ru: "Ошибка" },
  cancel: { es: "Cancelar", en: "Cancel", hi: "रद्द करें", zh: "取消", ru: "Отмена" },
  yes: { es: "Sí", en: "Yes", hi: "हाँ", zh: "是", ru: "Да" },
  no: { es: "No", en: "No", hi: "नहीं", zh: "否", ru: "Нет" },
  ok: { es: "OK", en: "OK", hi: "ठीक है", zh: "好", ru: "ОК" },
};

export type TKey = keyof typeof T;

type Ctx = { lang: Lang; setLang: (l: Lang) => Promise<void>; t: (key: TKey) => string };
const LangCtx = createContext<Ctx>({ lang: "es", setLang: async () => {}, t: (k) => String(k) });

function detectDeviceLang(): Lang {
  try {
    const locales = Localization.getLocales?.() || [];
    for (const loc of locales) {
      const code = (loc.languageCode || "").toLowerCase();
      if (["es", "en", "hi", "zh", "ru"].includes(code)) return code as Lang;
    }
  } catch {}
  return "es";
}

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("es");

  useEffect(() => {
    (async () => {
      const saved = await storage.getItem("rax_lang", "");
      if (saved && typeof saved === "string" && ["es", "en", "hi", "zh", "ru"].includes(saved)) {
        setLangState(saved as Lang);
      } else {
        setLangState(detectDeviceLang());
      }
    })();
  }, []);

  const setLang = useCallback(async (l: Lang) => {
    await storage.setItem("rax_lang", l);
    setLangState(l);
  }, []);

  const t = useCallback((key: TKey) => {
    const entry = T[key];
    if (!entry) return String(key);
    return (entry as any)[lang] || entry.es || String(key);
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}

export function useT() {
  return useContext(LangCtx);
}
