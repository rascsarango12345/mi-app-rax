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
  share: { es: "Compartir", en: "Share", hi: "साझा करें", zh: "分享", ru: "Поделиться" },
  copy: { es: "Copiar", en: "Copy", hi: "कॉपी", zh: "复制", ru: "Копировать" },
  copied: { es: "Copiado", en: "Copied", hi: "कॉपी हो गया", zh: "已复制", ru: "Скопировано" },
  loading: { es: "Cargando...", en: "Loading...", hi: "लोड हो रहा है...", zh: "加载中...", ru: "Загрузка..." },

  // Studio (Hub)
  tab_studio: { es: "Estudio", en: "Studio", hi: "स्टूडियो", zh: "工作室", ru: "Студия" },
  studio_title: { es: "Estudio Mágico RAX", en: "RAX Magic Studio", hi: "RAX मैजिक स्टूडियो", zh: "RAX 魔法工作室", ru: "RAX Магическая Студия" },
  studio_sub: { es: "Herramientas exclusivas con IA. Solo en RAX AI.", en: "Exclusive AI tools. Only on RAX AI.", hi: "विशेष AI टूल। केवल RAX AI पर।", zh: "独家 AI 工具。仅在 RAX AI 上。", ru: "Эксклюзивные AI-инструменты. Только в RAX AI." },

  // Cámara Mágica (AR Lens)
  lens_title: { es: "📸 Cámara Mágica", en: "📸 Magic Lens", hi: "📸 मैजिक लेंस", zh: "📸 魔法镜头", ru: "📸 Волшебная линза" },
  lens_sub: { es: "Apunta a cualquier cosa y descúbrelo todo", en: "Point at anything and discover everything", hi: "किसी भी चीज़ पर इंगित करें और सब कुछ जानें", zh: "对准任何物体，发现一切", ru: "Наведите на что угодно и узнайте всё" },
  lens_card_desc: { es: "Escanea objetos, plantas, comida, ropa, animales y descubre qué son al instante.", en: "Scan objects, plants, food, clothes, animals and discover what they are instantly.", hi: "वस्तुओं, पौधों, भोजन, कपड़ों को स्कैन करें", zh: "扫描物体、植物、食物、衣服并立即识别。", ru: "Сканируйте объекты, растения, еду, одежду." },
  lens_take_photo: { es: "Tomar foto", en: "Take photo", hi: "फोटो लें", zh: "拍照", ru: "Сделать фото" },
  lens_pick_gallery: { es: "Elegir de galería", en: "Pick from gallery", hi: "गैलरी से चुनें", zh: "从相册选择", ru: "Выбрать из галереи" },
  lens_analyzing: { es: "Analizando con magia IA...", en: "Analyzing with AI magic...", hi: "AI जादू से विश्लेषण कर रहा है...", zh: "AI 魔法分析中...", ru: "Анализ с AI магией..." },
  lens_scan_again: { es: "Escanear otro", en: "Scan another", hi: "दूसरा स्कैन करें", zh: "扫描另一个", ru: "Сканировать другое" },

  // Roast
  roast_title: { es: "🔥 Modo Roast", en: "🔥 Roast Mode", hi: "🔥 रोस्ट मोड", zh: "🔥 吐槽模式", ru: "🔥 Режим Жарки" },
  roast_sub: { es: "La IA más despiadada... ¡con humor!", en: "The most savage AI... with humor!", hi: "सबसे क्रूर AI... हास्य के साथ!", zh: "最狠的AI...带着幽默！", ru: "Самый беспощадный AI... с юмором!" },
  roast_card_desc: { es: "Sube tu foto o la de un amigo y deja que RAX te roastee con humor inteligente.", en: "Upload your photo or a friend's and let RAX roast you with smart humor.", hi: "अपनी या किसी मित्र की फ़ोटो अपलोड करें", zh: "上传你或朋友的照片让 RAX 吐槽你。", ru: "Загрузите фото и позвольте RAX весело подшутить." },
  roast_intensity: { es: "Intensidad", en: "Intensity", hi: "तीव्रता", zh: "强度", ru: "Интенсивность" },
  roast_soft: { es: "Suave", en: "Soft", hi: "हल्का", zh: "温和", ru: "Мягко" },
  roast_medium: { es: "Medio", en: "Medium", hi: "मध्यम", zh: "中等", ru: "Средне" },
  roast_brutal: { es: "Brutal", en: "Brutal", hi: "क्रूर", zh: "残酷", ru: "Жёстко" },
  roast_generate: { es: "Generar Roast 🔥", en: "Generate Roast 🔥", hi: "रोस्ट जनरेट करें 🔥", zh: "生成吐槽 🔥", ru: "Создать Жарку 🔥" },
  roast_generating: { es: "Preparando el roast...", en: "Preparing the roast...", hi: "रोस्ट तैयार कर रहा है...", zh: "准备吐槽中...", ru: "Готовим жарку..." },
  roast_again: { es: "Roastear otro", en: "Roast another", hi: "दूसरा रोस्ट करें", zh: "再吐槽一个", ru: "Жарить ещё" },

  // Journal
  journal_title: { es: "🌙 Diario Inteligente", en: "🌙 Smart Journal", hi: "🌙 स्मार्ट डायरी", zh: "🌙 智能日记", ru: "🌙 Умный дневник" },
  journal_sub: { es: "Tu mejor amigo IA que te recuerda y entiende", en: "Your AI best friend that remembers and understands you", hi: "आपका AI सबसे अच्छा दोस्त", zh: "记得并理解你的 AI 最佳朋友", ru: "Ваш лучший AI-друг, который помнит и понимает вас" },
  journal_card_desc: { es: "Escribe cómo te sientes. La IA recuerda todo y te da insights personalizados.", en: "Write how you feel. AI remembers everything and gives you personalized insights.", hi: "लिखें कि आप कैसा महसूस करते हैं", zh: "写下你的感受。AI 记得一切。", ru: "Напишите, что чувствуете. AI помнит всё." },
  journal_today_question: { es: "¿Cómo estás hoy?", en: "How are you today?", hi: "आज आप कैसे हैं?", zh: "你今天怎么样？", ru: "Как вы сегодня?" },
  journal_mood: { es: "Tu estado de ánimo", en: "Your mood", hi: "आपका मूड", zh: "你的心情", ru: "Ваше настроение" },
  journal_placeholder: { es: "Cuéntale a RAX cómo va tu día, qué te emociona, qué te preocupa...", en: "Tell RAX about your day, what excites you, what worries you...", hi: "RAX को अपने दिन के बारे में बताएं...", zh: "告诉 RAX 你的一天...", ru: "Расскажите RAX о своём дне..." },
  journal_save: { es: "Guardar entrada", en: "Save entry", hi: "एंट्री सेव करें", zh: "保存条目", ru: "Сохранить запись" },
  journal_history: { es: "Historial", en: "History", hi: "इतिहास", zh: "历史", ru: "История" },
  journal_insights: { es: "Insights de RAX", en: "RAX Insights", hi: "RAX अंतर्दृष्टि", zh: "RAX 洞察", ru: "Инсайты RAX" },
  journal_empty: { es: "Aún no tienes entradas. Empieza tu primer entrada de diario hoy ✨", en: "No entries yet. Start your first journal entry today ✨", hi: "अभी तक कोई एंट्री नहीं है ✨", zh: "还没有条目。今天开始你的第一篇 ✨", ru: "Записей пока нет. Начните сегодня ✨" },
  mood_happy: { es: "Feliz 😊", en: "Happy 😊", hi: "खुश 😊", zh: "开心 😊", ru: "Счастливый 😊" },
  mood_sad: { es: "Triste 😢", en: "Sad 😢", hi: "उदास 😢", zh: "难过 😢", ru: "Грустный 😢" },
  mood_anxious: { es: "Ansioso 😰", en: "Anxious 😰", hi: "चिंतित 😰", zh: "焦虑 😰", ru: "Тревожный 😰" },
  mood_neutral: { es: "Normal 😐", en: "Neutral 😐", hi: "सामान्य 😐", zh: "一般 😐", ru: "Обычный 😐" },
  mood_motivated: { es: "Motivado 💪", en: "Motivated 💪", hi: "प्रेरित 💪", zh: "充满动力 💪", ru: "Мотивирован 💪" },
  mood_angry: { es: "Enojado 😡", en: "Angry 😡", hi: "गुस्सा 😡", zh: "生气 😡", ru: "Злой 😡" },
  mood_grateful: { es: "Agradecido 🙏", en: "Grateful 🙏", hi: "आभारी 🙏", zh: "感恩 🙏", ru: "Благодарный 🙏" },

  // Shopper
  shopper_title: { es: "🛍️ Personal Shopper IA", en: "🛍️ AI Personal Shopper", hi: "🛍️ AI पर्सनल शॉपर", zh: "🛍️ AI 个人购物助手", ru: "🛍️ AI Личный шопер" },
  shopper_sub: { es: "Encuentra los mejores productos para ti", en: "Find the best products for you", hi: "अपने लिए सर्वोत्तम उत्पाद खोजें", zh: "为您找到最好的产品", ru: "Найдите лучшие продукты для вас" },
  shopper_card_desc: { es: "Describe qué buscas o sube una foto. La IA encuentra los mejores productos.", en: "Describe what you want or upload a photo. AI finds the best products.", hi: "बताएं कि आप क्या चाहते हैं या फोटो अपलोड करें।", zh: "描述您想要的或上传照片。", ru: "Опишите, что хотите, или загрузите фото." },
  shopper_query_placeholder: { es: "Ej: Audífonos inalámbricos con buena batería bajo $100", en: "E.g. Wireless headphones with good battery under $100", hi: "उदा: $100 के तहत वायरलेस हेडफ़ोन", zh: "例：100美元以下带电池良好的无线耳机", ru: "Напр: беспроводные наушники до $100" },
  shopper_budget: { es: "Presupuesto (USD)", en: "Budget (USD)", hi: "बजट (USD)", zh: "预算 (USD)", ru: "Бюджет (USD)" },
  shopper_search: { es: "Buscar productos 🔎", en: "Search products 🔎", hi: "उत्पाद खोजें 🔎", zh: "搜索产品 🔎", ru: "Найти продукты 🔎" },
  shopper_searching: { es: "Buscando los mejores productos...", en: "Finding the best products...", hi: "सर्वोत्तम उत्पाद ढूंढ रहा है...", zh: "正在寻找最佳产品...", ru: "Ищем лучшие продукты..." },
  shopper_search_again: { es: "Nueva búsqueda", en: "New search", hi: "नई खोज", zh: "新搜索", ru: "Новый поиск" },

  // Limits
  daily_limit_label: { es: "Hoy", en: "Today", hi: "आज", zh: "今天", ru: "Сегодня" },
  limit_reached: { es: "Has alcanzado el límite diario", en: "You've reached the daily limit", hi: "दैनिक सीमा पूरी हो गई", zh: "已达每日限额", ru: "Достигнут дневной лимит" },
  upgrade_for_more: { es: "Mejora tu plan para más", en: "Upgrade plan for more", hi: "अधिक के लिए प्लान अपग्रेड करें", zh: "升级以获得更多", ru: "Улучшите план для большего" },
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
