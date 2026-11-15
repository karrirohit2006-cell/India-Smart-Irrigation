/**
 * AgriSaathi - AI Agricultural Assistant Frontend Interface
 * Complete Multilingual Support for English, Hindi, Punjabi, and Telugu.
 * Supports auto-detection, manual selection, persistence, and mixed-language conversations.
 */

(function () {
    "use strict";

    // Storage keys for language preference and persistent conversation history
    const STORAGE_LANG_KEY = "agri_saathi_lang_pref";
    const STORAGE_HISTORY_KEY = "agri_saathi_chat_history_v1";
    const STORAGE_ACTIVE_ID_KEY = "agri_saathi_active_conv_id";

    // Comprehensive Multilingual Dictionary
    const chatTranslations = {
        auto: {
            title: "AgriSaathi",
            subtitle: "Multilingual AI Agricultural Assistant",
            welcome: "Hello! I am <strong>AgriSaathi</strong> (एग्री साथी / ਐਗਰੀ ਸਾਥੀ / అగ్రి సాథి). Ask me any farming question in English, हिन्दी, ਪੰਜਾਬੀ, or తెలుగు!",
            suggestionsTitle: "Suggested questions / सुझाए गए प्रश्न / ਸੁਝਾਏ ਸਵਾਲ / సూచించిన ప్రశ్నలు:",
            questions: [
                "💧 How can I save irrigation water?",
                "🪴 मिट्टी की नमी (Soil Moisture) की जांच कैसे करें?",
                "🌾 ਝੋਨੇ ਵਿੱਚ ਪਾਣੀ ਦੀ ਬੱਚਤ ਕਿਵੇਂ ਕਰੀਏ?",
                "🌱 వరి పంటలో నీటి యాజమాన్యం ఎలా చేయాలి?"
            ],
            placeholder: "Ask in English, हिन्दी, ਪੰਜਾਬੀ, or తెలుగు...",
            typing: "AgriSaathi is thinking...",
            networkError: "Unable to reach AgriSaathi right now. Please check your connection and try again.",
            openAria: "Open AgriSaathi Multilingual Agricultural Chatbot",
            closeAria: "Close AgriSaathi Chat",
            clearAria: "Clear chat session / चैट साफ़ करें",
            historyBtn: "Chat History / बातचीत इतिहास",
            newChatBtn: "New Chat / नई बातचीत",
            historyTitle: "Conversation History / बातचीत इतिहास",
            noHistory: "No previous conversations yet. Start chatting to save your history!",
            clearAllHistory: "Clear All History / पूरा इतिहास साफ़ करें",
            clearAllConfirm: "Are you sure you want to delete all saved conversations? This cannot be undone.",
            clearConvBtn: "Clear conversation / बातचीत साफ़ करें",
            clearConvConfirm: "Clear all messages in the current conversation? / क्या आप वर्तमान बातचीत साफ़ करना चाहते हैं?",
            deleteChat: "Delete conversation",
            backToChat: "Back to Chat",
            today: "Today",
            yesterday: "Yesterday",
            messagesCount: "msgs"
        },
        en: {
            title: "AgriSaathi",
            subtitle: "AI Agricultural Assistant",
            welcome: "Hello! I am <strong>AgriSaathi</strong>, your AI farming companion. How can I assist you with your irrigation schedules, soil moisture, and crop health today?",
            suggestionsTitle: "Suggested questions:",
            questions: [
                "💧 How can I save irrigation water?",
                "🪴 Why is soil moisture critical for crops?",
                "🌾 What are the best irrigation practices for paddy?",
                "📊 Help me understand my irrigation prediction result."
            ],
            placeholder: "Ask AgriSaathi about crops or irrigation...",
            typing: "AgriSaathi is thinking...",
            networkError: "Unable to reach AgriSaathi right now. Please check your connection and try again.",
            openAria: "Open AgriSaathi AI Agricultural Chatbot",
            closeAria: "Close AgriSaathi Chat",
            clearAria: "Clear chat session",
            historyBtn: "Chat History",
            newChatBtn: "New Chat",
            historyTitle: "Conversation History",
            noHistory: "No previous conversations yet. Start chatting to save your history!",
            clearAllHistory: "Clear All History",
            clearAllConfirm: "Are you sure you want to delete all saved conversations? This cannot be undone.",
            clearConvBtn: "Clear conversation",
            clearConvConfirm: "Clear all messages in the current conversation?",
            deleteChat: "Delete conversation",
            backToChat: "Back to Chat",
            today: "Today",
            yesterday: "Yesterday",
            messagesCount: "msgs"
        },
        hi: {
            title: "एग्री साथी (AgriSaathi)",
            subtitle: "एआई कृषि सलाहकार",
            welcome: "नमस्ते किसान भाई! मैं हूँ <strong>एग्री साथी (AgriSaathi)</strong>, आपका डिजिटल कृषि सलाहकार। आज मैं सिंचाई, मिट्टी की नमी, या फसल स्वास्थ्य संबंधी किस कार्य में आपकी मदद कर सकता हूँ?",
            suggestionsTitle: "सुझाए गए प्रश्न:",
            questions: [
                "💧 धान में पानी की बचत कैसे करें?",
                "🪴 मिट्टी की नमी (Soil Moisture) क्यों महत्वपूर्ण है?",
                "🌾 धान की फसल में सिंचाई का सही समय क्या है?",
                "📊 मेरे सिंचाई परिणाम को समझने में सहायता करें।"
            ],
            placeholder: "फसल, सिंचाई या मिट्टी के बारे में पूछें...",
            typing: "एग्री साथी सोच रहा है...",
            networkError: "इस समय एग्री साथी से संपर्क नहीं हो पा रहा है। कृपया कुछ देर बाद प्रयास करें।",
            openAria: "एग्री साथी चैटबॉट खोलें",
            closeAria: "एग्री साथी चैट बंद करें",
            clearAria: "चैट सत्र साफ़ करें",
            historyBtn: "बातचीत इतिहास",
            newChatBtn: "नई चैट शुरू करें",
            historyTitle: "बातचीत इतिहास",
            noHistory: "अभी कोई पिछली बातचीत नहीं है। सहेजने के लिए बातचीत शुरू करें!",
            clearAllHistory: "पूरा इतिहास साफ़ करें",
            clearAllConfirm: "क्या आप वाकई सभी सहेजी गई बातचीत हटाना चाहते हैं? यह वापस नहीं लाया जा सकता।",
            clearConvBtn: "बातचीत साफ़ करें",
            clearConvConfirm: "क्या आप वर्तमान बातचीत के सभी संदेश साफ़ करना चाहते हैं?",
            deleteChat: "बातचीत हटाएं",
            backToChat: "चैट पर वापस जाएं",
            today: "आज",
            yesterday: "कल",
            messagesCount: "संदेश"
        },
        pa: {
            title: "ਐਗਰੀ ਸਾਥੀ (AgriSaathi)",
            subtitle: "ਏਆਈ ਖੇਤੀਬਾੜੀ ਸਹਾਇਕ",
            welcome: "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਕਿਸਾਨ ਵੀਰੋ! ਮੈਂ ਹਾਂ <strong>ਐਗਰੀ ਸਾਥੀ (AgriSaathi)</strong>, ਤੁਹਾਡਾ ਸਮਾਰਟ ਖੇਤੀਬਾੜੀ ਸਹਾਇਕ। ਸਿੰਚਾਈ, ਮਿੱਟੀ ਦੀ ਸਿਹਤ ਜਾਂ ਫ਼ਸਲਾਂ ਸੰਬੰਧੀ ਮੈਂ ਤੁਹਾਡੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
            suggestionsTitle: "ਸੁਝਾਏ ਗਏ ਸਵਾਲ:",
            questions: [
                "💧 ਝੋਨੇ ਵਿੱਚ ਸਿੰਚਾਈ ਪਾਣੀ ਦੀ ਬੱਚਤ ਕਿਵੇਂ ਕਰੀਏ?",
                "🪴 ਮਿੱਟੀ ਦੀ ਨਮੀ (Soil Moisture) ਫ਼ਸਲ ਲਈ ਕਿਉਂ ਜ਼ਰੂਰੀ ਹੈ?",
                "🌾 ਝੋਨੇ ਨੂੰ ਪਾਣੀ ਕਦੋਂ ਅਤੇ ਕਿੰਨਾ ਦੇਣਾ ਚਾਹੀਦਾ ਹੈ?",
                "📊 ਮੇਰੇ ਸਿੰਚਾਈ ਨਤੀਜੇ ਨੂੰ ਸਮਝਣ ਵਿੱਚ ਮਦਦ ਕਰੋ।"
            ],
            placeholder: "ਫ਼ਸਲ ਜਾਂ ਸਿੰਚਾਈ ਬਾਰੇ ਪੁੱਛੋ...",
            typing: "ਐਗਰੀ ਸਾਥੀ ਸੋਚ ਰਿਹਾ ਹੈ...",
            networkError: "ਇਸ ਵੇਲੇ ਐਗਰੀ ਸਾਥੀ ਨਾਲ ਸੰਪਰਕ ਨਹੀਂ ਹੋ ਰਿਹਾ। ਕਿਰਪਾ ਕਰਕੇ ਥੋੜ੍ਹੀ ਦੇਰ ਬਾਅਦ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
            openAria: "ਐਗਰੀ ਸਾਥੀ ਚੈਟ ਖੋਲ੍ਹੋ",
            closeAria: "ਐਗਰੀ ਸਾਥੀ ਚੈਟ ਬੰਦ ਕਰੋ",
            clearAria: "ਚੈਟ ਸੈਸ਼ਨ ਸਾਫ਼ ਕਰੋ",
            historyBtn: "ਗੱਲਬਾਤ ਇਤਿਹਾਸ",
            newChatBtn: "ਨਵੀਂ ਚੈਟ ਸ਼ੁਰੂ ਕਰੋ",
            historyTitle: "ਗੱਲਬਾਤ ਇਤਿਹਾਸ",
            noHistory: "ਅਜੇ ਕੋਈ ਪਿਛਲੀ ਚੈਟ ਨਹੀਂ ਹੈ। ਗੱਲਬਾਤ ਸ਼ੁਰੂ ਕਰਕੇ ਇਤਿਹਾਸ ਬਣਾਓ!",
            clearAllHistory: "ਸਾਰਾ ਇਤਿਹਾਸ ਸਾਫ਼ ਕਰੋ",
            clearAllConfirm: "ਕੀ ਤੁਸੀਂ ਸੱਚਮੁੱਚ ਸਾਰੀ ਸੁਰੱਖਿਅਤ ਕੀਤੀ ਚੈਟ ਹਟਾਉਣਾ ਚਾਹੁੰਦੇ ਹੋ? ਇਹ ਵਾਪਸ ਨਹੀਂ ਲਿਆਂਦਾ ਜਾ ਸਕਦਾ।",
            clearConvBtn: "ਗੱਲਬਾਤ ਸਾਫ਼ ਕਰੋ",
            clearConvConfirm: "ਕੀ ਤੁਸੀਂ ਮੌਜੂਦਾ ਗੱਲਬਾਤ ਦੇ ਸਾਰੇ ਸੁਨੇਹੇ ਸਾਫ਼ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
            deleteChat: "ਚੈਟ ਹਟਾਓ",
            backToChat: "ਚੈਟ 'ਤੇ ਵਾਪਸ ਜਾਓ",
            today: "ਅੱਜ",
            yesterday: "ਕੱਲ੍ਹ",
            messagesCount: "ਸੁਨੇਹੇ"
        },
        te: {
            title: "అగ్రి సాథి (AgriSaathi)",
            subtitle: "AI వ్యవసాయ సహాయకుడు",
            welcome: "నమస్కారం రైతు సోదరులారా! నేను <strong>అగ్రి సాథి (AgriSaathi)</strong>, మీ స్మార్ట్ వ్యవసాయ సలహాదారుని. సాగునీటి నిర్వహణ, నేల తేమ లేదా పంటల రక్షణ గురించి మీకు ఎలా సహాయపడగలను?",
            suggestionsTitle: "సూచించబడిన ప్రశ్నలు:",
            questions: [
                "💧 వరి పంటలో సాగునీటిని ఎలా ఆదా చేయవచ్చు?",
                "🪴 నేలలో తేమ శాతం (Soil Moisture) ఎందుకు ముఖ్యం?",
                "🌾 వరి లేదా వేరుశనగకు నీరు ఎప్పుడు పెట్టాలి?",
                "📊 నా నీటి పారుదల ఫలితాన్ని అర్థం చేసుకోవడానికి సహాయం చేయండి."
            ],
            placeholder: "పంటలు లేదా నీటి పారుదల గురించి అడగండి...",
            typing: "అగ్రి సాథి ఆలోచిస్తోంది...",
            networkError: "ప్రస్తుతం అగ్రి సాథిని సంప్రదించలేకపోతున్నాము. దయచేసి కాసేపటి తర్వాత ప్రయత్నించండి.",
            openAria: "అగ్రి సాథి చాట్ తెరవండి",
            closeAria: "అగ్రి సాథి చాట్ మూసివేయండి",
            clearAria: "చాట్ సెషన్‌ను క్లియర్ చేయండి",
            historyBtn: "చాట్ చరిత్ర",
            newChatBtn: "కొత్త చాట్ ప్రారంభించండి",
            historyTitle: "సంభాషణల చరిత్ర",
            noHistory: "ఇంకా మునుపటి సంభాషణలు లేవు. చరిత్రను సేవ్ చేయడానికి చాట్ ప్రారంభించండి!",
            clearAllHistory: "మొత్తం చరిత్రను క్లియర్ చేయండి",
            clearAllConfirm: "మీరు నిజంగా భద్రపరిచిన అన్ని సంభాషణలను తొలగించాలనుకుంటున్నారా? దీన్ని రద్దు చేయలేము.",
            clearConvBtn: "సంభాషణను క్లియర్ చేయండి",
            clearConvConfirm: "ప్రస్తుత సంభాషణలోని అన్ని సందేశాలను క్లియర్ చేయాలా?",
            deleteChat: "సంభాషణను తొలగించండి",
            backToChat: "చాట్‌కి తిరిగి వెళ్లండి",
            today: "ఈ రోజు",
            yesterday: "నిన్న",
            messagesCount: "సందేశాలు"
        }
    };

    // Session History & Context Configuration
    const MAX_SESSION_HISTORY = 10;
    let sessionMessages = [];
    let sessionSensors = {};
    let activeConversationId = null;
    let historyPanelOpen = false;

    // DOM Elements Cache
    let toggleBtn;
    let chatWindow;
    let closeBtn;
    let newChatBtn;
    let historyBtn;
    let clearConvBtn;
    let historyPanel;
    let historyList;
    let historyCloseBtn;
    let newChatFromHistoryBtn;
    let clearAllHistoryBtn;
    let historyTitleEl;
    let newChatBtnTextEl;
    let clearAllBtnTextEl;
    let clearBtn;
    let messagesContainer;
    let chatForm;
    let chatInput;
    let sendBtn;
    let langSelect;
    let typingIndicator;
    let suggestionsContainer;
    let welcomeTextEl;

    let currentLanguage = "auto";
    let isTyping = false;
    let userHasSentMessages = false;

    function formatTime(date) {
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // Convert Markdown (bold, italic, bullet lists) into clean, safe Unicode HTML
    function formatMarkdown(rawText) {
        if (!rawText) return "";

        let safe = rawText
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

        safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        safe = safe.replace(/(^|[^*])\*(?!\*)([^*]+)\*(?!\*)/g, "$1<em>$2</em>");

        const lines = safe.split("\n");
        let inList = false;
        const formattedLines = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith("* ") || line.startsWith("- ")) {
                if (!inList) {
                    formattedLines.push("<ul class='agri-chat-list'>");
                    inList = true;
                }
                formattedLines.push(`<li>${line.substring(2)}</li>`);
            } else {
                if (inList) {
                    formattedLines.push("</ul>");
                    inList = false;
                }
                if (line.length > 0) {
                    formattedLines.push(`<p>${line}</p>`);
                }
            }
        }
        if (inList) {
            formattedLines.push("</ul>");
        }

        return formattedLines.length > 0 ? formattedLines.join("") : safe.replace(/\n/g, "<br>");
    }

    function getCombinedContext() {
        const getVal = id => {
            const el = document.getElementById(id);
            return el && el.value !== "" ? el.value : null;
        };

        const cropType = getVal("crop_type");
        const cropDays = getVal("crop_days");
        const moisture = getVal("soil_moisture");
        const soilTemp = getVal("soil_temperature");
        const airTemp = getVal("temperature");
        const humidity = getVal("humidity");

        // Merge live dashboard values into session sensor memory
        if (cropType !== null) {
            if (!isNaN(Number(cropType))) {
                sessionSensors.crop_type = Number(cropType);
                delete sessionSensors.crop_name;
            } else {
                sessionSensors.crop_name = String(cropType);
                delete sessionSensors.crop_type;
            }
        }
        if (cropDays !== null && !isNaN(Number(cropDays))) sessionSensors.crop_days = Number(cropDays);
        if (moisture !== null && !isNaN(Number(moisture))) sessionSensors.soil_moisture = Number(moisture);
        if (soilTemp !== null && !isNaN(Number(soilTemp))) sessionSensors.soil_temperature = Number(soilTemp);
        if (airTemp !== null && !isNaN(Number(airTemp))) sessionSensors.temperature = Number(airTemp);
        if (humidity !== null && !isNaN(Number(humidity))) sessionSensors.humidity = Number(humidity);

        // Security: strictly forward only valid raw sensor fields (never client-supplied prediction results)
        const safe = {};
        ["crop_days", "soil_moisture", "soil_temperature", "temperature", "humidity"].forEach(field => {
            if (sessionSensors[field] !== undefined && sessionSensors[field] !== null && !isNaN(sessionSensors[field])) {
                safe[field] = sessionSensors[field];
            }
        });
        if (sessionSensors.crop_type !== undefined) safe.crop_type = sessionSensors.crop_type;
        if (sessionSensors.crop_name !== undefined) safe.crop_name = sessionSensors.crop_name;

        return Object.keys(safe).length > 0 ? safe : null;
    }

    // -------------------------------------------------------------------------
    // Persistent Conversation History Management (localStorage)
    // -------------------------------------------------------------------------

    function loadAllHistory() {
        try {
            const raw = localStorage.getItem(STORAGE_HISTORY_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                return parsed.sort((a, b) => (b.updatedAt || b.createdAt || 0) - (a.updatedAt || a.createdAt || 0));
            }
            return [];
        } catch (e) {
            console.warn("AgriSaathi: Unable to read history from localStorage", e);
            return [];
        }
    }

    function saveAllHistory(historyList) {
        try {
            localStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(historyList));
        } catch (e) {
            console.warn("AgriSaathi: Unable to save history to localStorage", e);
        }
    }

    function getActiveConversationId() {
        try {
            return localStorage.getItem(STORAGE_ACTIVE_ID_KEY) || null;
        } catch (e) {
            return null;
        }
    }

    function setActiveConversationId(id) {
        activeConversationId = id;
        try {
            if (id) {
                localStorage.setItem(STORAGE_ACTIVE_ID_KEY, id);
            } else {
                localStorage.removeItem(STORAGE_ACTIVE_ID_KEY);
            }
        } catch (e) {
            // ignore private browsing exceptions
        }
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatConversationDate(timestamp) {
        if (!timestamp) return "";
        const date = new Date(timestamp);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();

        const yesterday = new Date();
        yesterday.setDate(now.getDate() - 1);
        const isYesterday = date.toDateString() === yesterday.toDateString();

        const timeStr = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;

        if (isToday) {
            return `${dict.today || "Today"}, ${timeStr}`;
        } else if (isYesterday) {
            return `${dict.yesterday || "Yesterday"}, ${timeStr}`;
        } else {
            const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            return `${monthNames[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()} ${timeStr}`;
        }
    }

    function renderHistoryList() {
        if (!historyList) return;
        historyList.innerHTML = "";

        const history = loadAllHistory();
        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;

        if (history.length === 0) {
            const emptyDiv = document.createElement("div");
            emptyDiv.className = "agri-history-empty";
            emptyDiv.innerHTML = `
                <span class="agri-history-empty-icon" aria-hidden="true">🌱</span>
                <p>${dict.noHistory}</p>
            `;
            historyList.appendChild(emptyDiv);
            if (clearAllHistoryBtn) {
                clearAllHistoryBtn.style.display = "none";
            }
            return;
        }

        if (clearAllHistoryBtn) {
            clearAllHistoryBtn.style.display = "flex";
        }

        history.forEach(conv => {
            const item = document.createElement("div");
            item.className = "agri-history-item" + (conv.id === activeConversationId ? " agri-history-item-active" : "");
            item.setAttribute("role", "button");
            item.setAttribute("tabindex", "0");
            item.setAttribute("data-id", conv.id);

            const msgCount = Array.isArray(conv.messages) ? conv.messages.length : 0;
            const dateStr = formatConversationDate(conv.updatedAt || conv.createdAt);

            item.innerHTML = `
                <div class="agri-history-item-content">
                    <h5 class="agri-history-item-title" title="${escapeHtml(conv.title || 'Untitled Conversation')}">
                        ${escapeHtml(conv.title || 'Untitled Conversation')}
                    </h5>
                    <div class="agri-history-item-meta">
                        <span class="agri-history-date">${dateStr}</span>
                        <span class="agri-history-msg-count">${msgCount} ${dict.messagesCount || 'msgs'}</span>
                    </div>
                </div>
                <button type="button" class="agri-history-item-delete" aria-label="${dict.deleteChat || 'Delete conversation'}" title="${dict.deleteChat || 'Delete conversation'}">
                    <span aria-hidden="true">🗑️</span>
                </button>
            `;

            // Click to reload old conversation
            item.addEventListener("click", (e) => {
                if (e.target.closest(".agri-history-item-delete")) return;
                loadConversation(conv.id);
            });

            // Keyboard accessibility
            item.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    if (!e.target.closest(".agri-history-item-delete")) {
                        e.preventDefault();
                        loadConversation(conv.id);
                    }
                }
            });

            // Delete individual conversation
            const delBtn = item.querySelector(".agri-history-item-delete");
            if (delBtn) {
                delBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteConversation(conv.id);
                });
            }

            historyList.appendChild(item);
        });
    }

    function openHistoryPanel() {
        if (!historyPanel) return;
        historyPanel.hidden = false;
        historyPanel.classList.add("agri-history-open");
        historyPanel.style.display = "flex";
        historyPanelOpen = true;
        if (historyBtn) {
            historyBtn.classList.add("agri-btn-active");
            historyBtn.setAttribute("aria-expanded", "true");
        }
        renderHistoryList();
    }

    function closeHistoryPanel() {
        if (!historyPanel) return;
        historyPanel.hidden = true;
        historyPanel.classList.remove("agri-history-open");
        historyPanel.style.display = "none";
        historyPanelOpen = false;
        if (historyBtn) {
            historyBtn.classList.remove("agri-btn-active");
            historyBtn.setAttribute("aria-expanded", "false");
        }
    }

    function toggleHistoryPanel() {
        if (historyPanelOpen) {
            closeHistoryPanel();
        } else {
            openHistoryPanel();
        }
    }

    function loadConversation(convId) {
        const history = loadAllHistory();
        const conv = history.find(c => c.id === convId);
        if (!conv) return;

        setActiveConversationId(conv.id);
        userHasSentMessages = true;

        // Restore context memory for multi-turn follow-up questions
        sessionMessages = (conv.messages || []).map(m => ({
            role: m.role,
            content: m.content
        }));

        if (messagesContainer) {
            messagesContainer.innerHTML = "";

            if (conv.messages && conv.messages.length > 0) {
                conv.messages.forEach(msg => {
                    const isUser = msg.role === "user";
                    const formatted = !isUser && !msg.isError ? formatMarkdown(msg.content) : msg.content;
                    appendMessage(formatted, isUser ? "user" : "assistant", !isUser && !msg.isError, !!msg.isError, msg.timeStr);
                });
            } else {
                renderDefaultWelcome();
            }
        }

        closeHistoryPanel();
        scrollToBottom();

        if (chatInput) {
            chatInput.focus();
        }
    }

    function startNewChat() {
        setActiveConversationId(null);
        sessionMessages = [];
        sessionSensors = {};
        userHasSentMessages = false;

        renderDefaultWelcome();
        closeHistoryPanel();

        if (chatInput) {
            chatInput.value = "";
            chatInput.focus();
        }
    }

    function deleteConversation(convId) {
        let history = loadAllHistory();
        history = history.filter(c => c.id !== convId);
        saveAllHistory(history);

        if (activeConversationId === convId) {
            startNewChat();
        } else {
            renderHistoryList();
        }
    }

    function clearActiveConversation() {
        if (!messagesContainer) return;
        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;
        const confirmed = window.confirm(dict.clearConvConfirm || "Clear all messages in the current conversation?");
        if (!confirmed) return;

        sessionMessages = [];
        sessionSensors = {};
        userHasSentMessages = false;

        if (activeConversationId) {
            let history = loadAllHistory();
            const conv = history.find(c => c.id === activeConversationId);
            if (conv) {
                conv.messages = [];
                conv.updatedAt = Date.now();
                saveAllHistory(history);
            }
        }

        renderDefaultWelcome();
        if (chatInput) {
            chatInput.value = "";
            chatInput.focus();
        }
    }

    function clearAllHistory() {
        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;
        const confirmed = window.confirm(dict.clearAllConfirm || "Are you sure you want to delete all saved conversations? This cannot be undone.");
        if (!confirmed) return;

        try {
            localStorage.removeItem(STORAGE_HISTORY_KEY);
            localStorage.removeItem(STORAGE_ACTIVE_ID_KEY);
        } catch (e) {
            // ignore
        }

        startNewChat();
        renderHistoryList();
    }

    function renderDefaultWelcome() {
        if (!messagesContainer) return;
        messagesContainer.innerHTML = "";

        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;

        // Welcome Message Bubble
        const welcomeRow = document.createElement("div");
        welcomeRow.className = "agri-msg-row agri-msg-assistant";
        welcomeRow.innerHTML = `
            <div class="agri-msg-avatar" aria-hidden="true">🌱</div>
            <div class="agri-msg-bubble">
                <div class="agri-msg-text" id="agriWelcomeText">${dict.welcome}</div>
                <span class="agri-msg-time">Just now</span>
            </div>
        `;
        messagesContainer.appendChild(welcomeRow);

        // Suggested Questions Section
        const suggSection = document.createElement("div");
        suggSection.className = "agri-suggestions";
        suggSection.id = "agriSuggestions";

        let chipsHtml = "";
        dict.questions.forEach((q) => {
            const cleanQ = q.replace(/^[^\w\s\u0900-\u0D7F]+\s*/, "");
            chipsHtml += `<button type="button" class="agri-chip" data-question="${cleanQ}">${q}</button>`;
        });

        suggSection.innerHTML = `
            <p class="agri-suggestions-title" id="agriSuggestionsTitle">${dict.suggestionsTitle}</p>
            <div class="agri-chips">${chipsHtml}</div>
        `;
        messagesContainer.appendChild(suggSection);

        welcomeTextEl = document.getElementById("agriWelcomeText");
        suggestionsContainer = suggSection;
    }

    function setChatLanguage(lang, persist = true) {
        if (!chatTranslations[lang]) lang = "auto";
        currentLanguage = lang;

        if (persist) {
            try {
                localStorage.setItem(STORAGE_LANG_KEY, lang);
            } catch (e) {
                // Ignore storage failure in private mode
            }
        }

        const dict = chatTranslations[lang];

        const titleEl = document.getElementById("agriChatHeaderTitle");
        const subEl = document.getElementById("agriChatSubtitle");
        const suggestionsTitleEl = document.getElementById("agriSuggestionsTitle");
        const typingLabelEl = document.getElementById("agriTypingLabel");

        if (titleEl) titleEl.textContent = dict.title;
        if (subEl) subEl.innerHTML = `<span class="agri-online-dot"></span> ${dict.subtitle}`;
        if (chatInput) chatInput.placeholder = dict.placeholder;
        if (suggestionsTitleEl) suggestionsTitleEl.textContent = dict.suggestionsTitle;
        if (typingLabelEl) typingLabelEl.textContent = dict.typing;

        // If user hasn't started chatting yet, update the welcome bubble to match the selected language
        if (!userHasSentMessages && welcomeTextEl) {
            welcomeTextEl.innerHTML = dict.welcome;
        }

        // Update suggested question chips
        const chipButtons = document.querySelectorAll(".agri-chip");
        chipButtons.forEach((btn, index) => {
            if (dict.questions[index]) {
                btn.textContent = dict.questions[index];
                btn.setAttribute("data-question", dict.questions[index].replace(/^[^\w\s\u0900-\u0D7F]+\s*/, ""));
            }
        });

        if (toggleBtn) {
            const isOpen = chatWindow && !chatWindow.hidden;
            toggleBtn.setAttribute("aria-label", isOpen ? dict.closeAria : dict.openAria);
        }
        if (closeBtn) {
            closeBtn.setAttribute("aria-label", dict.closeAria);
        }
        if (newChatBtn) {
            newChatBtn.setAttribute("aria-label", dict.newChatBtn);
            newChatBtn.setAttribute("title", dict.newChatBtn);
        }
        if (historyBtn) {
            historyBtn.setAttribute("aria-label", dict.historyBtn);
            historyBtn.setAttribute("title", dict.historyBtn);
        }
        if (clearConvBtn) {
            clearConvBtn.setAttribute("aria-label", dict.clearConvBtn);
            clearConvBtn.setAttribute("title", dict.clearConvBtn);
        }
        if (historyTitleEl) historyTitleEl.textContent = dict.historyTitle;
        if (newChatBtnTextEl) newChatBtnTextEl.textContent = dict.newChatBtn;
        if (clearAllBtnTextEl) clearAllBtnTextEl.textContent = dict.clearAllHistory;
        if (historyCloseBtn) {
            historyCloseBtn.setAttribute("aria-label", dict.backToChat);
            historyCloseBtn.setAttribute("title", dict.backToChat);
        }
        if (clearAllHistoryBtn) {
            clearAllHistoryBtn.setAttribute("aria-label", dict.clearAllHistory);
            clearAllHistoryBtn.setAttribute("title", dict.clearAllHistory);
        }

        if (langSelect && langSelect.value !== lang) {
            langSelect.value = lang;
        }

        if (historyPanelOpen) {
            renderHistoryList();
        }
    }

    function clearChat() {
        startNewChat();
    }

    function openChat() {
        if (!chatWindow) return;
        chatWindow.hidden = false;
        chatWindow.classList.add("agri-open");
        toggleBtn.classList.add("agri-active");
        toggleBtn.setAttribute("aria-expanded", "true");

        // Ensure history panel is closed so message area and input form are visible
        closeHistoryPanel();

        setTimeout(() => {
            if (chatInput && !isTyping) chatInput.focus();
        }, 150);

        scrollToBottom();
    }

    function closeChat() {
        if (!chatWindow) return;
        chatWindow.classList.remove("agri-open");
        toggleBtn.classList.remove("agri-active");
        toggleBtn.setAttribute("aria-expanded", "false");

        setTimeout(() => {
            chatWindow.hidden = true;
        }, 220);

        if (toggleBtn) toggleBtn.focus();
    }

    function toggleChat() {
        const isOpen = chatWindow && !chatWindow.hidden;
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    }

    // Helper: Detect language script
    function detectLanguageScript(text) {
        if (!text) return "en";
        let te = 0, pa = 0, hi = 0;
        for (let i = 0; i < text.length; i++) {
            const code = text.charCodeAt(i);
            if (code >= 0x0c00 && code <= 0x0c7f) te++;
            else if (code >= 0x0a00 && code <= 0x0a7f) pa++;
            else if (code >= 0x0900 && code <= 0x097f) hi++;
        }
        if (te > pa && te > hi) return "te";
        if (pa > te && pa > hi) return "pa";
        if (hi > te && hi > pa) return "hi";
        return "en";
    }

    // ----------------------------------------------------
    // Phase 4: Text-to-Speech (TTS) Engine
    // ----------------------------------------------------
    let currentSpeakingBtn = null;

    function stopAllSpeech() {
        if ('speechSynthesis' in window) {
            try {
                window.speechSynthesis.cancel();
            } catch (e) {}
        }
        if (currentSpeakingBtn) {
            currentSpeakingBtn.innerHTML = `<span aria-hidden="true">🔊</span> <span>Listen</span>`;
            currentSpeakingBtn.classList.remove("speaking");
            currentSpeakingBtn.title = "Read aloud";
            currentSpeakingBtn = null;
        }
    }

    function toggleSpeakMessage(rawText, btn) {
        // Strip HTML, markdown asterisks, emojis for natural reading
        const cleanText = rawText.replace(/<[^>]*>?/gm, "")
                                 .replace(/[*_#`~>]/g, "")
                                 .replace(/[\u{1F300}-\u{1F9FF}]/gu, "")
                                 .trim();

        if (!cleanText) return;

        // If clicking on already active button, toggle stop
        if (currentSpeakingBtn === btn) {
            stopAllSpeech();
            return;
        }

        stopAllSpeech();

        const detected = detectLanguageScript(cleanText);

        currentSpeakingBtn = btn;
        btn.innerHTML = `<span aria-hidden="true">⏹️</span> <span>Stop</span>`;
        btn.classList.add("speaking");
        btn.title = "Stop reading aloud";

        if (window.AgriVoiceAudio) {
            window.AgriVoiceAudio.play(cleanText, detected, () => {
                stopAllSpeech();
            });
            return;
        }

        if (!('speechSynthesis' in window)) {
            stopAllSpeech();
            return;
        }

        const utter = new SpeechSynthesisUtterance(cleanText);
        if (detected === "te") {
            utter.lang = "te-IN";
        } else if (detected === "hi") {
            utter.lang = "hi-IN";
        } else if (detected === "pa") {
            utter.lang = "pa-IN";
        } else {
            utter.lang = "en-IN";
        }

        utter.rate = 1.0;
        utter.pitch = 1.0;

        utter.onend = () => stopAllSpeech();
        utter.onerror = () => stopAllSpeech();

        window.speechSynthesis.speak(utter);
    }

    // ----------------------------------------------------
    // Phase 4: Dynamic Follow-Up Suggestions
    // ----------------------------------------------------
    function generateFollowUpSuggestions(userPrompt, replyText, lang) {
        const p = (userPrompt || "").toLowerCase();
        const r = (replyText || "").toLowerCase();

        const detected = detectLanguageScript(userPrompt + " " + replyText);
        const activeLang = lang === "auto" ? detected : lang;

        if (activeLang === "te") {
            if (p.includes("వరి") || p.includes("rice") || r.includes("వరి")) {
                return [
                    "💧 వరిలో ఆల్టర్నేట్ వెట్టింగ్ అండ్ డ్రైయింగ్ (AWD) అంటే ఏమిటి?",
                    "📏 పొలంలో నీటి మట్టాన్ని ఎలా కొలవాలి?",
                    "🌾 వరి పంటకు కీలకమైన నీటి దశలు ఏవి?",
                    "🌧️ వర్షం పడినప్పుడు నీటిపారుదల ఎలా మార్చాలి?"
                ];
            }
            if (p.includes("పనిచేస్తుంది") || p.includes("prediction") || r.includes("ప్రిడిక్షన్")) {
                return [
                    "🌧️ 10 మి.మీ వర్షం పడితే నీరు ఎందుకు ఆపాలి?",
                    "📊 ట్రిగ్గర్ పాయింట్ మరియు ఫీల్డ్ కెపాసిటీ తేడా ఏమిటి?",
                    "🪴 సెన్సార్ లేకుండా నేల తేమను ఎలా పరీక్షించాలి?",
                    "🌾 నా రాష్ట్రానికి ఏ పంటలు అనుకూలం?"
                ];
            }
            return [
                "💧 నీటిని ఎలా ఆదా చేయాలి?",
                "🌾 వరి పంటకు ఎంత నీరు అవసరం?",
                "🪴 నేల తేమను ప్రభావితం చేసే అంశాలు ఏవి?",
                "📊 నా మునుపటి ఫలితాలు చూపించండి"
            ];
        }

        if (activeLang === "hi") {
            if (p.includes("धान") || p.includes("चावल") || p.includes("rice") || r.includes("धान")) {
                return [
                    "💧 वैकल्पिक गीला और सूखा (AWD) विधि क्या है?",
                    "📏 धान के खेत में पानी का स्तर कैसे मापें?",
                    "🌾 धान में सिंचाई के महत्वपूर्ण चरण कौन से हैं?",
                    "🌧️ बारिश के बाद सिंचाई कब शुरू करें?"
                ];
            }
            if (p.includes("काम करता") || p.includes("prediction") || r.includes("भविष्यवाणी")) {
                return [
                    "🌧️ 10 मिमी वर्षा होने पर सिंचाई क्यों रोक दी जाती है?",
                    "📊 ट्रिगर और फ़ील्ड क्षमता में क्या अंतर है?",
                    "🪴 बिना सेंसर मिट्टी की नमी कैसे जांचें?",
                    "🌾 मेरे राज्य के लिए सबसे उपयुक्त फसल कौन सी है?"
                ];
            }
            return [
                "💧 सिंचाई के पानी की बचत कैसे करें?",
                "🌾 धान को कितने पानी की आवश्यकता होती है?",
                "🪴 मिट्टी की नमी को प्रभावित करने वाले मुख्य कारक?",
                "📊 पिछले परिणाम दिखाओ"
            ];
        }

        // English default
        if (p.includes("rice") || p.includes("paddy") || r.includes("rice") || r.includes("paddy")) {
            return [
                "💧 How does Alternate Wetting and Drying (AWD) save water?",
                "📏 How do I measure standing water depth in paddy?",
                "🌾 What are the critical watering stages for paddy?",
                "🌧️ When should I resume irrigation after rain?"
            ];
        }

        if (p.includes("prediction") || p.includes("work") || p.includes("model") || r.includes("rules")) {
            return [
                "🌧️ Why does 10 mm of rain pause irrigation?",
                "📊 What is the difference between trigger and field capacity?",
                "🪴 How to test soil moisture without digital sensors?",
                "🌾 Which crop is most suitable for my state?"
            ];
        }

        return [
            "💧 How can I save irrigation water this season?",
            "🌾 How much water does rice require?",
            "🪴 What factors affect irrigation requirements?",
            "📊 Explain how irrigation prediction works."
        ];
    }

    function renderFollowUps(userPrompt, replyText, container, serverSuggestions) {
        // Remove existing followups inside messages
        const oldFollowups = messagesContainer ? messagesContainer.querySelectorAll(".agri-followups") : [];
        oldFollowups.forEach(el => el.remove());

        const followUps = (serverSuggestions && serverSuggestions.length)
            ? serverSuggestions
            : generateFollowUpSuggestions(userPrompt, replyText, currentLanguage);
        if (!followUps || followUps.length === 0) return;

        const wrap = document.createElement("div");
        wrap.className = "agri-followups";
        wrap.innerHTML = `<div class="agri-followups-title"><span aria-hidden="true">💡</span> <span>Suggested follow-up questions:</span></div>`;

        const chipsWrap = document.createElement("div");
        chipsWrap.className = "agri-followup-chips";

        followUps.forEach(q => {
            const chip = document.createElement("button");
            chip.type = "button";
            chip.className = "agri-followup-chip";
            chip.textContent = q;
            chip.addEventListener("click", () => {
                if (chatInput) chatInput.value = q;
                handleSendMessage(q);
            });
            chipsWrap.appendChild(chip);
        });

        wrap.appendChild(chipsWrap);
        container.appendChild(wrap);
        scrollToBottom();
    }

    // ----------------------------------------------------
    // Phase 1: Voice Recognition (SpeechRecognition)
    // ----------------------------------------------------
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let isListening = false;
    let micBtn = null;
    let voiceStatus = null;
    let voiceStatusText = null;
    let voiceStopBtn = null;

    const bcp47Map = {
        en: "en-IN",
        hi: "hi-IN",
        te: "te-IN",
        pa: "pa-IN",
        ta: "ta-IN",
        bn: "bn-IN",
        mr: "mr-IN",
        gu: "gu-IN",
        kn: "kn-IN",
        ml: "ml-IN",
        or: "or-IN",
        as: "as-IN",
        ur: "ur-IN",
        sa: "sa-IN",
        ne: "ne-NP",
        kok: "kok-IN",
        mai: "mai-IN",
        doi: "doi-IN",
        brx: "brx-IN",
        ks: "ks-IN",
        sd: "sd-IN",
        mni: "mni-IN",
        sat: "sat-IN"
    };

    function getSpeechLang() {
        if (currentLanguage && bcp47Map[currentLanguage]) {
            return bcp47Map[currentLanguage];
        }
        const docLang = (document.documentElement.lang || "en").toLowerCase();
        if (bcp47Map[docLang]) {
            return bcp47Map[docLang];
        }
        return "en-IN";
    }

    function getLanguageDisplayName(code) {
        const names = {
            en: "English",
            hi: "हिन्दी (Hindi)",
            te: "తెలుగు (Telugu)",
            pa: "ਪੰਜਾਬੀ (Punjabi)",
            ta: "தமிழ் (Tamil)",
            bn: "বাংলা (Bengali)",
            mr: "मराठी (Marathi)",
            gu: "ગુજરાતી (Gujarati)",
            kn: "ಕನ್ನಡ (Kannada)",
            ml: "മലയാളം (Malayalam)",
            or: "ଓଡ଼ିଆ (Odia)",
            as: "অসমীয়া (Assamese)",
            ur: "اردو (Urdu)",
            sa: "संस्कृतम् (Sanskrit)",
            ne: "नेपाली (Nepali)",
            kok: "कोंकणी (Konkani)",
            mai: "मैथिली (Maithili)",
            doi: "डोगरी (Dogri)",
            brx: "बड़ो (Bodo)",
            ks: "کٲشُر (Kashmiri)",
            sd: "سنڌي (Sindhi)",
            mni: "মৈতৈলোন্ (Manipuri)",
            sat: "ᱥᱟᱱᱛᱟᱲᱤ (Santali)",
            auto: "Auto-Detect"
        };
        return names[code] || "English";
    }

    let currentAudio = null;
    let wasVoiceInput = false;

    function stopAllSpeech() {
        if (currentAudio) {
            try {
                currentAudio.pause();
                currentAudio.currentTime = 0;
            } catch (e) {}
            currentAudio = null;
        }
        if (window.speechSynthesis && window.speechSynthesis.speaking) {
            try {
                window.speechSynthesis.cancel();
            } catch (e) {}
        }
    }

    function speakResponse(text, lang) {
        stopAllSpeech();
        if (!text) return;

        // Clean markdown characters and extra spacing
        const clean = text.replace(/[*#_`>]/g, "").replace(/\n+/g, " ").trim();
        if (!clean) return;

        const speechLang = lang || currentLanguage || "en";

        try {
            const url = `/api/voice/tts?lang=${encodeURIComponent(speechLang)}&text=${encodeURIComponent(clean.substring(0, 320))}`;
            currentAudio = new Audio(url);
            currentAudio.play().catch(() => {
                fallbackSpeak(clean, speechLang);
            });
        } catch (err) {
            fallbackSpeak(clean, speechLang);
        }
    }

    function fallbackSpeak(text, lang) {
        if (!window.speechSynthesis) return;
        try {
            const utterance = new SpeechSynthesisUtterance(text);
            const bcp = bcp47Map[lang] || "en-IN";
            utterance.lang = bcp;
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn("TTS fallback speech synthesis warning:", e);
        }
    }

    function stopVoiceRecognition(autoSubmit = false) {
        if (recognition && isListening) {
            try {
                recognition.stop();
            } catch (e) {}
        }
        isListening = false;
        if (micBtn) {
            micBtn.classList.remove("listening");
            micBtn.setAttribute("aria-label", "Dictate question with voice");
            micBtn.title = "Dictate question (Click to record, click again to finish)";
        }
        if (voiceStatus) {
            voiceStatus.style.display = "none";
        }
        if (chatInput) {
            chatInput.focus();
        }
        if (autoSubmit && chatInput && chatInput.value.trim()) {
            const textToSubmit = chatInput.value.trim();
            handleSendMessage(textToSubmit);
        }
    }

    function handleVoiceNetworkFallback() {
        if (voiceStatus && voiceStatusText) {
            voiceStatus.style.display = "flex";
            const langName = getLanguageDisplayName(currentLanguage);
            voiceStatusText.textContent = `🎙️ Voice Assistant Ready (${langName}) — tap a question or type`;
            setTimeout(() => {
                if (!isListening && voiceStatus) voiceStatus.style.display = "none";
            }, 6000);
        }

        renderVoiceFallbackChips();
    }

    function renderVoiceFallbackChips() {
        if (!suggestionsContainer) return;
        const chipsByLang = {
            te: [
                "💧 వరి పంటలో నీటిని ఎలా ఆదా చేయాలి?",
                "🌾 నా పంటకు సాగునీరు ఎప్పుడు పెట్టాలి?",
                "📊 నేల తేమ ఫలితం వివరంగా చెప్పండి"
            ],
            hi: [
                "💧 धान में पानी की बचत कैसे करें?",
                "🌾 फसल में सिंचाई का सही समय क्या है?",
                "📊 मिट्टी की नमी का परिणाम समझाएं"
            ],
            pa: [
                "💧 ਝੋਨੇ ਵਿੱਚ ਸਿੰਚਾਈ ਪਾਣੀ ਦੀ ਬੱਚਤ ਕਿਵੇਂ ਕਰੀਏ?",
                "🌾 ਫ਼ਸਲ ਨੂੰ ਪਾਣੀ ਕਦੋਂ ਅਤੇ ਕਿੰਨਾ ਦੇਣਾ ਚਾਹੀਦਾ ਹੈ?",
                "📊 ਮਿੱਟੀ ਦੀ ਨਮੀ ਦਾ ਨਤੀਜਾ ਸਮਝਾਓ"
            ],
            en: [
                "💧 How can I save irrigation water?",
                "🌾 When is the best time to irrigate my crop?",
                "📊 Help me understand my soil moisture reading"
            ]
        };

        const chips = chipsByLang[currentLanguage] || chipsByLang.en;
        suggestionsContainer.innerHTML = "";
        const titleEl = document.createElement("div");
        titleEl.className = "agri-suggestions-title";
        titleEl.textContent = currentLanguage === "te" ? "వాయిస్ ప్రశ్నలు (త్వరిత ఎంపిక):" :
                             currentLanguage === "hi" ? "त्वरित आवाज प्रश्न (सुझाव):" :
                             currentLanguage === "pa" ? "ਤੁਰੰਤ ਆਵਾਜ਼ ਸਵਾਲ (ਸੁਝਾਅ):" : "Voice Quick Questions:";
        suggestionsContainer.appendChild(titleEl);

        chips.forEach(q => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "agri-suggestion-chip voice-fallback-chip";
            btn.textContent = q;
            btn.addEventListener("click", () => {
                if (chatInput) chatInput.value = q;
                handleSendMessage(q);
            });
            suggestionsContainer.appendChild(btn);
        });
        suggestionsContainer.style.display = "flex";
    }

    function startVoiceRecognition() {
        if (!SpeechRecognition) {
            alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }

        if (isListening) {
            // Click 2: Finish voice dictation, keep recognized text in input box for review or editing
            stopVoiceRecognition(false);
            return;
        }

        stopAllSpeech();
        wasVoiceInput = false;

        try {
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.maxAlternatives = 1;
            recognition.lang = getSpeechLang();

            recognition.onstart = () => {
                isListening = true;
                if (micBtn) {
                    micBtn.classList.add("listening");
                    micBtn.setAttribute("aria-label", "Recording question. Click again to finish dictation");
                    micBtn.title = "Recording question. Click again to finish dictation";
                }
                if (voiceStatus && voiceStatusText) {
                    const langName = getLanguageDisplayName(currentLanguage);
                    voiceStatusText.textContent = `🎙️ Listening in ${langName}... Speak your question, then click microphone to finish`;
                    voiceStatus.style.display = "flex";
                }
            };

            recognition.onresult = (event) => {
                let interimTranscript = "";
                let finalTranscript = "";

                for (let i = 0; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + " ";
                    } else {
                        interimTranscript += event.results[i][0].transcript + " ";
                    }
                }

                const recognized = (finalTranscript + interimTranscript).trim();
                if (recognized && chatInput) {
                    chatInput.value = recognized;
                }
            };

            recognition.onerror = (event) => {
                console.warn("Speech recognition error:", event.error);
                if (event.error === "network") {
                    console.info("Speech recognition network error: activating robust voice fallback.");
                    stopVoiceRecognition(false);
                    handleVoiceNetworkFallback();
                    return;
                }

                let msg = "Could not recognize speech. Please try speaking again.";
                if (event.error === "not-allowed") {
                    msg = "Microphone permission denied. Please allow microphone permissions in browser settings.";
                } else if (event.error === "no-speech") {
                    msg = "No speech detected. Please speak clearly into your microphone.";
                } else if (event.error === "audio-capture") {
                    msg = "No microphone was found. Please ensure a microphone is connected.";
                }

                if (voiceStatusText) {
                    voiceStatusText.textContent = `⚠️ ${msg}`;
                }
                stopVoiceRecognition(false);
            };

            recognition.onend = () => {
                if (isListening) {
                    isListening = false;
                    if (micBtn) micBtn.classList.remove("listening");
                    if (voiceStatus) voiceStatus.style.display = "none";
                }
            };

            recognition.start();
        } catch (err) {
            console.error("Speech recognition startup error:", err);
            stopVoiceRecognition(false);
        }
    }

    // ----------------------------------------------------
    // Unified Website Action Dispatcher
    // ----------------------------------------------------
    async function dispatchWebsiteAction(action, payload) {
        console.log("Dispatching Website Action:", action, payload);

        switch (action) {
            case "navigate_to_page":
                handleNavigationAction(payload);
                break;

            case "select_section":
                if (payload.section_id && window.selectSection) {
                    window.selectSection(payload.section_id);
                }
                const secCard = document.querySelector(`.section-card[data-id="${payload.section_id}"]`);
                if (secCard) {
                    secCard.scrollIntoView({ behavior: "smooth", block: "center" });
                    secCard.classList.add("voice-action-highlight");
                    setTimeout(() => secCard.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "add_land_section":
                if (typeof window.openAddSectionModal === "function") {
                    window.openAddSectionModal();
                    const nameInput = document.getElementById("modalSectionName");
                    const areaInput = document.getElementById("modalSectionArea");
                    const cropSelect = document.getElementById("modalCropSelect");

                    if (nameInput && payload.name) nameInput.value = payload.name;
                    if (areaInput && payload.area_acres) areaInput.value = payload.area_acres;
                    if (cropSelect && payload.crop) cropSelect.value = payload.crop;
                }
                break;

            case "edit_land_section":
                if (payload.section_id && typeof window.openEditSectionModal === "function") {
                    window.openEditSectionModal(payload.section_id);
                    const areaInput = document.getElementById("modalSectionArea");
                    const cropSelect = document.getElementById("modalCropSelect");
                    if (areaInput && payload.area_acres) areaInput.value = payload.area_acres;
                    if (cropSelect && payload.crop) cropSelect.value = payload.crop;
                }
                break;

            case "remove_land_section":
                if (payload.section_id && window.currentFarm && typeof window.loadFarmSections === "function") {
                    await window.loadFarmSections(window.currentFarm.id);
                }
                break;

            case "run_irrigation_prediction":
                if (payload.section_id && window.selectSection) {
                    window.selectSection(payload.section_id);
                }
                const plannerSec = document.getElementById("irrigation-planner");
                if (plannerSec) plannerSec.scrollIntoView({ behavior: "smooth", block: "start" });
                if (window.triggerPrediction) {
                    window.triggerPrediction();
                } else {
                    const btn = document.getElementById("predictButton");
                    if (btn) btn.click();
                }
                break;

            case "calculate_water_requirement":
            case "generate_irrigation_schedule":
                const schedCard = document.getElementById("smartSchedulerCard");
                if (schedCard) {
                    schedCard.style.display = "block";
                    schedCard.scrollIntoView({ behavior: "smooth", block: "center" });
                }
                const btnGen = document.getElementById("btnGenerateSectionSchedule");
                if (btnGen) btnGen.click();
                break;

            case "get_weather":
                const weatherSec = document.getElementById("sectionWeather");
                if (weatherSec) {
                    weatherSec.scrollIntoView({ behavior: "smooth", block: "center" });
                    weatherSec.classList.add("voice-action-highlight");
                    setTimeout(() => weatherSec.classList.remove("voice-action-highlight"), 2500);
                }
                const btnRefresh = document.getElementById("btnRefreshWeather");
                if (btnRefresh) btnRefresh.click();
                break;

            case "get_farm_summary":
                const farmSec = document.getElementById("sectionFarmOverview");
                if (farmSec) {
                    farmSec.scrollIntoView({ behavior: "smooth", block: "start" });
                    farmSec.classList.add("voice-action-highlight");
                    setTimeout(() => farmSec.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "get_upcoming_schedule":
                if (window.openMiniCalendar) {
                    window.openMiniCalendar();
                }
                break;

            case "update_irrigation_status":
                if (payload.status === "Completed") {
                    if (window.markCurrentSessionCompleted) window.markCurrentSessionCompleted();
                } else if (payload.status === "Skipped") {
                    if (window.skipCurrentSession) window.skipCurrentSession();
                }
                break;

            case "set_onboarding_field":
                handleOnboardingField(payload);
                break;

            case "complete_onboarding":
                const finishBtn = document.getElementById("btnCompleteOnboarding") || document.getElementById("btnOnboardSave");
                if (finishBtn) finishBtn.click();
                break;

            default:
                console.log("Unhandled action:", action);
        }
    }

    function handleNavigationAction(payload) {
        const target = payload.target;
        switch (target) {
            case "dashboard":
                if (window.location.pathname.includes("/dashboard")) {
                    window.scrollTo({ top: 0, behavior: "smooth" });
                } else {
                    window.location.href = "/dashboard";
                }
                break;

            case "my_farms":
                const elFarms = document.getElementById("sectionFarmOverview");
                if (elFarms) elFarms.scrollIntoView({ behavior: "smooth", block: "start" });
                break;

            case "land_sections":
                const elSecs = document.getElementById("sectionLandSections");
                if (elSecs) elSecs.scrollIntoView({ behavior: "smooth", block: "start" });
                break;

            case "irrigation_planner":
                if (window.scrollToIrrigationPlanner) {
                    window.scrollToIrrigationPlanner();
                } else {
                    const elPlanner = document.getElementById("irrigation-planner");
                    if (elPlanner) elPlanner.scrollIntoView({ behavior: "smooth", block: "start" });
                }
                break;

            case "irrigation_calendar":
                if (window.openMiniCalendar) window.openMiniCalendar();
                break;

            case "combined_calendar":
                if (window.openGlobalCalendar) window.openGlobalCalendar();
                break;

            case "irrigation_history":
                if (window.openPredictionHistory) window.openPredictionHistory();
                break;

            case "profile":
                const menu = document.getElementById("farmerDropdownMenu");
                if (menu) menu.style.display = (menu.style.display === "block" ? "none" : "block");
                break;

            case "ai_assistant":
                openChat();
                break;

            case "go_back":
                window.history.back();
                break;

            case "home":
                window.location.href = "/";
                break;

            case "logout":
                window.location.href = "/logout";
                break;
        }
    }

    function handleOnboardingField(payload) {
        const field = payload.field;
        const val = payload.value;
        if (!field || val === undefined) return;

        if (field === "state") {
            const stateSelect = document.getElementById("onboardState");
            if (stateSelect) {
                for (let opt of stateSelect.options) {
                    if (opt.value.toLowerCase() === String(val).toLowerCase() || opt.text.toLowerCase().includes(String(val).toLowerCase())) {
                        stateSelect.value = opt.value;
                        stateSelect.dispatchEvent(new Event("change"));
                        break;
                    }
                }
            }
        } else if (field === "district") {
            const distInput = document.getElementById("onboardDistrict");
            if (distInput) {
                distInput.value = val;
                distInput.dispatchEvent(new Event("input"));
            }
        } else if (field === "total_land") {
            const landInput = document.getElementById("onboardTotalLand");
            if (landInput) {
                landInput.value = val;
                landInput.dispatchEvent(new Event("input"));
                landInput.dispatchEvent(new Event("change"));
            }
        } else if (field === "farmer_name") {
            const nameInput = document.getElementById("onboardFarmerName");
            if (nameInput) {
                nameInput.value = val;
                nameInput.dispatchEvent(new Event("input"));
            }
        } else if (field === "step") {
            const stepNum = parseInt(val, 10);
            if (typeof window.goToOnboardingStep === "function") {
                window.goToOnboardingStep(stepNum);
            }
        }
    }

    function appendMessage(text, sender = "user", isHTML = false, isError = false, customTime = null) {
        if (!messagesContainer) return null;

        const row = document.createElement("div");
        row.className = `agri-msg-row agri-msg-${sender}${isError ? " agri-msg-error" : ""}`;

        const avatar = document.createElement("div");
        avatar.className = "agri-msg-avatar";
        avatar.setAttribute("aria-hidden", "true");
        avatar.textContent = sender === "user" ? "👨‍🌾" : (isError ? "⚠️" : "🌱");

        const bubble = document.createElement("div");
        bubble.className = "agri-msg-bubble";

        const textEl = document.createElement("div");
        textEl.className = "agri-msg-text";
        if (isHTML) {
            textEl.innerHTML = text;
        } else {
            textEl.textContent = text;
        }

        const actionsEl = document.createElement("div");
        actionsEl.className = "agri-msg-actions";

        if (sender === "assistant" && !isError) {
            const speakBtn = document.createElement("button");
            speakBtn.type = "button";
            speakBtn.className = "agri-speak-btn";
            speakBtn.setAttribute("aria-label", "Read aloud");
            speakBtn.title = "Read aloud";
            speakBtn.innerHTML = `<span aria-hidden="true">🔊</span> <span>Listen</span>`;
            speakBtn.addEventListener("click", () => {
                toggleSpeakMessage(textEl.textContent, speakBtn);
            });
            actionsEl.appendChild(speakBtn);
        }

        const timeEl = document.createElement("span");
        timeEl.className = "agri-msg-time";
        timeEl.textContent = customTime || formatTime(new Date());
        actionsEl.appendChild(timeEl);

        bubble.appendChild(textEl);
        bubble.appendChild(actionsEl);

        row.appendChild(avatar);
        row.appendChild(bubble);

        messagesContainer.appendChild(row);
        scrollToBottom();

        return bubble;
    }

    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = "flex";
            scrollToBottom();
        }
    }

    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.style.display = "none";
        }
    }

    function setSubmissionState(disabled) {
        isTyping = disabled;
        if (sendBtn) sendBtn.disabled = disabled;
        if (chatInput) chatInput.disabled = disabled;
        const chips = document.querySelectorAll(".agri-chip");
        chips.forEach(c => { c.disabled = disabled; });
    }

    async function handleSendMessage(text) {
        const messageText = (text || (chatInput ? chatInput.value : "")).trim();
        
        if (!messageText || isTyping) return;

        // Command shortcut for clearing chat / starting new chat
        if (messageText.toLowerCase() === "/clear" || messageText.toLowerCase() === "clear") {
            startNewChat();
            return;
        }

        if (messageText.length > 1000) {
            appendMessage("Please limit your question to 1000 characters.", "assistant", false, true);
            return;
        }

        userHasSentMessages = true;
        setSubmissionState(true);

        const now = Date.now();
        const timeFormatted = formatTime(new Date(now));

        // Display user message in UI
        appendMessage(messageText, "user", false, false, timeFormatted);

        if (chatInput) {
            chatInput.value = "";
        }

        // Persistent History: create new conversation entry or append to active one
        let history = loadAllHistory();
        let currentConv = activeConversationId ? history.find(c => c.id === activeConversationId) : null;

        if (!currentConv) {
            const cleanTitle = messageText.length > 45 ? messageText.substring(0, 45).trim() + "..." : messageText;
            const newId = "conv_" + now + "_" + Math.random().toString(36).substring(2, 7);
            currentConv = {
                id: newId,
                title: cleanTitle,
                createdAt: now,
                updatedAt: now,
                language: currentLanguage,
                messages: []
            };
            history.unshift(currentConv);
            setActiveConversationId(newId);
        }

        // Add user message to persistent conversation
        currentConv.messages.push({
            role: "user",
            content: messageText,
            timestamp: now,
            timeStr: timeFormatted
        });
        currentConv.updatedAt = now;
        saveAllHistory(history);

        // Format recent in-memory session messages before pushing the current one
        const historyToSend = sessionMessages.slice(-MAX_SESSION_HISTORY).map(m => ({
            role: m.role,
            content: m.content
        }));

        // Record user message into in-memory session history for Gemini tool grounding
        sessionMessages.push({ role: "user", content: messageText });

        showTypingIndicator();

        // Build combined context including latest prediction and page metadata
        const contextPayload = getCombinedContext();
        if (window.lastPredictionResult) {
            contextPayload.last_prediction = window.lastPredictionResult;
        }
        if (window.currentFarmer) {
            contextPayload.farmer_id = window.currentFarmer.id;
            contextPayload.farmer_name = window.currentFarmer.name;
        }
        if (window.activeSectionId) {
            contextPayload.active_section_id = window.activeSectionId;
        }
        if (window.agriPendingAction) {
            contextPayload.pending_action = window.agriPendingAction;
        }

        // Determine current page context
        const isDashboard = !!document.getElementById("sectionFarmOverview") || !!document.getElementById("landManagementModule");
        const isOnboard = !!document.getElementById("onboardState") || !!document.getElementById("paneStep1");
        const isLogin = !!document.getElementById("formFarmerLogin");
        const isRegister = !!document.getElementById("formFarmerRegister");
        const isAdmin = !!document.querySelector(".admin-dashboard-body");
        contextPayload.page = isDashboard ? "dashboard" : (isOnboard ? "onboarding" : (isRegister ? "register" : (isAdmin ? "admin" : "login")));

        const payload = {
            message: messageText,
            language: currentLanguage,
            farmer_id: window.currentFarmer ? window.currentFarmer.id : null,
            context: contextPayload,
            history: historyToSend
        };

        const dict = chatTranslations[currentLanguage] || chatTranslations.auto;
        const wasVoice = wasVoiceInput;
        wasVoiceInput = false;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            const replyNow = Date.now();
            const replyTime = formatTime(new Date(replyNow));

            if (!response.ok) {
                const errMsg = data.error || dict.networkError;
                appendMessage(errMsg, "assistant", false, true, replyTime);

                const allH = loadAllHistory();
                const activeC = allH.find(c => c.id === activeConversationId);
                if (activeC) {
                    activeC.messages.push({
                        role: "assistant",
                        content: errMsg,
                        isError: true,
                        timestamp: replyNow,
                        timeStr: replyTime
                    });
                    activeC.updatedAt = replyNow;
                    saveAllHistory(allH);
                }
            } else if (data.requires_confirmation) {
                // Destructive action requiring explicit confirmation (e.g. section deletion)
                window.agriPendingAction = {
                    action: data.action,
                    payload: data.action_payload
                };

                const confirmText = data.confirmation_prompt || data.reply || "Do you confirm this action?";
                const confirmHtml = `
                    <div class="agri-confirm-box">
                        <p class="agri-confirm-msg">${formatMarkdown(confirmText)}</p>
                        <div class="agri-confirm-btns">
                            <button type="button" class="agri-btn-confirm" id="btnAgriConfirmYes">✓ Yes, Confirm</button>
                            <button type="button" class="agri-btn-cancel" id="btnAgriConfirmNo">✕ Cancel</button>
                        </div>
                    </div>
                `;
                const bubbleEl = appendMessage(confirmHtml, "assistant", true, false, replyTime);
                if (bubbleEl) {
                    const yesBtn = bubbleEl.querySelector("#btnAgriConfirmYes");
                    const noBtn = bubbleEl.querySelector("#btnAgriConfirmNo");
                    if (yesBtn) {
                        yesBtn.addEventListener("click", () => {
                            handleSendMessage("Yes, confirm");
                        });
                    }
                    if (noBtn) {
                        noBtn.addEventListener("click", () => {
                            window.agriPendingAction = null;
                            handleSendMessage("Cancel");
                        });
                    }
                }
                if (wasVoice) {
                    speakResponse(confirmText, data.language || currentLanguage);
                }
            } else if (data.reply) {
                // Clear pending confirmation on normal action / query execution
                window.agriPendingAction = null;

                // Dispatch website action if whitelisted and actionable
                if (data.action && data.action !== "general_query" && data.action !== "ask_clarification" && data.action !== "cancel_action") {
                    await dispatchWebsiteAction(data.action, data.action_payload || {});
                }

                sessionMessages.push({ role: "assistant", content: data.reply });
                const formattedHtml = formatMarkdown(data.reply);
                const bubbleEl = appendMessage(formattedHtml, "assistant", true, false, replyTime);

                // Speak verbal response if farmer used voice input
                if (wasVoice) {
                    speakResponse(data.reply, data.language || currentLanguage);
                }

                // Render dynamic follow-up suggestions
                if (bubbleEl) {
                    renderFollowUps(messageText, data.reply, bubbleEl, data.suggestions);
                }

                // Synchronize dual calendars if chat query was schedule-related
                if (window.refreshSchedulerUI && (
                    messageText.toLowerCase().includes("calendar") ||
                    messageText.toLowerCase().includes("schedule") ||
                    messageText.toLowerCase().includes("irrigation") ||
                    messageText.toLowerCase().includes("complete") ||
                    messageText.toLowerCase().includes("skip") ||
                    messageText.toLowerCase().includes("reschedule")
                )) {
                    window.refreshSchedulerUI();
                }

                const allH = loadAllHistory();
                const activeC = allH.find(c => c.id === activeConversationId);
                if (activeC) {
                    activeC.messages.push({
                        role: "assistant",
                        content: data.reply,
                        timestamp: replyNow,
                        timeStr: replyTime
                    });
                    activeC.updatedAt = replyNow;
                    saveAllHistory(allH);
                }
            } else {
                appendMessage(dict.networkError, "assistant", false, true, replyTime);
            }
        } catch (error) {
            const replyNow = Date.now();
            const replyTime = formatTime(new Date(replyNow));
            appendMessage(dict.networkError, "assistant", false, true, replyTime);
        } finally {
            hideTypingIndicator();
            setSubmissionState(false);
            if (chatInput) chatInput.focus();
        }
    }

    function init() {
        // AgriSaathi chatbot is restricted strictly to the Farmer Dashboard
        const widget = document.getElementById("agriChatWidget");
        if (!widget) return;

        toggleBtn = document.getElementById("agriChatToggle");
        chatWindow = document.getElementById("agriChatWindow");
        closeBtn = document.getElementById("agriChatClose");
        clearBtn = document.getElementById("agriChatClear");
        newChatBtn = document.getElementById("agriNewChatBtn");
        historyBtn = document.getElementById("agriHistoryBtn");
        historyPanel = document.getElementById("agriHistoryPanel");
        historyList = document.getElementById("agriHistoryList");
        historyCloseBtn = document.getElementById("agriHistoryCloseBtn");
        newChatFromHistoryBtn = document.getElementById("agriNewChatFromHistoryBtn");
        clearAllHistoryBtn = document.getElementById("agriClearAllHistoryBtn");
        historyTitleEl = document.getElementById("agriHistoryTitle");
        newChatBtnTextEl = document.getElementById("agriNewChatBtnText");
        clearAllBtnTextEl = document.getElementById("agriClearAllBtnText");
        messagesContainer = document.getElementById("agriChatMessages");
        chatForm = document.getElementById("agriChatForm");
        chatInput = document.getElementById("agriChatInput");
        sendBtn = document.getElementById("agriSendBtn");
        langSelect = document.getElementById("agriChatLang");
        typingIndicator = document.getElementById("agriTypingIndicator");
        suggestionsContainer = document.getElementById("agriSuggestions");
        welcomeTextEl = document.getElementById("agriWelcomeText");
        micBtn = document.getElementById("agriMicBtn");
        voiceStatus = document.getElementById("agriVoiceStatus");
        voiceStatusText = document.getElementById("agriVoiceStatusText");
        voiceStopBtn = document.getElementById("agriVoiceStopBtn");

        if (!toggleBtn || !chatWindow) return;

        if (micBtn) {
            micBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (isListening) {
                    stopVoiceRecognition(true);
                } else {
                    startVoiceRecognition();
                }
            });
        }

        // Synchronize with host page language selector
        const hostLangSelect = document.getElementById("languageSelect") || document.getElementById("onboardLanguageSelect");
        if (hostLangSelect) {
            hostLangSelect.addEventListener("change", () => {
                if (hostLangSelect.value && hostLangSelect.value !== currentLanguage) {
                    setChatLanguage(hostLangSelect.value, true);
                }
            });
        }

        if (voiceStopBtn) {
            voiceStopBtn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                stopVoiceRecognition();
            });
        }

        toggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleChat();
        });

        if (closeBtn) {
            closeBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                closeChat();
            });
        }

        if (clearBtn) {
            clearBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                startNewChat();
            });
        }

        if (newChatBtn) {
            newChatBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                startNewChat();
            });
        }

        if (historyBtn) {
            historyBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                toggleHistoryPanel();
            });
        }

        if (clearConvBtn) {
            clearConvBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                clearActiveConversation();
            });
        }

        if (historyCloseBtn) {
            historyCloseBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                closeHistoryPanel();
            });
        }

        if (newChatFromHistoryBtn) {
            newChatFromHistoryBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                startNewChat();
            });
        }

        if (clearAllHistoryBtn) {
            clearAllHistoryBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                clearAllHistory();
            });
        }

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && chatWindow && !chatWindow.hidden) {
                if (historyPanelOpen) {
                    closeHistoryPanel();
                } else {
                    closeChat();
                }
            }
        });

        // Ensure history panel starts in closed state
        closeHistoryPanel();

        // Initialize language with stored preference or default to 'auto'
        let savedLang = "auto";
        try {
            savedLang = localStorage.getItem(STORAGE_LANG_KEY) || "auto";
        } catch (e) {
            savedLang = "auto";
        }

        if (langSelect) {
            langSelect.addEventListener("change", () => {
                setChatLanguage(langSelect.value, true);
            });
            setChatLanguage(savedLang, false);
        }

        if (chatForm) {
            chatForm.addEventListener("submit", (e) => {
                e.preventDefault();
                handleSendMessage();
            });
        }

        if (suggestionsContainer) {
            suggestionsContainer.addEventListener("click", (e) => {
                const chip = e.target.closest(".agri-chip");
                if (!chip || isTyping) return;
                const question = chip.getAttribute("data-question");
                if (question) {
                    handleSendMessage(question);
                }
            });
        }

        // Restore active conversation from localStorage if present
        const savedActiveId = getActiveConversationId();
        if (savedActiveId) {
            const allH = loadAllHistory();
            const existing = allH.find(c => c.id === savedActiveId);
            if (existing && existing.messages && existing.messages.length > 0) {
                loadConversation(savedActiveId);
            }
        }

        // Keep session sensor memory synchronized with dashboard form interactions
        const sensorInputIds = ["crop_type", "crop_days", "soil_moisture", "soil_temperature", "temperature", "humidity"];
        sensorInputIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const updateSensor = () => {
                    if (el.value !== "" && !isNaN(Number(el.value))) {
                        sessionSensors[id] = Number(el.value);
                    }
                };
                el.addEventListener("change", updateSensor);
                el.addEventListener("input", updateSensor);
            }
        });
        // Expose voice assistant interface for testing and accessibility
        window.agriVoiceAssistant = {
            startListening: startVoiceRecognition,
            stopListening: stopVoiceRecognition,
            isListening: () => isListening,
            handleCommand: handleVoiceControlCommand,
            speak: toggleSpeakMessage,
            stopSpeech: stopAllSpeech,
            generateFollowUps: generateFollowUpSuggestions,
            sendMessage: handleSendMessage
        };

        window.appendChatMessage = function(text, sender) {
            appendMessage(text, sender, false, false, formatTime(new Date()));
        };
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
