/**
 * Smart Irrigation Planner - Frontend Application
 * Handles State & Crop selection, Decision Zone Visualization,
 * Multi-unit sensor inputs, Rainfall evaluation, and ML predictions.
 */

// WebAuthn domain standardization: seamlessly redirect 127.0.0.1 to localhost
if (typeof window !== "undefined" && window.location && window.location.hostname === "127.0.0.1") {
    window.location.replace(window.location.href.replace("://127.0.0.1", "://localhost"));
}

const translations = {
    en: {
        title: "Smart Irrigation Planner",
        subtitle: "Simple support for smarter farming",
        languageLabel: "Choose Language",
        welcome: "Let's check your field",
        intro: "Enter your crop and sensor readings.",
        formTitle: "Crop and Soil Details",
        stateLabel: "Step 1: Select State or Union Territory",
        cropLabel: "Step 2: Select Crop",
        btnLocation: "Detect",
        daysLabel: "Crop age (days)",
        moistureLabel: "Soil moisture (% of field capacity)",
        moistureHelp: "Enter the sensor reading (0 - 100%).",
        moistureRiceLabel: "Water level (cm relative to soil surface)",
        moistureRiceHelp: "Enter water level relative to soil surface (-25 to +5 cm).",
        soilTempLabel: "Soil temperature",
        airTempLabel: "Air temperature",
        humidityLabel: "Relative humidity",
        rainfall7dLabel: "Rainfall in last 7 days (mm) *",
        rainfall7dHelp: "Required. If 10 mm or more, irrigation is paused automatically.",
        forecast24hLabel: "Forecast rainfall next 24 hours (mm)",
        forecast24hHelp: "Optional (default is 0 mm).",
        unitWarning: "Temperatures are converted to Celsius for ML prediction. Ranges CSV is the single source of truth.",
        predict: "Check Irrigation",
        resultTitle: "Your result",
        resultPlaceholder: "Your prediction will appear here.",
        disclaimer: "This prediction combines genuine state-wise crop rules with Machine Learning. Always verify field conditions before irrigating.",
        irrigate: "IRRIGATE — Water Needed",
        monitor: "MONITOR — Do Not Irrigate Yet",
        noIrrigate: "DO NOT IRRIGATE — Soil Wet Enough",
        probability: "Probability of irrigation needed",
        loading: "Evaluating state rules & ML prediction...",
        error: "Could not get a prediction. Please check your inputs.",
        modelInfoTitle: "Model & Dataset Specifications",
        infoCrop: "Active Crop",
        infoAlgorithm: "Algorithm",
        infoDataset: "Dataset Source",
        infoRecords: "Total Samples",
        infoAccuracy: "Accuracy",
        infoPrecision: "Decision Source",
        infoDate: "Status"
    },

    hi: {
        title: "स्मार्ट सिंचाई योजनाकार",
        subtitle: "बेहतर खेती के लिए आसान सहायता",
        languageLabel: "भाषा चुनें",
        welcome: "अपने खेत की स्थिति देखें",
        intro: "अपनी फसल और सेंसर की रीडिंग भरें।",
        formTitle: "फसल और मिट्टी का विवरण",
        stateLabel: "चरण 1: राज्य या केंद्र शासित प्रदेश चुनें",
        cropLabel: "चरण 2: फसल चुनें",
        btnLocation: "पहचानें",
        daysLabel: "फसल की उम्र (दिन)",
        moistureLabel: "मिट्टी की नमी (% फ़ील्ड क्षमता)",
        moistureHelp: "सेंसर की रीडिंग भरें (0 - 100%)।",
        moistureRiceLabel: "पानी का स्तर (सेमी, मिट्टी की सतह के सापेक्ष)",
        moistureRiceHelp: "धान में पानी का स्तर (-25 से +5 सेमी)।",
        soilTempLabel: "मिट्टी का तापमान",
        airTempLabel: "हवा का तापमान",
        humidityLabel: "सापेक्ष आर्द्रता",
        rainfall7dLabel: "पिछले 7 दिनों में वर्षा (मिमी) *",
        rainfall7dHelp: "अनिवार्य। 10 मिमी या अधिक होने पर सिंचाई रोक दी जाती है।",
        forecast24hLabel: "अगले 24 घंटों में अनुमानित वर्षा (मिमी)",
        forecast24hHelp: "वैकल्पिक (डिफ़ॉल्ट 0 मिमी)।",
        unitWarning: "एमएल भविष्यवाणी के लिए तापमान को सेल्सियस में बदला जाता है।",
        predict: "सिंचाई की जाँच करें",
        resultTitle: "आपका परिणाम",
        resultPlaceholder: "आपकी भविष्यवाणी यहाँ दिखाई देगी।",
        disclaimer: "यह राज्य-वार कृषि नियमों और मशीन लर्निंग पर आधारित परिणाम है।",
        irrigate: "सिंचाई करें — पानी की आवश्यकता है",
        monitor: "निगरानी रखें — अभी सिंचाई न करें",
        noIrrigate: "सिंचाई न करें — मिट्टी में पर्याप्त नमी है",
        probability: "सिंचाई की आवश्यकता की संभावना",
        loading: "राज्य के नियमों और मॉडल द्वारा जाँच की जा रही है...",
        error: "अनुमान नहीं मिल सका। कृपया जानकारी जाँचें।",
        modelInfoTitle: "मॉडल एवं डेटासेट विनिर्देश",
        infoCrop: "चयनित फसल",
        infoAlgorithm: "एल्गोरिथम",
        infoDataset: "डेटासेट स्रोत",
        infoRecords: "कुल नमूने",
        infoAccuracy: "सटीकता (Accuracy)",
        infoPrecision: "निर्णय का आधार",
        infoDate: "स्थिति"
    },

    pa: {
        title: "ਸਮਾਰਟ ਸਿੰਚਾਈ ਯੋਜਨਾਕਾਰ",
        subtitle: "ਬਿਹਤਰ ਖੇਤੀ ਲਈ ਆਸਾਨ ਮਦਦ",
        languageLabel: "ਭਾਸ਼ਾ ਚੁਣੋ",
        welcome: "ਆਪਣੇ ਖੇਤ ਦੀ ਸਥਿਤੀ ਵੇਖੋ",
        intro: "ਆਪਣੀ ਫ਼ਸਲ ਅਤੇ ਸੈਂਸਰ ਦੀਆਂ ਰੀਡਿੰਗਾਂ ਭਰੋ।",
        formTitle: "ਫ਼ਸਲ ਅਤੇ ਮਿੱਟੀ ਦਾ ਵੇਰਵਾ",
        stateLabel: "ਕਦਮ 1: ਰਾਜ ਜਾਂ ਕੇਂਦਰ ਸ਼ਾਸਿਤ ਪ੍ਰਦੇਸ਼ ਚੁਣੋ",
        cropLabel: "ਕਦਮ 2: ਫ਼ਸਲ ਚੁਣੋ",
        btnLocation: "ਖੋਜੋ",
        daysLabel: "ਫ਼ਸਲ ਦੀ ਉਮਰ (ਦਿਨ)",
        moistureLabel: "ਮਿੱਟੀ ਦੀ ਨਮੀ (% ਫੀਲਡ ਸਮਰੱਥਾ)",
        moistureHelp: "ਸੈਂਸਰ ਦੀ ਰੀਡਿੰਗ ਭਰੋ (0 - 100%)।",
        moistureRiceLabel: "ਪਾਣੀ ਦਾ ਪੱਧਰ (ਸੈਂਟੀਮੀਟਰ)",
        moistureRiceHelp: "ਮਿੱਟੀ ਦੀ ਸਤ੍ਹਾ ਅਨੁਸਾਰ ਪਾਣੀ ਦਾ ਪੱਧਰ (-25 ਤੋਂ +5 ਸੈਂਟੀਮੀਟਰ)।",
        soilTempLabel: "ਮਿੱਟੀ ਦਾ ਤਾਪਮਾਨ",
        airTempLabel: "ਹਵਾ ਦਾ ਤਾਪਮਾਨ",
        humidityLabel: "ਸਾਪੇਖ ਨਮੀ",
        rainfall7dLabel: "ਪਿਛਲੇ 7 ਦਿਨਾਂ ਵਿੱਚ ਮੀਂਹ (ਮਿਲੀਮੀਟਰ) *",
        rainfall7dHelp: "ਲਾਜ਼ਮੀ। ਜੇਕਰ 10 ਮਿਲੀਮੀਟਰ ਜਾਂ ਵੱਧ ਹੈ, ਤਾਂ ਸਿੰਚਾਈ ਰੋਕੀ ਜਾਂਦੀ ਹੈ।",
        forecast24hLabel: "ਅਗਲੇ 24 ਘੰਟਿਆਂ ਵਿੱਚ ਮੀਂਹ ਦਾ ਅਨੁਮਾਨ (ਮਿਲੀਮੀਟਰ)",
        forecast24hHelp: "ਵਿਕਲਪਿਕ (ਮੂਲ 0 ਮਿਲੀਮੀਟਰ)।",
        unitWarning: "ਅਨੁਮਾਨ ਲਈ ਤਾਪਮਾਨ ਸੈਲਸੀਅਸ ਵਿੱਚ ਬਦਲਿਆ ਜਾਂਦਾ ਹੈ।",
        predict: "ਸਿੰਚਾਈ ਦੀ ਜਾਂਚ ਕਰੋ",
        resultTitle: "ਤੁਹਾਡਾ ਨਤੀਜਾ",
        resultPlaceholder: "ਤੁਹਾਡਾ ਅਨੁਮਾਨ ਇੱਥੇ ਦਿਖਾਈ ਦੇਵੇਗਾ।",
        disclaimer: "ਇਹ ਫ਼ੈਸਲਾ ਰਾਜ-ਵਾਰ ਨਿਯਮਾਂ ਅਤੇ ਮਸ਼ੀਨ ਲਰਨਿੰਗ 'ਤੇ ਆਧਾਰਿਤ ਹੈ।",
        irrigate: "ਸਿੰਚਾਈ ਕਰੋ — ਪਾਣੀ ਦੀ ਲੋੜ ਹੈ",
        monitor: "ਨਿਗਰਾਨੀ ਰੱਖੋ — ਹਾਲੇ ਪਾਣੀ ਨਾ ਦਿਓ",
        noIrrigate: "ਸਿੰਚਾਈ ਨਾ ਕਰੋ — ਪਾਣੀ ਕਾਫ਼ੀ ਹੈ",
        probability: "ਸਿੰਚਾਈ ਦੀ ਲੋੜ ਦੀ ਸੰਭਾਵਨਾ",
        loading: "ਨਿਯਮਾਂ ਅਤੇ ਮਾਡਲ ਅਨੁਸਾਰ ਜਾਂਚ ਹੋ ਰਹੀ ਹੈ...",
        error: "ਅਨੁਮਾਨ ਨਹੀਂ ਮਿਲਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਜਾਣਕਾਰੀ ਜਾਂਚੋ।",
        modelInfoTitle: "ਮਾਡਲ ਅਤੇ ਡਾਟਾਸੈੱਟ ਵੇਰਵੇ",
        infoCrop: "ਫ਼ਸਲ",
        infoAlgorithm: "ਐਲਗੋਰਿਦਮ",
        infoDataset: "ਡਾਟਾਸੈੱਟ ਸਰੋਤ",
        infoRecords: "ਕੁੱਲ ਰਿਕਾਰਡ",
        infoAccuracy: "ਸ਼ੁੱਧਤਾ",
        infoPrecision: "ਫ਼ੈਸਲੇ ਦਾ ਆਧਾਰ",
        infoDate: "ਸਥਿਤੀ"
    },

    te: {
        title: "స్మార్ట్ సాగునీటి ప్రణాళిక",
        subtitle: "మెరుగైన వ్యవసాయం కోసం సులభమైన సహాయం",
        languageLabel: "భాషను ఎంచుకోండి",
        welcome: "మీ పొలం పరిస్థితిని తనిఖీ చేద్దాం",
        intro: "మీ పంట మరియు సెన్సార్ రీడింగులను నమోదు చేయండి.",
        formTitle: "పంట మరియు నేల వివరాలు",
        stateLabel: "దశ 1: రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతాన్ని ఎంచుకోండి",
        cropLabel: "దశ 2: పంటను ఎంచుకోండి",
        btnLocation: "గుర్తించు",
        daysLabel: "పంట వయస్సు (రోజులు)",
        moistureLabel: "నేల తేమ శాతం (ఫీల్డ్ కెపాసిటీ %)",
        moistureHelp: "సెన్సార్ రీడింగ్‌ను నమోదు చేయండి (0 - 100%).",
        moistureRiceLabel: "వరి నీటి మట్టం (సెం.మీ)",
        moistureRiceHelp: "నేల ఉపరితలం ప్రకారం నీటి మట్టం (-25 నుండి +5 సెం.మీ).",
        soilTempLabel: "నేల ఉష్ణోగ్రత",
        airTempLabel: "గాలి ఉష్ణోగ్రత",
        humidityLabel: "సాపేక్ష ఆర్ద్రత",
        rainfall7dLabel: "గడచిన 7 రోజులలో వర్షపాతం (మి.మీ) *",
        rainfall7dHelp: "తప్పనిసరి. 10 మి.మీ లేదా అంతకంటే ఎక్కువ ఉంటే నీరు పెట్టరాదు.",
        forecast24hLabel: "రాబోయే 24 గంటల్లో వర్ష సూచన (మి.మీ)",
        forecast24hHelp: "ఐచ్ఛికం (డిఫాల్ట్ 0 మి.మీ).",
        unitWarning: "మోడల్ అంచనా కోసం ఉష్ణోగ్రత సెల్సియస్‌లోకి మార్చబడుతుంది.",
        predict: "సాగునీటి అవసరాన్ని తనిఖీ చేయండి",
        resultTitle: "మీ ఫలితం",
        resultPlaceholder: "మీ అంచనా ఇక్కడ కనిపిస్తుంది.",
        disclaimer: "ఇది రాష్ట్ర వారీ పంట నియమాలు మరియు మెషిన్ లెర్నింగ్ ఆధారిత ఫలితం.",
        irrigate: "నీరు పెట్టండి — సాగునీరు అవసరం",
        monitor: "పర్యవేక్షించండి — ప్రస్తుతం నీరు అవసరం లేదు",
        noIrrigate: "నీరు పెట్టవద్దు — నేలలో తగినంత తేమ ఉంది",
        probability: "సాగునీటి అవసర సంభావ్యత",
        loading: "నియమాలు మరియు మోడల్ ద్వారా పరిశీలించబడుతోంది...",
        error: "అంచనా పొందలేకపోయాము. దయచేసి వివరాలను సరిచూడండి.",
        modelInfoTitle: "మోడల్ మరియు డేటాసెట్ వివరాలు",
        infoCrop: "ఎంచుకున్న పంట",
        infoAlgorithm: "అల్గారిథమ్",
        infoDataset: "డేటా మూలం",
        infoRecords: "మొత్తం రికార్డులు",
        infoAccuracy: "ఖచ్చితత్వం",
        infoPrecision: "నిర్ణయ మూలం",
        infoDate: "స్థితి"
    }
};

const cropIcons = {
    "rice": "🌾",
    "paddy": "🌾",
    "wheat": "🌾",
    "maize": "🌽",
    "corn": "🌽",
    "cotton": "⚪",
    "sugarcane": "🎋",
    "groundnut": "🥜",
    "groundnuts": "🥜",
    "peanut": "🥜",
    "soybean": "🌱",
    "mustard": "🌼",
    "millets": "🌾",
    "bajra": "🌾",
    "jowar": "🌾",
    "tomato": "🍅",
    "chilli": "🌶️",
    "chili": "🌶️",
    "potato": "🥔",
    "onion": "🧅",
    "banana": "🍌",
    "mango": "🥭",
    "apple": "🍎",
    "tea": "🍵",
    "coffee": "☕",
    "coconut": "🥥",
    "rubber": "🌳",
    "spices": "🌿",
    "vegetables": "🥬",
    "pulses": "🫘",
    "barley": "🌾"
};

// Global state variables
let availableStates = [];
let currentCrops = [];
let selectedCropData = null;

// DOM Elements
const languageSelect = document.getElementById("language");
const stateSelect = document.getElementById("state_select");
const cropSelect = document.getElementById("crop_type");
const btnLocation = document.getElementById("btnDetectLocation");
const cropRangeCard = document.getElementById("cropRangeCard");
const irrigationForm = document.getElementById("irrigationForm");
const predictButton = document.getElementById("predictButton");
const resultBox = document.getElementById("result");
const cropIcon = document.getElementById("cropIcon");

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function getCropIcon(cropName) {
    if (!cropName) return "🌱";
    const lower = cropName.toLowerCase();
    for (const [k, icon] of Object.entries(cropIcons)) {
        if (lower.includes(k)) return icon;
    }
    return "🌱";
}

// ----------------------------------------------------
// Step 1: Load and populate states
// ----------------------------------------------------
async function loadStates() {
    try {
        const response = await fetch("/api/states");
        const data = await response.json();
        availableStates = data.states || [];

        stateSelect.innerHTML = '<option value="">-- Choose your State or UT --</option>';
        availableStates.forEach(state => {
            const opt = document.createElement("option");
            opt.value = state;
            opt.textContent = state;
            stateSelect.appendChild(opt);
        });

        // Default to Punjab for convenience or first state
        if (availableStates.includes("Punjab")) {
            stateSelect.value = "Punjab";
            loadCropsForState("Punjab");
        }
    } catch (err) {
        console.error("Error loading states:", err);
    }
}

// ----------------------------------------------------
// Step 2: Load crops for chosen state
// ----------------------------------------------------
async function loadCropsForState(stateName) {
    if (!stateName) {
        cropSelect.innerHTML = '<option value="">-- Select a state first --</option>';
        cropSelect.disabled = true;
        cropRangeCard.style.display = "none";
        selectedCropData = null;
        return;
    }

    cropSelect.disabled = true;
    cropSelect.innerHTML = '<option value="">Loading crops...</option>';

    try {
        const response = await fetch(`/api/crops?state=${encodeURIComponent(stateName)}`);
        const data = await response.json();
        currentCrops = data.crops || [];

        cropSelect.innerHTML = "";
        currentCrops.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.crop;
            opt.textContent = `${getCropIcon(c.crop)} ${c.label}`;
            cropSelect.appendChild(opt);
        });

        cropSelect.disabled = false;

        // Select first crop by default
        if (currentCrops.length > 0) {
            cropSelect.value = currentCrops[0].crop;
            onCropSelected(currentCrops[0]);
        }
    } catch (err) {
        console.error("Error loading crops:", err);
        cropSelect.innerHTML = '<option value="">Failed to load crops</option>';
    }
}

// ----------------------------------------------------
// Step 3: Display Decision Zones for selected crop
// ----------------------------------------------------
function onCropSelected(cropData) {
    if (!cropData) return;
    selectedCropData = cropData;

    const cropName = cropData.crop;
    const isRice = (cropName === "Rice");
    const stateName = stateSelect.value;
    const trigger = cropData.irrigation_trigger;
    const wetLimit = cropData.no_irrigation_from;
    const unit = cropData.reading_unit;

    if (cropIcon) {
        cropIcon.textContent = getCropIcon(cropName);
    }

    // Step 3 Range Card Update
    cropRangeCard.style.display = "block";
    cropRangeCard.classList.add("has-data");
    setText("rangeCropTitle", `${getCropIcon(cropName)} ${cropData.label} in ${stateName}`);

    const segIrr = document.getElementById("segIrrigate");
    const segMon = document.getElementById("segMonitor");
    const segNoIrr = document.getElementById("segNoIrrigate");

    if (isRice) {
        // Rice: water level -25 to +5 cm (total span 30 cm)
        // Irrigate: -25 to -15 cm (10 cm = 33.3% or 50% visual balance)
        // Do Not Irrigate: -15 to +5 cm (20 cm = 66.7%)
        setText(
            "rangeSummaryText",
            `Irrigate: water level -25 to -15 cm | No need: above -15 to +5 cm (${unit})`
        );
        segIrr.style.width = "40%";
        segIrr.textContent = "IRRIGATE (≤ -15 cm)";
        segMon.style.display = "none";
        segNoIrr.style.width = "60%";
        segNoIrr.textContent = "DO NOT IRRIGATE (> -15 cm)";

        setText("lblMin", "-25 cm");
        setText("lblTrigger", "-15 cm (Trigger)");
        setText("lblWetLimit", "");
        setText("lblMax", "+5 cm");
    } else {
        // Normal crops: 0 to 100% of field capacity
        const irrPct = Math.max(10, Math.min(80, trigger));
        const monPct = Math.max(10, Math.min(80, wetLimit - trigger));
        const noIrrPct = Math.max(10, 100 - wetLimit);

        setText(
            "rangeSummaryText",
            `Irrigate: 0–${trigger}% | Monitor: ${trigger}–${wetLimit}% | No need: ${wetLimit}–100% (${unit})`
        );
        segIrr.style.width = `${irrPct}%`;
        segIrr.textContent = `IRRIGATE (≤ ${trigger}%)`;
        segMon.style.display = "flex";
        segMon.style.width = `${monPct}%`;
        segMon.textContent = `MONITOR (${trigger}–${wetLimit}%)`;
        segNoIrr.style.width = `${noIrrPct}%`;
        segNoIrr.textContent = `DO NOT IRRIGATE (≥ ${wetLimit}%)`;

        setText("lblMin", "0%");
        setText("lblTrigger", `${trigger}% (Trigger)`);
        setText("lblWetLimit", `${wetLimit}% (Wet)`);
        setText("lblMax", "100%");
    }

    // Step 4: Adapt sensor reading input label and range
    const readingLabel = document.getElementById("sensorReadingLabel");
    const readingInput = document.getElementById("soil_moisture");
    const readingHelp = document.getElementById("sensorReadingHelp");
    const readingSuffix = document.getElementById("sensorReadingSuffix");
    const readingIcon = document.getElementById("sensorReadingIcon");

    const lang = languageSelect ? languageSelect.value : "en";
    const dict = translations[lang] || translations.en;

    if (isRice) {
        if (readingLabel) readingLabel.textContent = dict.moistureRiceLabel || "Water level (cm relative to soil surface, -25 to +5)";
        if (readingInput) {
            readingInput.min = "-25";
            readingInput.max = "5";
            readingInput.placeholder = "e.g. -12.0";
        }
        if (readingHelp) readingHelp.textContent = dict.moistureRiceHelp || "Enter water level relative to soil surface (-25 to +5 cm).";
        if (readingSuffix) readingSuffix.textContent = "cm";
        if (readingIcon) readingIcon.textContent = "📏";
    } else {
        if (readingLabel) readingLabel.textContent = dict.moistureLabel || "Soil moisture (% of field capacity, 0-100)";
        if (readingInput) {
            readingInput.min = "0";
            readingInput.max = "100";
            readingInput.placeholder = "e.g. 35.0";
        }
        if (readingHelp) readingHelp.textContent = dict.moistureHelp || "Enter sensor reading (0 - 100% of field capacity).";
        if (readingSuffix) readingSuffix.textContent = "%";
        if (readingIcon) readingIcon.textContent = "🪴";
    }

    // Update Model info card specifications
    setText("infoCropName", `${cropData.label} (${stateName})`);
    setText("infoDataset", `India Ranges (${cropData.source || "Official"})`);
}

// ----------------------------------------------------
// Event Listeners for State & Crop
// ----------------------------------------------------
if (stateSelect) {
    stateSelect.addEventListener("change", () => {
        loadCropsForState(stateSelect.value);
    });
}

if (cropSelect) {
    cropSelect.addEventListener("change", () => {
        const found = currentCrops.find(c => c.crop === cropSelect.value);
        if (found) onCropSelected(found);
    });
}

// Geolocation guess
if (btnLocation) {
    btnLocation.addEventListener("click", () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser.");
            return;
        }
        btnLocation.textContent = "Locating...";
        navigator.geolocation.getCurrentPosition(
            () => {
                // If location permitted, default to Punjab or keep current
                if (!stateSelect.value && availableStates.includes("Punjab")) {
                    stateSelect.value = "Punjab";
                    loadCropsForState("Punjab");
                }
                btnLocation.innerHTML = '<span>📍</span> <span>Detected</span>';
            },
            () => {
                btnLocation.innerHTML = '<span>📍</span> <span>Detect</span>';
                alert("Could not detect exact location. Please select your State from the dropdown.");
            },
            { timeout: 6000 }
        );
    });
}

// ----------------------------------------------------
// Multi-Unit Conversion Helper
// ----------------------------------------------------
function toCelsius(value, unit) {
    if (unit === "F") return (value - 32) * 5 / 9;
    if (unit === "K") return value - 273.15;
    return value;
}

function updateSensorCards() {
    const moisture = document.getElementById("soil_moisture") ? document.getElementById("soil_moisture").value : "";
    const airTemperature = document.getElementById("temperature") ? document.getElementById("temperature").value : "";
    const airUnit = document.getElementById("air_temp_unit") ? document.getElementById("air_temp_unit").value : "C";
    const humidity = document.getElementById("humidity") ? document.getElementById("humidity").value : "";

    const isRice = selectedCropData && selectedCropData.crop === "Rice";
    const unitSuffix = isRice ? " cm" : "%";

    setText("heroMoisture", moisture !== "" ? `${moisture}${unitSuffix}` : "--");

    if (airTemperature !== "") {
        const celsius = toCelsius(Number(airTemperature), airUnit);
        setText("heroTemperature", `${celsius.toFixed(1)} °C`);
    } else {
        setText("heroTemperature", "-- °C");
    }

    setText("heroHumidity", humidity !== "" ? `${humidity}%` : "--%");
}

["soil_moisture", "temperature", "air_temp_unit", "humidity"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener("input", updateSensorCards);
        el.addEventListener("change", updateSensorCards);
    }
});

// ----------------------------------------------------
// Form Submission: Execute Prediction & Rule Decision
// ----------------------------------------------------
if (irrigationForm) {
    irrigationForm.addEventListener("submit", async event => {
        event.preventDefault();

        const language = languageSelect ? languageSelect.value : "en";
        const text = translations[language] || translations.en;

        const stateVal = stateSelect ? stateSelect.value : "";
        const cropVal = cropSelect ? cropSelect.value : "";

        if (!stateVal) {
            alert("Please select a State or Union Territory first.");
            return;
        }
        if (!cropVal) {
            alert("Please select a Crop first.");
            return;
        }

        const value = id => Number(document.getElementById(id).value);

        const payload = {
            state: stateVal,
            crop: cropVal,
            crop_age_days: value("crop_days"),
            sensor_reading: value("soil_moisture"),
            soil_temp: value("soil_temperature"),
            soil_temp_unit: document.getElementById("soil_temp_unit").value,
            air_temp: value("temperature"),
            air_temp_unit: document.getElementById("air_temp_unit").value,
            humidity: value("humidity"),
            rainfall_7d: value("rainfall_7d"),
            forecast_24h: document.getElementById("forecast_24h").value !== "" ? value("forecast_24h") : 0.0,
        };

        predictButton.disabled = true;
        resultBox.textContent = text.loading;
        setText("predictionTitle", text.loading);
        setText("predictionDescription", "Evaluating field sensor telemetry against decision zones...");
        setText("statusIcon", "⏳");

        const banner = document.getElementById("predictionBanner");
        if (banner) {
            banner.classList.remove("status-irrigate", "status-monitor", "status-no-irrigate");
        }

        const bar = document.getElementById("probabilityBar");
        const probabilityValue = document.getElementById("probabilityValue");
        const track = document.getElementById("probabilityTrack");
        const ruleAlert = document.getElementById("ruleOverrideAlert");
        const gaugeCard = document.getElementById("resultGaugeCard");

        if (bar) bar.style.width = "0%";
        if (probabilityValue) probabilityValue.textContent = "--%";
        if (track) track.setAttribute("aria-valuenow", "0");
        if (ruleAlert) ruleAlert.style.display = "none";
        if (gaugeCard) gaugeCard.style.display = "none";

        try {
            const response = await fetch("/predict", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || text.error);
            }

            const status = data.status; // "IRRIGATE", "MONITOR", or "DO NOT IRRIGATE"
            const needsIrrigation = (status === "IRRIGATE");
            const isMonitor = (status === "MONITOR");

            // Probability from ML
            const probability = Math.max(0, Math.min(100, Number(data.confidence_pct || 0)));

            // 1. Status Banner Update
            let statusTitle = text.noIrrigate;
            let statusIconEmoji = "🌿";

            if (needsIrrigation) {
                statusTitle = text.irrigate;
                statusIconEmoji = "💧";
            } else if (isMonitor) {
                statusTitle = text.monitor;
                statusIconEmoji = "🔍";
            }

            setText("predictionTitle", statusTitle);
            setText("predictionDescription", data.reason || text.noDescription);
            setText("statusIcon", statusIconEmoji);

            if (banner) {
                banner.classList.remove("status-irrigate", "status-monitor", "status-no-irrigate");
                if (needsIrrigation) {
                    banner.classList.add("status-irrigate");
                } else if (isMonitor) {
                    banner.classList.add("status-monitor");
                } else {
                    banner.classList.add("status-no-irrigate");
                }
            }

            // 2. Rule Override Alert
            if (data.rule_override && ruleAlert) {
                ruleAlert.style.display = "flex";
                setText(
                    "ruleOverrideText",
                    `Range rule priority applied: Ranges CSV dictates "${status}", overriding raw ML classification.`
                );
            }

            // 3. Zone Gauge / Marker Update
            if (gaugeCard && selectedCropData) {
                gaugeCard.style.display = "block";
                const isRice = (selectedCropData.crop === "Rice");
                const reading = Number(data.sensor_reading);
                const trigger = Number(selectedCropData.irrigation_trigger);
                const wetLimit = Number(selectedCropData.no_irrigation_from);

                const gSegIrr = document.getElementById("gaugeSegIrrigate");
                const gSegMon = document.getElementById("gaugeSegMonitor");
                const gSegNoIrr = document.getElementById("gaugeSegNoIrrigate");
                const pointer = document.getElementById("gaugePointer");
                const pointerLabel = document.getElementById("gaugePointerLabel");

                let pointerPct = 0;

                if (isRice) {
                    // -25 to +5 cm
                    setText("gaugeReadingText", `Paddy Water Level: ${reading.toFixed(1)} cm`);
                    gSegIrr.style.width = "40%";
                    gSegIrr.textContent = "IRRIGATE (≤ -15 cm)";
                    gSegMon.style.display = "none";
                    gSegNoIrr.style.width = "60%";
                    gSegNoIrr.textContent = "DO NOT IRRIGATE (> -15 cm)";

                    setText("gaugeLblMin", "-25 cm");
                    setText("gaugeLblTrigger", "-15 cm");
                    setText("gaugeLblWetLimit", "");
                    setText("gaugeLblMax", "+5 cm");

                    pointerPct = Math.max(0, Math.min(100, ((reading - (-25)) / (5 - (-25))) * 100));
                    if (pointerLabel) pointerLabel.textContent = `${reading.toFixed(1)} cm`;
                } else {
                    setText("gaugeReadingText", `Soil Moisture: ${reading.toFixed(1)}%`);
                    const irrW = Math.max(10, Math.min(80, trigger));
                    const monW = Math.max(10, Math.min(80, wetLimit - trigger));
                    const noIrrW = Math.max(10, 100 - wetLimit);

                    gSegIrr.style.width = `${irrW}%`;
                    gSegIrr.textContent = `IRRIGATE (≤ ${trigger}%)`;
                    gSegMon.style.display = "flex";
                    gSegMon.style.width = `${monW}%`;
                    gSegMon.textContent = `MONITOR (${trigger}–${wetLimit}%)`;
                    gSegNoIrr.style.width = `${noIrrW}%`;
                    gSegNoIrr.textContent = `DO NOT IRRIGATE (≥ ${wetLimit}%)`;

                    setText("gaugeLblMin", "0%");
                    setText("gaugeLblTrigger", `${trigger}%`);
                    setText("gaugeLblWetLimit", `${wetLimit}%`);
                    setText("gaugeLblMax", "100%");

                    pointerPct = Math.max(0, Math.min(100, reading));
                    if (pointerLabel) pointerLabel.textContent = `${reading.toFixed(1)}%`;
                }

                if (pointer) {
                    requestAnimationFrame(() => {
                        pointer.style.left = `${pointerPct}%`;
                    });
                }
            }

            // 4. Progress Bar
            if (probabilityValue) probabilityValue.textContent = `${probability.toFixed(1)}%`;
            if (bar) {
                requestAnimationFrame(() => {
                    bar.style.width = `${probability}%`;
                });
            }
            if (track) track.setAttribute("aria-valuenow", probability.toFixed(1));

            // 5. Result box disclaimer
            resultBox.textContent = data.disclaimer || text.disclaimer;

            // 6. Update Model specifications card
            if (data.model_info) {
                const info = data.model_info;
                setText("infoAlgorithm", info.algorithm || "--");
                setText("infoDataset", info.dataset_source || "--");
                setText("infoBadgeText", info.badge_text || "Trained on state-wise crop irrigation dataset (synthetic rule-based)");
                if (info.records_count) setText("infoRecords", `${info.records_count.toLocaleString()} records`);
            }

            updateSensorCards();

            // 7. Save prediction to history and global window cache
            const cropNameSelected = selectedCropData ? selectedCropData.crop : (cropSelect && cropSelect.selectedIndex >= 0 ? cropSelect.options[cropSelect.selectedIndex]?.text : "");
            const historyItem = {
                id: Date.now(),
                timestamp: new Date().toISOString(),
                dateStr: new Date().toLocaleString(),
                state: stateSelect ? stateSelect.value : "",
                crop: cropNameSelected,
                reading: data.sensor_reading,
                unit: selectedCropData && selectedCropData.crop === "Rice" ? "cm" : "%",
                status: status,
                confidence: probability,
                reason: data.reason || "",
                rule_override: data.rule_override || false
            };

            window.lastPredictionResult = historyItem;
            savePredictionToHistory(historyItem);

            // 8. Smart Irrigation Recommendation & Scheduler Update
            if (status === "IRRIGATE") {
                const schedules = data.schedules && data.schedules.length > 0 ? data.schedules : [];
                updateSchedulerUI(schedules, data.water_requirement_liters || 450.0);
            } else {
                showNoIrrigationUI(data.reason || data.no_irrigation_reason);
            }

        } catch (error) {
            setText("predictionTitle", text.error);
            setText("predictionDescription", error.message || text.error);
            setText("statusIcon", "⚠️");
            resultBox.textContent = error.message || text.error;
        } finally {
            predictButton.disabled = false;
        }
    });
}

// ----------------------------------------------------
// Language Switcher
// ----------------------------------------------------
function setLanguage(lang) {
    const dictionary = translations[lang] || translations.en;
    document.documentElement.lang = lang;

    document.querySelectorAll("[data-i18n]").forEach(el => {
        const key = el.dataset.i18n;
        if (dictionary[key]) {
            el.textContent = dictionary[key];
        }
    });

    if (selectedCropData) {
        onCropSelected(selectedCropData);
    }
}

if (languageSelect) {
    languageSelect.addEventListener("change", () => {
        setLanguage(languageSelect.value);
    });
}

// ----------------------------------------------------
// Prediction History Management
// ----------------------------------------------------
function getPredictionHistoryKey() {
    const fid = (window.currentFarmer && window.currentFarmer.id) ? window.currentFarmer.id : "guest";
    return `agri_prediction_history_${fid}`;
}

function getPredictionHistory() {
    try {
        const stored = localStorage.getItem(getPredictionHistoryKey());
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function savePredictionToHistory(item) {
    try {
        const history = getPredictionHistory();
        history.unshift(item);
        if (history.length > 30) history.pop();
        localStorage.setItem(getPredictionHistoryKey(), JSON.stringify(history));
    } catch (e) {
        console.warn("Failed to persist prediction history:", e);
    }
}

function renderPredictionHistory() {
    const container = document.getElementById("predictionHistoryContent");
    if (!container) return;

    const history = getPredictionHistory();
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="history-empty-notice">
                <span style="font-size: 28px; display: block; margin-bottom: 8px;">🌱</span>
                <strong>No predictions recorded yet.</strong>
                <p>Run your first irrigation check to see historical recommendations here.</p>
            </div>
        `;
        return;
    }

    let rowsHtml = history.map(item => {
        let badgeClass = "no-irrigate";
        let badgeLabel = "DO NOT IRRIGATE";
        if (item.status === "IRRIGATE") {
            badgeClass = "irrigate";
            badgeLabel = "IRRIGATE";
        } else if (item.status === "MONITOR") {
            badgeClass = "monitor";
            badgeLabel = "MONITOR";
        }

        const readingDisplay = typeof item.reading === "number" ? item.reading.toFixed(1) : item.reading;

        return `
            <tr>
                <td><strong>${item.dateStr || "Recent"}</strong></td>
                <td>${item.state || "--"}</td>
                <td><strong>${item.crop || "--"}</strong></td>
                <td>${readingDisplay} ${item.unit || "%"}</td>
                <td><span class="history-badge ${badgeClass}">${badgeLabel}</span></td>
                <td><small style="color: #475569;">${item.reason || "--"}</small></td>
            </tr>
        `;
    }).join("");

    container.innerHTML = `
        <div style="overflow-x: auto;">
            <table class="history-table">
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>State</th>
                        <th>Crop</th>
                        <th>Reading</th>
                        <th>Decision</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>
                    ${rowsHtml}
                </tbody>
            </table>
        </div>
    `;
}

function openPredictionHistory() {
    const modal = document.getElementById("predictionHistoryModal");
    if (!modal) return;
    renderPredictionHistory();
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");
}

function closePredictionHistory() {
    const modal = document.getElementById("predictionHistoryModal");
    if (!modal) return;
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
}

function clearAllPredictionHistory() {
    if (confirm("Are you sure you want to clear your prediction history?")) {
        localStorage.removeItem(getPredictionHistoryKey());
        renderPredictionHistory();
    }
}

// Bind History Modal Controls
const btnViewHistory = document.getElementById("btnViewHistory");
if (btnViewHistory) {
    btnViewHistory.addEventListener("click", openPredictionHistory);
}

const historyModalCloseBtn = document.getElementById("historyModalCloseBtn");
if (historyModalCloseBtn) {
    historyModalCloseBtn.addEventListener("click", closePredictionHistory);
}

const closePredictionHistoryBtn = document.getElementById("closePredictionHistoryBtn");
if (closePredictionHistoryBtn) {
    closePredictionHistoryBtn.addEventListener("click", closePredictionHistory);
}

const historyModalBackdrop = document.getElementById("historyModalBackdrop");
if (historyModalBackdrop) {
    historyModalBackdrop.addEventListener("click", closePredictionHistory);
}

const clearPredictionHistoryBtn = document.getElementById("clearPredictionHistoryBtn");
if (clearPredictionHistoryBtn) {
    clearPredictionHistoryBtn.addEventListener("click", clearAllPredictionHistory);
}

// ----------------------------------------------------
// Global Helpers for Website Control & Voice Commands
// ----------------------------------------------------
window.openPredictionHistory = openPredictionHistory;
window.closePredictionHistory = closePredictionHistory;

window.scrollToIrrigationPlanner = function() {
    const plannerEl = document.getElementById("irrigation-planner") || document.getElementById("irrigationForm");
    if (plannerEl) {
        plannerEl.scrollIntoView({ behavior: "smooth", block: "start" });
        plannerEl.classList.add("planner-highlight");
        setTimeout(() => plannerEl.classList.remove("planner-highlight"), 1600);
        const stateEl = document.getElementById("state_select");
        if (stateEl) stateEl.focus();
        return true;
    }
    return false;
};

window.selectStateByName = async function(stateName) {
    if (!stateSelect) return false;
    const cleanQuery = stateName.trim().toLowerCase();
    
    // Look for exact or partial match
    let matchedOption = Array.from(stateSelect.options).find(opt => 
        opt.value.toLowerCase() === cleanQuery || 
        opt.text.toLowerCase() === cleanQuery ||
        opt.value.toLowerCase().includes(cleanQuery)
    );

    if (matchedOption && matchedOption.value) {
        stateSelect.value = matchedOption.value;
        await loadCropsForState(matchedOption.value);
        return matchedOption.value;
    }
    return false;
};

window.selectCropByName = function(cropName) {
    if (!cropSelect) return false;
    const cleanQuery = cropName.trim().toLowerCase();

    let matchedOption = Array.from(cropSelect.options).find(opt => 
        opt.text.toLowerCase() === cleanQuery || 
        opt.value.toLowerCase() === cleanQuery ||
        opt.text.toLowerCase().includes(cleanQuery)
    );

    if (matchedOption && matchedOption.value) {
        cropSelect.value = matchedOption.value;
        const cropData = currentCrops.find(c => String(c.id) === matchedOption.value || c.crop.toLowerCase() === cleanQuery);
        if (cropData) {
            onCropSelected(cropData);
        }
        return matchedOption.text;
    }
    return false;
};

window.triggerPrediction = function() {
    if (!irrigationForm) return { success: false, reason: "Form not found" };

    const stateVal = stateSelect ? stateSelect.value : "";
    const cropVal = cropSelect ? cropSelect.value : "";
    const moistureEl = document.getElementById("soil_moisture");
    const rainfallEl = document.getElementById("rainfall_7d");

    if (!stateVal) return { success: false, missing: "state", message: "Please select a State or UT first." };
    if (!cropVal) return { success: false, missing: "crop", message: "Please select a Crop first." };
    if (!moistureEl || moistureEl.value === "") return { success: false, missing: "moisture", message: "Please enter soil moisture or water level." };
    if (!rainfallEl || rainfallEl.value === "") return { success: false, missing: "rainfall", message: "Please enter recent 7-day rainfall." };

    if (predictButton && predictButton.disabled) {
        return { success: false, message: "Prediction is currently processing. Please wait." };
    }

    if (predictButton) {
        predictButton.click();
        return { success: true, message: `Running prediction for ${cropSelect.options[cropSelect.selectedIndex]?.text} in ${stateVal}...` };
    }
    return { success: false, message: "Prediction button not found." };
};

// Initial bootstrap
loadStates();

// ========================================================
// AI Smart Irrigation Dual Synchronized Calendar & Scheduler Module
// ========================================================
let appSchedules = [];
let activeScheduleIdx = 0;
let calCurrentYear = new Date().getFullYear();
let calCurrentMonth = new Date().getMonth(); // 0-indexed
let selectedDateStr = null;

// Calendar 1: Main Irrigation Calendar DOM Elements
const mainSchedCalendar = document.getElementById("mainSchedCalendar");
const mainCalPrevBtn = document.getElementById("mainCalPrevBtn");
const mainCalNextBtn = document.getElementById("mainCalNextBtn");
const mainCalMonthYear = document.getElementById("mainCalMonthYear");
const mainCalDaysGrid = document.getElementById("mainCalDaysGrid");

// Calendar 2: Mini Calendar Popup DOM Elements
const btnMiniCalToggle = document.getElementById("btnMiniCalendarToggle");
const miniCalPopup = document.getElementById("miniCalendarPopup");
const miniCalPrevBtn = document.getElementById("miniCalPrevBtn");
const miniCalNextBtn = document.getElementById("miniCalNextBtn");
const miniCalCloseBtn = document.getElementById("miniCalCloseBtn");
const miniCalMonthYear = document.getElementById("miniCalMonthYear");
const miniCalDaysGrid = document.getElementById("miniCalDaysGrid");
const miniCalSelectedDetail = document.getElementById("miniCalSelectedDetail");
const calBadgeCount = document.getElementById("calBadgeCount");

// Cards & Header KPI
const smartSchedulerCard = document.getElementById("smartSchedulerCard");
const noIrrigationCard = document.getElementById("noIrrigationCard");
const noIrrigationReason = document.getElementById("noIrrigationReason");
const schedWaterReqVal = document.getElementById("schedWaterReqVal");

// Date-Wise Details Panel Elements
const schedActiveSessionBox = document.getElementById("schedActiveSessionBox");
const schedSelectedDateTag = document.getElementById("schedSelectedDateTag");
const schedRelativeTimeLabel = document.getElementById("schedRelativeTimeLabel");
const schedSessionCrop = document.getElementById("schedSessionCrop");
const schedSessionTime = document.getElementById("schedSessionTime");
const schedSessionWater = document.getElementById("schedSessionWater");
const schedSessionDuration = document.getElementById("schedSessionDuration");
const schedSessionWeather = document.getElementById("schedSessionWeather");
const schedSessionStatus = document.getElementById("schedSessionStatus");
const schedSessionReason = document.getElementById("schedSessionReason");

// Action Buttons
const btnMarkCompleted = document.getElementById("btnMarkCompleted");
const btnSkipSession = document.getElementById("btnSkipSession");
const btnWhySchedule = document.getElementById("btnWhySchedule");
const schedWhyExplanation = document.getElementById("schedWhyExplanation");

const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
];

// Helper: Format Date String YYYY-MM-DD -> "November 15, 2026"
function formatDateDisplay(dateStr) {
    if (!dateStr) return "--";
    const parts = dateStr.split("-");
    if (parts.length === 3) {
        const d = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
        return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
    }
    return dateStr;
}

// Helper: Relative label e.g. "Today's session", "Tomorrow's session"
function getRelativeDateLabel(dateStr) {
    if (!dateStr) return "Scheduled session";
    const parts = dateStr.split("-");
    if (parts.length !== 3) return "Scheduled session";
    const target = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffDays = Math.round((target - today) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today's session";
    if (diffDays === 1) return "Tomorrow's session";
    if (diffDays > 1) return `Upcoming in ${diffDays} days`;
    if (diffDays === -1) return "Yesterday's session";
    return `Past session (${Math.abs(diffDays)} days ago)`;
}

// Helper: Weather summary string
function getWeatherSummaryForDate(session) {
    if (!session) return "Clear / Forecast Dry (0.0 mm)";
    const r = (session.reason || "").toLowerCase();
    if (r.includes("rain") || r.includes("mm")) {
        return "Rain Forecast Detected (Adjusted)";
    }
    return "Clear / Forecast Dry (0.0 mm)";
}

// Update the pending badge on Calendar 2 toggle icon
function updatePendingBadge() {
    const pendingCount = appSchedules.filter(s => s.status !== "Completed" && s.status !== "Skipped").length;
    if (calBadgeCount) {
        if (pendingCount > 0) {
            calBadgeCount.textContent = pendingCount;
            calBadgeCount.style.display = "inline-block";
        } else {
            calBadgeCount.style.display = "none";
        }
    }
}

// Toggle Calendar 2 Popup
function toggleMiniCalendar(forceState) {
    if (!miniCalPopup) return;
    const isHidden = miniCalPopup.style.display === "none" || !miniCalPopup.style.display;
    const shouldOpen = typeof forceState === "boolean" ? forceState : isHidden;
    miniCalPopup.style.display = shouldOpen ? "block" : "none";
    if (btnMiniCalToggle) {
        btnMiniCalToggle.setAttribute("aria-expanded", shouldOpen ? "true" : "false");
    }
    if (shouldOpen) {
        renderDualCalendars();
    }
}

// Close mini calendar on outside click
document.addEventListener("click", (e) => {
    if (!miniCalPopup || miniCalPopup.style.display === "none") return;
    if (btnMiniCalToggle && btnMiniCalToggle.contains(e.target)) return;
    if (!miniCalPopup.contains(e.target)) {
        toggleMiniCalendar(false);
    }
});

if (btnMiniCalToggle) {
    btnMiniCalToggle.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleMiniCalendar();
    });
}

if (miniCalCloseBtn) {
    miniCalCloseBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        toggleMiniCalendar(false);
    });
}

// Synchronized month navigation
function changeCalendarMonth(delta) {
    calCurrentMonth += delta;
    if (calCurrentMonth < 0) {
        calCurrentMonth = 11;
        calCurrentYear--;
    } else if (calCurrentMonth > 11) {
        calCurrentMonth = 0;
        calCurrentYear++;
    }
    renderDualCalendars();
}

if (mainCalPrevBtn) mainCalPrevBtn.addEventListener("click", () => changeCalendarMonth(-1));
if (mainCalNextBtn) mainCalNextBtn.addEventListener("click", () => changeCalendarMonth(1));
if (miniCalPrevBtn) miniCalPrevBtn.addEventListener("click", () => changeCalendarMonth(-1));
if (miniCalNextBtn) miniCalNextBtn.addEventListener("click", () => changeCalendarMonth(1));

// Render Both Calendars (100% Synchronized)
function renderDualCalendars() {
    const titleText = `${MONTH_NAMES[calCurrentMonth]} ${calCurrentYear}`;
    if (mainCalMonthYear) mainCalMonthYear.textContent = titleText;
    if (miniCalMonthYear) miniCalMonthYear.textContent = titleText;

    if (mainCalDaysGrid) mainCalDaysGrid.innerHTML = "";
    if (miniCalDaysGrid) miniCalDaysGrid.innerHTML = "";

    const today = new Date();
    const firstDayIndex = new Date(calCurrentYear, calCurrentMonth, 1).getDay();
    const totalDays = new Date(calCurrentYear, calCurrentMonth + 1, 0).getDate();

    // Leading empty cells
    for (let i = 0; i < firstDayIndex; i++) {
        if (mainCalDaysGrid) {
            const emptyMain = document.createElement("div");
            emptyMain.className = "cal-day-cell empty-cell";
            mainCalDaysGrid.appendChild(emptyMain);
        }
        if (miniCalDaysGrid) {
            const emptyMini = document.createElement("div");
            emptyMini.className = "mini-cal-day-cell empty-cell";
            miniCalDaysGrid.appendChild(emptyMini);
        }
    }

    // Days 1..totalDays
    for (let day = 1; day <= totalDays; day++) {
        const dateIso = `${calCurrentYear}-${String(calCurrentMonth + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const isToday = (
            day === today.getDate() &&
            calCurrentMonth === today.getMonth() &&
            calCurrentYear === today.getFullYear()
        );
        const isSelected = (selectedDateStr === dateIso);

        const daySessions = appSchedules.filter(s => s.irrigation_date === dateIso);

        // Status determination
        // Completed -> GREEN
        // Upcoming / Pending / Rescheduled -> BLUE
        // Skipped -> RED
        // None -> GREY
        let statusKey = "none";
        let mainBadge = "";
        let miniBadge = "";
        let tooltip = `No irrigation scheduled for ${formatDateDisplay(dateIso)}`;

        const completedSess = daySessions.find(s => s.status === "Completed");
        const activeSess = daySessions.find(s => ["Upcoming", "Pending", "Rescheduled"].includes(s.status));
        const skippedSess = daySessions.find(s => s.status === "Skipped");

        if (completedSess) {
            statusKey = "completed";
            mainBadge = `<span class="cal-day-indicator">✓ Done</span>`;
            miniBadge = `<span class="mini-cal-drop" title="Completed">✓</span>`;
            tooltip = `Irrigation Completed: ${completedSess.crop} (${completedSess.water_quantity_liters} L)`;
        } else if (activeSess) {
            statusKey = "upcoming";
            const qty = Math.round(activeSess.water_quantity_liters || 450);
            mainBadge = `<span class="cal-day-indicator">💧 ${qty}L</span>`;
            miniBadge = `<span class="mini-cal-drop" title="Irrigation Required">💧</span>`;
            tooltip = `Irrigation Required (${activeSess.status}): ${activeSess.crop} (${qty} L at ${activeSess.recommended_time})`;
        } else if (skippedSess) {
            statusKey = "skipped";
            mainBadge = `<span class="cal-day-indicator">✕ Skip</span>`;
            miniBadge = `<span class="mini-cal-drop" title="Skipped">✕</span>`;
            tooltip = `Irrigation Skipped: ${skippedSess.crop}`;
        }

        // Calendar 1: Main Cell
        if (mainCalDaysGrid) {
            const mainCell = document.createElement("div");
            mainCell.className = `cal-day-cell cell-${statusKey}`;
            if (isToday) mainCell.classList.add("is-today");
            if (isSelected) mainCell.classList.add("is-selected");
            mainCell.title = tooltip;
            mainCell.dataset.date = dateIso;

            mainCell.innerHTML = `
                <span class="cal-day-num">${day}</span>
                ${mainBadge}
            `;

            mainCell.addEventListener("click", () => {
                selectDate(dateIso);
            });
            mainCalDaysGrid.appendChild(mainCell);
        }

        // Calendar 2: Mini Cell
        if (miniCalDaysGrid) {
            const miniCell = document.createElement("div");
            miniCell.className = `mini-cal-day-cell cell-${statusKey}`;
            if (isToday) miniCell.classList.add("is-today");
            if (isSelected) miniCell.classList.add("is-selected");
            miniCell.title = tooltip;
            miniCell.dataset.date = dateIso;

            if (statusKey !== "none") {
                miniCell.classList.add("has-irrigation");
                miniCell.innerHTML = `<span>${day}</span>${miniBadge}`;
            } else {
                miniCell.innerHTML = `<span>${day}</span>`;
            }

            miniCell.addEventListener("click", () => {
                selectDate(dateIso);
            });
            miniCalDaysGrid.appendChild(miniCell);
        }
    }
}

// Date-Wise Selection Handler (updates both calendars & details panel)
function selectDate(dateIso) {
    if (!dateIso) return;
    selectedDateStr = dateIso;

    // Update active highlight on all cells without rebuilding
    document.querySelectorAll(".cal-day-cell, .mini-cal-day-cell").forEach(el => {
        if (el.dataset.date === dateIso) {
            el.classList.add("is-selected");
        } else {
            el.classList.remove("is-selected");
        }
    });

    const matching = appSchedules.filter(s => s.irrigation_date === dateIso);
    const formatted = formatDateDisplay(dateIso);
    const relText = getRelativeDateLabel(dateIso);

    if (matching.length > 0) {
        const sess = matching.find(s => ["Upcoming", "Pending", "Rescheduled"].includes(s.status))
            || matching.find(s => s.status === "Completed")
            || matching[0];

        activeScheduleIdx = appSchedules.indexOf(sess);

        if (schedSelectedDateTag) schedSelectedDateTag.textContent = `Selected Date: ${formatted}`;
        if (schedRelativeTimeLabel) schedRelativeTimeLabel.textContent = relText;
        if (schedSessionCrop) schedSessionCrop.textContent = sess.crop || (selectedCropData ? selectedCropData.crop : "Wheat");
        if (schedSessionTime) schedSessionTime.textContent = sess.recommended_time || "06:00 AM";
        if (schedSessionWater) schedSessionWater.textContent = `${Math.round(sess.water_quantity_liters || 450)} L`;
        if (schedSessionDuration) schedSessionDuration.textContent = `${sess.duration_minutes || 45} mins`;
        if (schedSessionWeather) schedSessionWeather.textContent = getWeatherSummaryForDate(sess);
        if (schedSessionReason) schedSessionReason.textContent = sess.reason || "Recommended based on soil moisture and crop rules.";

        if (schedSessionStatus) {
            schedSessionStatus.textContent = sess.status || "Upcoming";
            schedSessionStatus.className = "sched-status-chip";
            const st = (sess.status || "").toLowerCase();
            if (st === "completed") {
                schedSessionStatus.classList.add("status-completed");
            } else if (st === "skipped") {
                schedSessionStatus.classList.add("status-skipped");
            } else if (st === "rescheduled") {
                schedSessionStatus.classList.add("status-rescheduled");
            } else {
                schedSessionStatus.classList.add("status-upcoming");
            }
        }

        if (btnMarkCompleted) {
            const isComp = (sess.status === "Completed");
            btnMarkCompleted.disabled = isComp;
            btnMarkCompleted.style.opacity = isComp ? "0.6" : "1";
            btnMarkCompleted.innerHTML = isComp 
                ? '<span>✓</span> <span>Completed</span>' 
                : '<span>✓</span> <span>Mark Completed</span>';
            btnMarkCompleted.title = isComp ? "Session already completed" : "Confirm completion of this session";
        }

        if (btnSkipSession) {
            const isSkip = (sess.status === "Skipped");
            const isComp = (sess.status === "Completed");
            btnSkipSession.disabled = isSkip || isComp;
            btnSkipSession.style.opacity = (isSkip || isComp) ? "0.6" : "1";
            btnSkipSession.innerHTML = isSkip 
                ? '<span>✕</span> <span>Skipped</span>' 
                : '<span>✕</span> <span>Skip Irrigation</span>';
            btnSkipSession.title = isSkip ? "Session already skipped" : "Skip this session and let AI reschedule";
        }

        if (miniCalSelectedDetail) {
            miniCalSelectedDetail.style.display = "block";
            const stClass = sess.status.toLowerCase();
            miniCalSelectedDetail.innerHTML = `
                <div class="mini-detail-card">
                    <div class="mini-detail-top">
                        <strong>${formatted}</strong>
                        <span class="sched-status-chip status-${stClass}">${sess.status}</span>
                    </div>
                    <div class="mini-detail-sub">
                        <span>🌾 ${sess.crop}</span> • <span>⏰ ${sess.recommended_time}</span> • <span>🚰 ${Math.round(sess.water_quantity_liters)} L</span>
                    </div>
                </div>
            `;
        }
    } else {
        // Date with no scheduled session
        if (schedSelectedDateTag) schedSelectedDateTag.textContent = `Selected Date: ${formatted}`;
        if (schedRelativeTimeLabel) schedRelativeTimeLabel.textContent = "No session scheduled";
        if (schedSessionCrop) schedSessionCrop.textContent = (selectedCropData ? selectedCropData.crop : "Field");
        if (schedSessionTime) schedSessionTime.textContent = "--";
        if (schedSessionWater) schedSessionWater.textContent = "0 L";
        if (schedSessionDuration) schedSessionDuration.textContent = "--";
        if (schedSessionWeather) schedSessionWeather.textContent = "Optimal Soil Moisture";
        if (schedSessionReason) {
            schedSessionReason.textContent = "No irrigation is scheduled for this date. Soil moisture remains adequate and safe.";
        }

        if (schedSessionStatus) {
            schedSessionStatus.textContent = "No Irrigation";
            schedSessionStatus.className = "sched-status-chip status-none";
        }

        if (btnMarkCompleted) {
            btnMarkCompleted.disabled = true;
            btnMarkCompleted.style.opacity = "0.4";
            btnMarkCompleted.innerHTML = '<span>✓</span> <span>Mark Completed</span>';
            btnMarkCompleted.title = "No irrigation scheduled on this date";
        }
        if (btnSkipSession) {
            btnSkipSession.disabled = true;
            btnSkipSession.style.opacity = "0.4";
            btnSkipSession.innerHTML = '<span>✕</span> <span>Skip Irrigation</span>';
            btnSkipSession.title = "No irrigation scheduled on this date";
        }

        if (miniCalSelectedDetail) {
            miniCalSelectedDetail.style.display = "block";
            miniCalSelectedDetail.innerHTML = `
                <div class="mini-detail-card">
                    <div class="mini-detail-top">
                        <strong>${formatted}</strong>
                        <span class="sched-status-chip status-none">No Irrigation</span>
                    </div>
                    <div class="mini-detail-sub">
                        <span>Optimal soil conditions. No watering required.</span>
                    </div>
                </div>
            `;
        }
    }
}

// Action: Mark Session as Completed (turns GREEN)
async function markCurrentSessionCompleted() {
    if (!appSchedules || appSchedules.length === 0) return;
    const session = appSchedules[activeScheduleIdx];
    if (!session || session.status === "Completed") return;

    try {
        const res = await fetch(`/api/schedules/${session.id}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "Completed" })
        });
        const data = await res.json();
        if (data.status === "success") {
            if (data.schedules) {
                appSchedules = data.schedules;
            } else {
                session.status = "Completed";
            }
            updatePendingBadge();
            renderDualCalendars();
            selectDate(session.irrigation_date);
        }
    } catch (err) {
        console.error("Failed to mark schedule as completed:", err);
    }
}

// Action: Skip Session & Let AI Reschedule (turns RED & BLUE)
async function skipCurrentSession() {
    if (!appSchedules || appSchedules.length === 0) return;
    const session = appSchedules[activeScheduleIdx];
    if (!session || session.status === "Skipped") return;

    try {
        const res = await fetch(`/api/schedules/${session.id}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: "Skipped", skip_reason: "Skipped by farmer" })
        });
        const data = await res.json();
        if (data.status === "success") {
            if (data.schedules) {
                appSchedules = data.schedules;
            } else {
                session.status = "Skipped";
            }
            updatePendingBadge();
            renderDualCalendars();

            const resched = appSchedules.find(s => s.status === "Rescheduled");
            if (resched) {
                selectDate(resched.irrigation_date);
            } else {
                selectDate(session.irrigation_date);
            }
        }
    } catch (err) {
        console.error("Failed to skip session:", err);
    }
}

if (btnMarkCompleted) {
    btnMarkCompleted.addEventListener("click", (e) => {
        e.preventDefault();
        markCurrentSessionCompleted();
    });
}

if (btnSkipSession) {
    btnSkipSession.addEventListener("click", (e) => {
        e.preventDefault();
        skipCurrentSession();
    });
}

if (btnWhySchedule && schedWhyExplanation) {
    btnWhySchedule.addEventListener("click", () => {
        const isHidden = schedWhyExplanation.style.display === "none" || !schedWhyExplanation.style.display;
        schedWhyExplanation.style.display = isHidden ? "block" : "none";
    });
}

// Main Scheduler UI Updater (called after prediction)
function updateSchedulerUI(schedules, waterRequirement) {
    appSchedules = schedules || [];
    activeScheduleIdx = 0;

    if (noIrrigationCard) noIrrigationCard.style.display = "none";
    if (smartSchedulerCard) smartSchedulerCard.style.display = "block";

    if (schedWaterReqVal) {
        const qty = waterRequirement || (appSchedules[0] ? appSchedules[0].water_quantity_liters : 450);
        schedWaterReqVal.textContent = `${Math.round(qty)} L`;
    }

    updatePendingBadge();

    if (appSchedules.length > 0) {
        const firstActive = appSchedules.find(s => ["Upcoming", "Pending", "Rescheduled"].includes(s.status)) || appSchedules[0];
        activeScheduleIdx = appSchedules.indexOf(firstActive);
        selectedDateStr = firstActive.irrigation_date;

        const parts = firstActive.irrigation_date.split("-");
        if (parts.length === 3) {
            calCurrentYear = parseInt(parts[0], 10);
            calCurrentMonth = parseInt(parts[1], 10) - 1;
        }
    }

    renderDualCalendars();
    if (selectedDateStr) {
        selectDate(selectedDateStr);
    }
}

function showNoIrrigationUI(reason) {
    if (smartSchedulerCard) smartSchedulerCard.style.display = "none";
    if (noIrrigationCard) {
        noIrrigationCard.style.display = "flex";
        if (noIrrigationReason) {
            noIrrigationReason.textContent = reason || "No irrigation schedule available yet. Calculate irrigation requirements above to generate a schedule.";
        }
    }
    appSchedules = [];
    updatePendingBadge();
}

// Initial bootstrap of schedules from SQLite
async function initSchedulerFromBackend() {
    try {
        const res = await fetch("/api/schedules");
        if (res.ok) {
            const data = await res.json();
            if (data && data.schedules && data.schedules.length > 0) {
                appSchedules = data.schedules;
                updatePendingBadge();

                if (smartSchedulerCard) {
                    smartSchedulerCard.style.display = "block";
                }
                if (noIrrigationCard) {
                    noIrrigationCard.style.display = "none";
                }

                const firstActive = appSchedules.find(s => ["Upcoming", "Pending", "Rescheduled"].includes(s.status)) || appSchedules[0];
                activeScheduleIdx = appSchedules.indexOf(firstActive);
                selectedDateStr = firstActive.irrigation_date;

                const parts = firstActive.irrigation_date.split("-");
                if (parts.length === 3) {
                    calCurrentYear = parseInt(parts[0], 10);
                    calCurrentMonth = parseInt(parts[1], 10) - 1;
                }

                renderDualCalendars();
                selectDate(selectedDateStr);
            } else {
                showNoIrrigationUI("No irrigation schedule available yet. Calculate irrigation requirements above to generate a schedule.");
            }
        }
    } catch (e) {
        console.warn("Could not fetch existing schedules:", e);
        showNoIrrigationUI("No irrigation schedule available yet. Calculate irrigation requirements above to generate a schedule.");
    }
}

// Global hooks for Voice Assistant & External Controls
window.openMiniCalendar = () => toggleMiniCalendar(true);
window.closeMiniCalendar = () => toggleMiniCalendar(false);
window.refreshSchedulerUI = initSchedulerFromBackend;
window.selectScheduleDate = (dateIso) => selectDate(dateIso);
window.markCurrentSessionCompleted = markCurrentSessionCompleted;
window.skipCurrentSession = skipCurrentSession;
window.rescheduleCurrentSession = skipCurrentSession;

// Initialize on page load
initSchedulerFromBackend();

/* ========================================================
   Phase 1-9: Multi-Farmer & Multi-Land Management Engine
   ======================================================== */

// Global State
window.currentFarmer = null;
window.currentFarm = null;
window.farmSections = [];
window.activeSectionId = null;
window.landSummary = null;
window.liveWeather = null;
window.globalCalYear = new Date().getFullYear();
window.globalCalMonth = new Date().getMonth() + 1;
window.globalCalData = null;

// DOM Elements
const btnGlobalCalendarToggle = document.getElementById("btnGlobalCalendarToggle");
const globalCalBadge = document.getElementById("globalCalBadge");
const farmerAccountBtn = document.getElementById("farmerAccountBtn");
const farmerDropdownMenu = document.getElementById("farmerDropdownMenu");
const farmerNameDisplay = document.getElementById("farmerNameDisplay");
const farmerLocationDisplay = document.getElementById("farmerLocationDisplay");
const dropdownFarmerName = document.getElementById("dropdownFarmerName");
const dropdownFarmerPhone = document.getElementById("dropdownFarmerPhone");
const dropdownFarmerLand = document.getElementById("dropdownFarmerLand");
const dropdownFarmerLocation = document.getElementById("dropdownFarmerLocation");
const dropdownAuthBtn = document.getElementById("dropdownAuthBtn");
const dropdownAuthIcon = document.getElementById("dropdownAuthIcon");
const dropdownAuthLabel = document.getElementById("dropdownAuthLabel");

// Land Banner & Weather
const farmTitleText = document.getElementById("farmTitleText");
const farmAccountBadge = document.getElementById("farmAccountBadge");
const farmLocationText = document.getElementById("farmLocationText");
const btnSwitchFarmerDemo = document.getElementById("btnSwitchFarmerDemo");
const weatherTempDisplay = document.getElementById("weatherTempDisplay");
const weatherConditionDisplay = document.getElementById("weatherConditionDisplay");
const weatherLocationTag = document.getElementById("weatherLocationTag");
const weatherHumidityDisplay = document.getElementById("weatherHumidityDisplay");
const weatherRainDisplay = document.getElementById("weatherRainDisplay");
const weatherForecast24Display = document.getElementById("weatherForecast24Display");
const weatherSoilTempDisplay = document.getElementById("weatherSoilTempDisplay");
const weatherSyncTime = document.getElementById("weatherSyncTime");
const btnRefreshWeather = document.getElementById("btnRefreshWeather");

// Land Stats & Allocation Bar
const landStatTotal = document.getElementById("landStatTotal");
const landStatAllocated = document.getElementById("landStatAllocated");
const landStatAvailable = document.getElementById("landStatAvailable");
const landStatSections = document.getElementById("landStatSections");
const landProgressBar = document.getElementById("landProgressBar");
const landProgressLegend = document.getElementById("landProgressLegend");

// Sections Grid & Planner Context
const sectionsCardsGrid = document.getElementById("sectionsCardsGrid");
const btnAddSectionModalBtn = document.getElementById("btnAddSectionModalBtn");
const activeSectionBanner = document.getElementById("activeSectionBanner");
const activeSecTitle = document.getElementById("activeSecTitle");
const activeSecSub = document.getElementById("activeSecSub");
const activeSecAgeChip = document.getElementById("activeSecAgeChip");
const btnEditCurrentSection = document.getElementById("btnEditCurrentSection");
const sectionAreaFieldWrap = document.getElementById("sectionAreaFieldWrap");
const sectionAreaAcresInput = document.getElementById("section_area_acres");
const sowingDateFieldWrap = document.getElementById("sowingDateFieldWrap");
const sowingDateInput = document.getElementById("sowing_date");
const calculatedCropAgeBadge = document.getElementById("calculatedCropAgeBadge");

// Planning Prompt & Empty Land
const schedPlanPrompt = document.getElementById("schedPlanPrompt");
const schedStartDateInput = document.getElementById("schedStartDateInput");
const schedPeriodSelect = document.getElementById("schedPeriodSelect");
const btnGenerateSectionSchedule = document.getElementById("btnGenerateSectionSchedule");
const emptyLandCard = document.getElementById("emptyLandCard");
const emptyLandSectionName = document.getElementById("emptyLandSectionName");
const emptyLandAreaDisplay = document.getElementById("emptyLandAreaDisplay");
const btnCultivateEmptySection = document.getElementById("btnCultivateEmptySection");

// Modals
const authModal = document.getElementById("authModal");
const authModalCloseBtn = document.getElementById("authModalCloseBtn");
const authModalBackdrop = document.getElementById("authModalBackdrop");
const tabAuthLoginBtn = document.getElementById("tabAuthLoginBtn");
const tabAuthRegisterBtn = document.getElementById("tabAuthRegisterBtn");
const formFarmerLogin = document.getElementById("formFarmerLogin");
const formFarmerRegister = document.getElementById("formFarmerRegister");
const loginFeedback = document.getElementById("loginFeedback");
const registerFeedback = document.getElementById("registerFeedback");
const btnAutoDetectGPS = document.getElementById("btnAutoDetectGPS");
const regState = document.getElementById("regState");
const regDistrict = document.getElementById("regDistrict");
const regVillage = document.getElementById("regVillage");
const regLat = document.getElementById("regLat");
const regLon = document.getElementById("regLon");
const detectedCoordsText = document.getElementById("detectedCoordsText");
const regTotalLand = document.getElementById("regTotalLand");
const regLandUnit = document.getElementById("regLandUnit");
const canonicalAreaHint = document.getElementById("canonicalAreaHint");

const sectionModal = document.getElementById("sectionModal");
const sectionModalCloseBtn = document.getElementById("sectionModalCloseBtn");
const sectionModalBackdrop = document.getElementById("sectionModalBackdrop");
const formSectionManage = document.getElementById("formSectionManage");
const modalSectionTitle = document.getElementById("sectionModalTitle");
const modalSectionId = document.getElementById("modalSectionId");
const modalSectionName = document.getElementById("modalSectionName");
const modalSectionArea = document.getElementById("modalSectionArea");
const modalAreaLimitHint = document.getElementById("modalAreaLimitHint");
const modalIsEmpty = document.getElementById("modalIsEmpty");
const modalCultivatedFields = document.getElementById("modalCultivatedFields");
const modalCropSelect = document.getElementById("modalCropSelect");
const modalCropVariety = document.getElementById("modalCropVariety");
const modalSowingDate = document.getElementById("modalSowingDate");
const modalSoilType = document.getElementById("modalSoilType");
const modalSoilMoisture = document.getElementById("modalSoilMoisture");
const modalSoilTemp = document.getElementById("modalSoilTemp");
const sectionModalFeedback = document.getElementById("sectionModalFeedback");
const btnDeleteSectionAction = document.getElementById("btnDeleteSectionAction");

const globalCalendarModal = document.getElementById("globalCalendarModal");
const globalCalendarCloseBtn = document.getElementById("globalCalendarCloseBtn");
const globalCalendarBackdrop = document.getElementById("globalCalendarBackdrop");
const closeGlobalCalendarBtn = document.getElementById("closeGlobalCalendarBtn");
const globalCalPrevBtn = document.getElementById("globalCalPrevBtn");
const globalCalNextBtn = document.getElementById("globalCalNextBtn");
const globalCalMonthYear = document.getElementById("globalCalMonthYear");
const globalCalDaysGrid = document.getElementById("globalCalDaysGrid");
const breakdownDateTitle = document.getElementById("breakdownDateTitle");
const breakdownSectionsCount = document.getElementById("breakdownSectionsCount");
const breakdownTotalWater = document.getElementById("breakdownTotalWater");
const breakdownSectionsList = document.getElementById("breakdownSectionsList");

// ----------------------------------------------------
// 1. Initial Authentication & Demo Loading
// ----------------------------------------------------
async function checkAuthAndInitFarmer() {
    try {
        const res = await fetch("/api/auth/me");
        if (res.ok) {
            const data = await res.json();
            if (data.authenticated && data.farmer) {
                if (!data.farmer.onboarding_completed) {
                    window.location.href = "/onboarding";
                    return;
                }
                applyFarmerSession(data.farmer, data.primary_farm, data.land_summary, data.is_impersonating, data.admin_username);
                return;
            }
        }
        // If not authenticated, redirect to Farmer Login page immediately
        window.location.href = "/";
    } catch (e) {
        console.warn("Auth check failed, redirecting to login:", e);
        window.location.href = "/";
    }
}

function applyFarmerSession(farmer, farm, summary, isImpersonating = false, adminUsername = null) {
    window.currentFarmer = farmer;
    window.currentFarm = farm;
    window.landSummary = summary;
    window.isImpersonating = isImpersonating;

    // Administrative Impersonation Banner
    const adminBanner = document.getElementById("adminImpersonationBanner");
    const bannerFarmerName = document.getElementById("bannerFarmerName");
    const bannerFarmerId = document.getElementById("bannerFarmerId");
    if (adminBanner) {
        if (isImpersonating) {
            adminBanner.style.display = "block";
            if (bannerFarmerName) bannerFarmerName.textContent = farmer.name;
            if (bannerFarmerId) bannerFarmerId.textContent = farmer.id;
        } else {
            adminBanner.style.display = "none";
        }
    }

    // Update Top Bar
    if (farmerNameDisplay) farmerNameDisplay.textContent = farmer.name;
    const locText = `${farmer.village || farmer.district || "Farm"}, ${farmer.state}`;
    if (farmerLocationDisplay) farmerLocationDisplay.textContent = locText;

    if (dropdownFarmerName) dropdownFarmerName.textContent = farmer.name;
    const dropdownFarmerUsername = document.getElementById("dropdownFarmerUsername");
    if (dropdownFarmerUsername) dropdownFarmerUsername.textContent = `@${farmer.username || farmer.id}`;
    if (dropdownFarmerLand) dropdownFarmerLand.textContent = `${farmer.total_land || (farm && farm.total_area_acres) || 1.0} ${(farm && farm.unit) || "Acres"}`;
    if (dropdownFarmerLocation) dropdownFarmerLocation.textContent = `📍 ${farmer.state}`;

    if (dropdownAuthIcon) dropdownAuthIcon.textContent = "🚪";
    if (dropdownAuthLabel) dropdownAuthLabel.textContent = "Logout";

    const dropdownManageDevicesBtn = document.getElementById("dropdownManageDevicesBtn");
    if (dropdownManageDevicesBtn) dropdownManageDevicesBtn.style.display = "flex";

    // Update Banner
    if (farmTitleText) farmTitleText.textContent = (farm && farm.name) ? farm.name : `${farmer.name}'s Farm`;
    if (farmAccountBadge) {
        farmAccountBadge.textContent = "Active Farm";
        farmAccountBadge.className = "farm-verified-pill";
    }
    if (farmLocationText) {
        const locParts = [farmer.village, farmer.district, farmer.state].filter(Boolean).join(", ");
        const latStr = farmer.latitude ? `${farmer.latitude.toFixed(4)}° N` : "--";
        const lonStr = farmer.longitude ? `${farmer.longitude.toFixed(4)}° E` : "--";
        farmLocationText.textContent = `📍 ${locParts || "Farm Location"} · GPS: ${latStr}, ${lonStr}`;
    }

    // Fetch Weather & Sections
    if (farmer.latitude && farmer.longitude) {
        fetchLiveFarmWeather(farmer.latitude, farmer.longitude);
    }
    if (farm && farm.id) {
        loadFarmSections(farm.id);
    }
    updateGlobalCalendarBadge();
}

async function demoLoginFarmer(demoType) {
    try {
        const res = await fetch("/api/auth/demo-login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ demo_user: demoType })
        });
        const data = await res.json();
        if (data.status === "success") {
            const meRes = await fetch("/api/auth/me");
            if (meRes.ok) {
                const meData = await meRes.json();
                applyFarmerSession(meData.farmer, meData.primary_farm, meData.land_summary);
            }
            if (authModal) authModal.style.display = "none";
            if (farmerDropdownMenu) farmerDropdownMenu.style.display = "none";
        }
    } catch (e) {
        console.error("Demo login error:", e);
    }
}

async function logoutFarmer() {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
        window.location.href = "/";
    } catch (e) {
        window.location.href = "/";
    }
}

// ----------------------------------------------------
// 2. Land Sections & Allocation Bar
// ----------------------------------------------------
async function loadFarmSections(farmId) {
    if (!farmId) return;
    try {
        const res = await fetch(`/api/farms/${farmId}/sections`);
        if (!res.ok) return;
        const data = await res.json();
        window.farmSections = data.sections || [];
        window.landSummary = data.summary || {};

        renderLandSummary(window.landSummary);
        renderSectionsGrid(window.farmSections);

        // Auto-select first active or first section
        if (window.farmSections.length > 0) {
            const defaultSec = window.farmSections.find(s => !s.is_empty) || window.farmSections[0];
            selectSection(defaultSec.id);
        }
    } catch (e) {
        console.error("Failed to load sections:", e);
    }
}

function renderLandSummary(summary) {
    if (!summary) return;
    const tot = summary.total_land || 1.0;
    const alloc = summary.allocated_land || 0.0;
    const avail = summary.available_land || 0.0;
    const count = summary.total_sections || 0;
    const unit = summary.unit || "Acre";

    if (landStatTotal) landStatTotal.textContent = `${tot.toFixed(2)} ${unit}`;
    if (landStatAllocated) landStatAllocated.textContent = `${alloc.toFixed(2)} ${unit}`;
    if (landStatAvailable) landStatAvailable.textContent = `${avail.toFixed(2)} ${unit}`;
    if (landStatSections) landStatSections.textContent = `${count} Sections`;

    // Render Multi-Segment Progress Bar
    if (landProgressBar) {
        landProgressBar.innerHTML = "";
        window.farmSections.forEach(sec => {
            const pct = Math.max(2, (sec.area_acres / tot) * 100);
            const seg = document.createElement("div");
            seg.className = "progress-segment";
            seg.style.width = `${pct}%`;
            seg.title = `${sec.name}: ${sec.area_acres} Ac (${sec.is_empty ? "Empty" : sec.crop})`;

            const cLower = (sec.crop || "").toLowerCase();
            if (sec.is_empty) seg.classList.add("seg-empty");
            else if (cLower === "wheat") seg.classList.add("seg-wheat");
            else if (cLower === "potato") seg.classList.add("seg-potato");
            else if (cLower === "rice") seg.classList.add("seg-rice");
            else if (cLower === "maize") seg.classList.add("seg-maize");
            else seg.classList.add("seg-crop-general");

            landProgressBar.appendChild(seg);
        });
    }

    // Legend
    if (landProgressLegend) {
        landProgressLegend.innerHTML = "";
        window.farmSections.forEach(sec => {
            const chip = document.createElement("span");
            chip.className = "legend-chip";
            const dot = document.createElement("span");
            dot.className = "chip-dot";

            const cLower = (sec.crop || "").toLowerCase();
            if (sec.is_empty) dot.style.background = "#94a3b8";
            else if (cLower === "wheat") dot.style.background = "#16a34a";
            else if (cLower === "potato") dot.style.background = "#f59e0b";
            else if (cLower === "rice") dot.style.background = "#0284c7";
            else dot.style.background = "#10b981";

            chip.appendChild(dot);
            chip.appendChild(document.createTextNode(`${sec.name} (${sec.is_empty ? "Empty" : sec.crop} ${sec.area_acres} Ac)`));
            landProgressLegend.appendChild(chip);
        });
    }
}

function renderSectionsGrid(sections) {
    if (!sectionsCardsGrid) return;
    sectionsCardsGrid.innerHTML = "";

    sections.forEach(sec => {
        const card = document.createElement("div");
        card.className = `section-card ${sec.id === window.activeSectionId ? "active" : ""} ${sec.is_empty ? "is-empty" : ""}`;
        card.dataset.sectionId = sec.id;

        const cName = sec.crop || (sec.is_empty ? "Empty Land" : "Field");
        let cropIcon = "🌾";
        let pillClass = "pill-empty";
        if (!sec.is_empty) {
            const cl = cName.toLowerCase();
            if (cl === "potato") { cropIcon = "🥔"; pillClass = "pill-potato"; }
            else if (cl === "rice") { cropIcon = "🌾"; pillClass = "pill-rice"; }
            else if (cl === "wheat") { cropIcon = "🌾"; pillClass = "pill-wheat"; }
            else { cropIcon = "🌱"; pillClass = "pill-wheat"; }
        }

        const ageText = sec.is_empty ? "Uncultivated" : `Age: ${sec.crop_age_days}d (${sec.growth_stage || "Active"})`;

        card.innerHTML = `
            <div class="section-card-top">
                <div class="sec-name-badge-group">
                    <span class="sec-name-title">${sec.name}</span>
                    <span class="sec-area-tag">${sec.area_acres.toFixed(2)} Acre</span>
                </div>
                <span class="sec-crop-pill ${pillClass}">
                    <span>${cropIcon}</span>
                    <span>${cName}</span>
                </span>
            </div>
            <div class="section-card-body">
                <div class="sec-meta-row">
                    <span>Growth Stage</span>
                    <strong>${ageText}</strong>
                </div>
                <div class="sec-meta-row">
                    <span>Soil Moisture</span>
                    <strong>${sec.is_empty ? "--" : sec.soil_moisture + "%"}</strong>
                </div>
                <div class="sec-meta-row">
                    <span>Irrigation Status</span>
                    ${sec.is_empty 
                        ? '<span class="sec-irr-indicator irr-empty">🌱 No Irrigation Needed</span>'
                        : '<span class="sec-irr-indicator irr-needed">💧 Active Unit</span>'}
                </div>
            </div>
            <div class="section-card-footer">
                <button type="button" class="btn-sec-plan">${sec.id === window.activeSectionId ? "✓ Planning Active" : "Select & Plan"}</button>
                <button type="button" class="btn-sec-edit-sm" title="Edit section">✏️ Edit</button>
                <button type="button" class="btn-sec-delete-sm" title="Remove section" style="background:#fee2e2; color:#991b1b; border:1px solid #fecaca; border-radius:6px; padding:4px 8px; font-size:12px; font-weight:600; cursor:pointer;">🗑️ Remove</button>
            </div>
        `;

        card.addEventListener("click", (e) => {
            if (e.target.closest(".btn-sec-edit-sm")) {
                openEditSectionModal(sec.id);
            } else if (e.target.closest(".btn-sec-delete-sm")) {
                e.stopPropagation();
                if (confirm(`Are you sure you want to remove ${sec.name}?`)) {
                    fetch(`/api/sections/${sec.id}`, { method: "DELETE" }).then(res => {
                        if (res.ok && window.currentFarm) loadFarmSections(window.currentFarm.id);
                    });
                }
            } else {
                selectSection(sec.id);
            }
        });

        sectionsCardsGrid.appendChild(card);
    });
}

function selectSection(sectionId) {
    window.activeSectionId = sectionId;
    const sec = window.farmSections.find(s => s.id === sectionId);
    if (!sec) return;

    // Highlight card in grid
    const allCards = sectionsCardsGrid ? sectionsCardsGrid.querySelectorAll(".section-card") : [];
    allCards.forEach(c => {
        if (c.dataset.sectionId === sectionId) {
            c.classList.add("active");
            const btn = c.querySelector(".btn-sec-plan");
            if (btn) btn.textContent = "✓ Planning Active";
        } else {
            c.classList.remove("active");
            const btn = c.querySelector(".btn-sec-plan");
            if (btn) btn.textContent = "Select & Plan";
        }
    });

    // Populate Active Banner
    if (activeSecTitle) {
        activeSecTitle.textContent = `${sec.name} — ${sec.is_empty ? "Empty Land" : sec.crop} (${sec.area_acres.toFixed(2)} Acre)`;
    }
    if (activeSecSub) {
        activeSecSub.textContent = sec.is_empty 
            ? "Uncultivated section · No irrigation schedule or prediction" 
            : `Independent irrigation calculations scaled for ${sec.area_acres.toFixed(2)} acre`;
    }
    if (activeSecAgeChip) {
        if (sec.is_empty) {
            activeSecAgeChip.style.display = "inline-flex";
            activeSecAgeChip.textContent = "🌱 Uncultivated";
        } else if (sec.crop_age_days) {
            activeSecAgeChip.style.display = "inline-flex";
            activeSecAgeChip.textContent = `🌱 Age: ${sec.crop_age_days} days (${sec.growth_stage || "Active"})`;
        } else {
            activeSecAgeChip.style.display = "none";
            activeSecAgeChip.textContent = "";
        }
    }

    // Populate Form Inputs
    if (sectionAreaAcresInput) sectionAreaAcresInput.value = sec.area_acres;
    if (sowingDateInput) {
        sowingDateInput.value = sec.sowing_date || "";
        if (calculatedCropAgeBadge) {
            const placeholder = document.getElementById("calculatedCropAgePlaceholder");
            if (sec.is_empty) {
                calculatedCropAgeBadge.style.display = "inline-block";
                calculatedCropAgeBadge.textContent = "Uncultivated";
                if (placeholder) placeholder.style.display = "none";
            } else if (sec.crop_age_days) {
                calculatedCropAgeBadge.style.display = "inline-block";
                calculatedCropAgeBadge.textContent = `${sec.crop_age_days} days (${sec.growth_stage || "Active"})`;
                if (placeholder) placeholder.style.display = "none";
            } else {
                calculatedCropAgeBadge.style.display = "none";
                calculatedCropAgeBadge.textContent = "";
                if (placeholder) placeholder.style.display = "inline";
            }
        }
    }

    const stateSelect = document.getElementById("state_select");
    const cropTypeSelect = document.getElementById("crop_type");
    const soilMoistureInput = document.getElementById("soil_moisture");
    const soilTempInput = document.getElementById("soil_temperature");

    if (soilMoistureInput) soilMoistureInput.value = sec.soil_moisture;
    if (soilTempInput) soilTempInput.value = sec.soil_temp;

    // Handle Empty Land vs Cultivated Section
    if (sec.is_empty) {
        if (emptyLandCard) emptyLandCard.style.display = "flex";
        if (emptyLandSectionName) emptyLandSectionName.textContent = sec.name;
        if (emptyLandAreaDisplay) emptyLandAreaDisplay.textContent = `${sec.area_acres.toFixed(2)} Acre`;
        if (smartSchedulerCard) smartSchedulerCard.style.display = "none";
        if (noIrrigationCard) noIrrigationCard.style.display = "none";
    } else {
        if (emptyLandCard) emptyLandCard.style.display = "none";

        // Sync Crop Dropdown
        if (window.currentFarmer && stateSelect) {
            stateSelect.value = window.currentFarmer.state;
            stateSelect.dispatchEvent(new Event("change"));
            setTimeout(() => {
                if (cropTypeSelect) {
                    cropTypeSelect.value = sec.crop;
                    cropTypeSelect.dispatchEvent(new Event("change"));
                }
            }, 100);
        }

        // Load section schedules & display scheduler
        loadSectionSchedules(sec.id);
    }
}

// ----------------------------------------------------
// 3. Section-Wise Prediction & Scheduling
// ----------------------------------------------------
async function loadSectionSchedules(sectionId) {
    try {
        const res = await fetch(`/api/sections/${sectionId}/schedules`);
        if (!res.ok) return;
        const data = await res.json();
        const scheds = data.schedules || [];
        if (scheds.length > 0) {
            updateSchedulerUI(scheds, scheds[0].water_quantity_liters);
        } else {
            // Clean initial empty state: no schedule generated yet for this section!
            showNoIrrigationUI("No irrigation schedule available yet. Calculate irrigation requirements above to generate a schedule.");
        }
    } catch (e) {
        console.warn("Could not load section schedules:", e);
    }
}

async function predictActiveSection() {
    if (!window.activeSectionId) return;
    const sec = window.farmSections.find(s => s.id === window.activeSectionId);
    if (!sec || sec.is_empty) return;

    try {
        const res = await fetch(`/api/sections/${sec.id}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                soil_moisture: document.getElementById("soil_moisture") ? parseFloat(document.getElementById("soil_moisture").value) : sec.soil_moisture,
                air_temp: window.liveWeather ? window.liveWeather.current_temp : sec.air_temp,
                humidity: window.liveWeather ? window.liveWeather.current_humidity : sec.humidity,
                forecast_24h: window.liveWeather ? window.liveWeather.forecast_rainfall_24h : 0.0
            })
        });
        if (!res.ok) return;
        const pred = await res.json();

        if (pred.irrigation_required) {
            // Set default start date in prompt to tomorrow
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            if (schedStartDateInput) {
                schedStartDateInput.value = tomorrow.toISOString().split("T")[0];
            }
            if (schedPlanPrompt) schedPlanPrompt.style.display = "block";

            // If schedules returned, update scheduler
            if (pred.schedules && pred.schedules.length > 0) {
                updateSchedulerUI(pred.schedules, pred.water_requirement_liters);
            }
        } else {
            showNoIrrigationUI(pred.reason);
        }
    } catch (e) {
        console.error("Section prediction failed:", e);
    }
}

async function generateSectionScheduleAction() {
    if (!window.activeSectionId) return;
    const startDate = schedStartDateInput ? schedStartDateInput.value : null;
    const period = schedPeriodSelect ? parseInt(schedPeriodSelect.value, 10) : 7;
    const rainForecast = window.liveWeather ? window.liveWeather.forecast_rainfall_24h : 0.0;

    try {
        const res = await fetch(`/api/sections/${window.activeSectionId}/schedule`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start_date: startDate,
                planning_period_days: period,
                forecast_24h: rainForecast
            })
        });
        const data = await res.json();
        if (data.status === "success" && data.schedules) {
            updateSchedulerUI(data.schedules);
            updateGlobalCalendarBadge();
            if (window.currentFarm) loadFarmSections(window.currentFarm.id);
        }
    } catch (e) {
        console.error("Failed to generate section schedule:", e);
    }
}

if (btnGenerateSectionSchedule) {
    btnGenerateSectionSchedule.addEventListener("click", (e) => {
        e.preventDefault();
        generateSectionScheduleAction();
    });
}

// ----------------------------------------------------
// 4. Live Weather Integration (Open-Meteo)
// ----------------------------------------------------
async function fetchLiveFarmWeather(lat, lon) {
    try {
        const res = await fetch(`/api/weather/live?lat=${lat}&lon=${lon}`);
        if (!res.ok) return;
        const w = await res.json();
        window.liveWeather = w;

        if (weatherTempDisplay) weatherTempDisplay.textContent = `${w.current_temp.toFixed(1)} °C`;
        if (weatherConditionDisplay) weatherConditionDisplay.textContent = w.current_weather;
        if (weatherHumidityDisplay) weatherHumidityDisplay.textContent = `${Math.round(w.current_humidity)}%`;
        if (weatherRainDisplay) weatherRainDisplay.textContent = `${w.current_rainfall.toFixed(1)} mm`;
        if (weatherForecast24Display) weatherForecast24Display.textContent = `${w.forecast_rainfall_24h.toFixed(1)} mm`;
        if (weatherSoilTempDisplay) weatherSoilTempDisplay.textContent = `${(w.current_temp - 2).toFixed(1)} °C`;

        const now = new Date();
        if (weatherSyncTime) weatherSyncTime.textContent = `Updated ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

        // Sync with hero banners
        const heroTemp = document.getElementById("heroTemperature");
        const heroHum = document.getElementById("heroHumidity");
        if (heroTemp) heroTemp.textContent = `${w.current_temp.toFixed(1)} °C`;
        if (heroHum) heroHum.textContent = `${Math.round(w.current_humidity)}%`;
    } catch (e) {
        console.warn("Weather fetch failed:", e);
    }
}

if (btnRefreshWeather) {
    btnRefreshWeather.addEventListener("click", () => {
        if (window.currentFarmer) {
            fetchLiveFarmWeather(window.currentFarmer.latitude || 30.9010, window.currentFarmer.longitude || 75.8573);
        }
    });
}

// ----------------------------------------------------
// 5. Global Combined Farmer Calendar
// ----------------------------------------------------
async function updateGlobalCalendarBadge() {
    try {
        const res = await fetch("/api/farmer/calendar");
        if (!res.ok) return;
        const data = await res.json();
        const days = data.daily_schedule || data.days || {};
        let upcomingCount = 0;
        Object.values(days).forEach(d => {
            if (d.has_upcoming) upcomingCount++;
        });

        if (globalCalBadge) {
            if (upcomingCount > 0) {
                globalCalBadge.style.display = "inline-flex";
                globalCalBadge.textContent = upcomingCount;
            } else {
                globalCalBadge.style.display = "none";
            }
        }
    } catch (e) {
        console.warn("Could not update calendar badge:", e);
    }
}

async function openGlobalCalendarModal() {
    if (!globalCalendarModal) return;
    globalCalendarModal.style.display = "flex";
    await renderGlobalCalendar(window.globalCalYear, window.globalCalMonth);
}

async function renderGlobalCalendar(year, month) {
    try {
        const res = await fetch(`/api/farmer/calendar?year=${year}&month=${month}`);
        if (!res.ok) return;
        const data = await res.json();
        window.globalCalData = data;

        const dateObj = new Date(year, month - 1, 1);
        if (globalCalMonthYear) {
            globalCalMonthYear.textContent = dateObj.toLocaleString("en-US", { month: "long", year: "numeric" });
        }

        if (!globalCalDaysGrid) return;
        globalCalDaysGrid.innerHTML = "";

        const daysInMonth = new Date(year, month, 0).getDate();
        const firstDayIdx = new Date(year, month - 1, 1).getDay();
        const dailyMap = data.daily_schedule || data.days || {};

        // Empty padding cells
        for (let i = 0; i < firstDayIdx; i++) {
            const emptyCell = document.createElement("div");
            emptyCell.className = "global-cal-cell cell-empty";
            globalCalDaysGrid.appendChild(emptyCell);
        }

        // Active day cells
        let firstActiveDateStr = null;
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
            const dayData = dailyMap[dateStr];

            const cell = document.createElement("div");
            cell.className = "global-cal-cell";
            cell.dataset.date = dateStr;

            const topDiv = document.createElement("div");
            topDiv.className = "global-cell-top";
            const numSpan = document.createElement("span");
            numSpan.className = "global-cell-num";
            numSpan.textContent = d;
            topDiv.appendChild(numSpan);

            if (dayData) {
                const dotsRow = document.createElement("div");
                dotsRow.className = "global-dots-row";
                if (dayData.has_upcoming) {
                    const dot = document.createElement("span");
                    dot.className = "g-dot g-dot-blue";
                    dotsRow.appendChild(dot);
                }
                if (dayData.has_completed) {
                    const dot = document.createElement("span");
                    dot.className = "g-dot g-dot-green";
                    dotsRow.appendChild(dot);
                }
                if (dayData.has_skipped) {
                    const dot = document.createElement("span");
                    dot.className = "g-dot g-dot-red";
                    dotsRow.appendChild(dot);
                }
                topDiv.appendChild(dotsRow);

                cell.appendChild(topDiv);

                const waterSpan = document.createElement("span");
                waterSpan.className = "global-cell-water";
                waterSpan.textContent = `${Math.round(dayData.total_water_liters)} L`;
                cell.appendChild(waterSpan);

                if (!firstActiveDateStr) firstActiveDateStr = dateStr;
            } else {
                cell.appendChild(topDiv);
            }

            cell.addEventListener("click", () => selectGlobalCalendarDate(dateStr));
            globalCalDaysGrid.appendChild(cell);
        }

        // Select first active date or today
        const todayStr = new Date().toISOString().split("T")[0];
        const toSelect = firstActiveDateStr || (dailyMap[todayStr] ? todayStr : Object.keys(dailyMap)[0]);
        if (toSelect) {
            selectGlobalCalendarDate(toSelect);
        } else {
            selectGlobalCalendarDate(todayStr);
        }
    } catch (e) {
        console.error("Failed to render global calendar:", e);
    }
}

function selectGlobalCalendarDate(dateStr) {
    if (!globalCalDaysGrid) return;
    const cells = globalCalDaysGrid.querySelectorAll(".global-cal-cell");
    cells.forEach(c => {
        if (c.dataset.date === dateStr) c.classList.add("is-selected");
        else c.classList.remove("is-selected");
    });

    const dailyMap = window.globalCalData ? (window.globalCalData.daily_schedule || window.globalCalData.days || {}) : {};
    const dayData = dailyMap[dateStr];

    const dObj = new Date(dateStr);
    const formatted = dObj.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

    if (breakdownDateTitle) {
        breakdownDateTitle.textContent = `Farmer's Daily Irrigation — ${formatted}`;
    }

    if (dayData && dayData.items && dayData.items.length > 0) {
        if (breakdownSectionsCount) {
            breakdownSectionsCount.textContent = `${dayData.sections_count} Section${dayData.sections_count > 1 ? "s" : ""} Require Irrigation`;
        }
        if (breakdownTotalWater) {
            breakdownTotalWater.textContent = `${Math.round(dayData.total_water_liters)} L`;
        }
        if (breakdownSectionsList) {
            breakdownSectionsList.innerHTML = "";
            dayData.items.forEach(it => {
                const cLower = (it.crop || "").toLowerCase();
                const icon = cLower === "potato" ? "🥔" : (cLower === "rice" ? "🌾" : "🌾");
                const itemDiv = document.createElement("div");
                itemDiv.className = "breakdown-section-item";
                itemDiv.innerHTML = `
                    <div class="breakdown-item-left">
                        <span class="breakdown-crop-icon">${icon}</span>
                        <div>
                            <span class="breakdown-item-name">${it.section_name} — ${it.crop}</span>
                            <small class="breakdown-item-sub">${it.area_acres} Acre · Optimal Time: ${it.recommended_time}</small>
                        </div>
                    </div>
                    <div class="breakdown-item-right">
                        <strong class="breakdown-item-water">${Math.round(it.water_quantity_liters)} L</strong>
                        <span class="sched-status-chip status-${(it.status || "").toLowerCase()}">${it.status}</span>
                    </div>
                `;
                breakdownSectionsList.appendChild(itemDiv);
            });
        }
    } else {
        if (breakdownSectionsCount) breakdownSectionsCount.textContent = "No Sections Scheduled";
        if (breakdownTotalWater) breakdownTotalWater.textContent = "0 L";
        if (breakdownSectionsList) {
            breakdownSectionsList.innerHTML = `
                <div style="padding: 12px; text-align: center; color: #64748b; font-size: 13px;">
                    No irrigation scheduled on this date across your farm sections. Soil moisture is within safe levels.
                </div>
            `;
        }
    }
}

if (btnGlobalCalendarToggle) {
    btnGlobalCalendarToggle.addEventListener("click", openGlobalCalendarModal);
}

if (globalCalendarCloseBtn) {
    globalCalendarCloseBtn.addEventListener("click", () => {
        if (globalCalendarModal) globalCalendarModal.style.display = "none";
    });
}

if (closeGlobalCalendarBtn) {
    closeGlobalCalendarBtn.addEventListener("click", () => {
        if (globalCalendarModal) globalCalendarModal.style.display = "none";
    });
}

if (globalCalendarBackdrop) {
    globalCalendarBackdrop.addEventListener("click", () => {
        if (globalCalendarModal) globalCalendarModal.style.display = "none";
    });
}

if (globalCalPrevBtn) {
    globalCalPrevBtn.addEventListener("click", () => {
        window.globalCalMonth--;
        if (window.globalCalMonth < 1) {
            window.globalCalMonth = 12;
            window.globalCalYear--;
        }
        renderGlobalCalendar(window.globalCalYear, window.globalCalMonth);
    });
}

if (globalCalNextBtn) {
    globalCalNextBtn.addEventListener("click", () => {
        window.globalCalMonth++;
        if (window.globalCalMonth > 12) {
            window.globalCalMonth = 1;
            window.globalCalYear++;
        }
        renderGlobalCalendar(window.globalCalYear, window.globalCalMonth);
    });
}

// ----------------------------------------------------
// 6. Section Modal & CRUD Operations (Section Name, Plot Area, Crop Type ONLY)
// ----------------------------------------------------
function openAddSectionModal() {
    if (!sectionModal) return;
    if (modalSectionTitle) modalSectionTitle.textContent = "Add Land Section";
    if (modalSectionId) modalSectionId.value = "";
    if (modalSectionName) modalSectionName.value = `Section 0${(window.farmSections ? window.farmSections.length + 1 : 1)}`;
    if (modalSectionArea) {
        modalSectionArea.value = (window.landSummary && window.landSummary.available_land > 0) 
            ? window.landSummary.available_land 
            : 0.50;
    }
    if (modalCropSelect) modalCropSelect.value = "Wheat";
    if (btnDeleteSectionAction) btnDeleteSectionAction.style.display = "none";
    if (sectionModalFeedback) sectionModalFeedback.style.display = "none";

    if (modalAreaLimitHint && window.landSummary) {
        modalAreaLimitHint.textContent = `Available for allocation: ${window.landSummary.available_land} ${window.landSummary.unit || 'Acre'}`;
    }

    sectionModal.style.display = "flex";
}

function openEditSectionModal(sectionId) {
    const sec = window.farmSections.find(s => s.id === sectionId);
    if (!sec || !sectionModal) return;

    if (modalSectionTitle) modalSectionTitle.textContent = `Edit Land Section: ${sec.name}`;
    if (modalSectionId) modalSectionId.value = sec.id;
    if (modalSectionName) modalSectionName.value = sec.name;
    if (modalSectionArea) modalSectionArea.value = sec.area_acres;

    if (modalCropSelect) {
        modalCropSelect.value = (sec.is_empty || !sec.crop || sec.crop.toLowerCase() === "empty") ? "Empty" : sec.crop;
    }

    if (btnDeleteSectionAction) btnDeleteSectionAction.style.display = "inline-block";
    if (sectionModalFeedback) sectionModalFeedback.style.display = "none";

    if (modalAreaLimitHint && window.landSummary) {
        const maxAvail = (window.landSummary.available_land + sec.area_acres).toFixed(2);
        modalAreaLimitHint.textContent = `Current: ${sec.area_acres} ${window.landSummary.unit || 'Acre'} | Max allocatable: ${maxAvail} ${window.landSummary.unit || 'Acre'}`;
    }

    sectionModal.style.display = "flex";
}

if (btnAddSectionModalBtn) {
    btnAddSectionModalBtn.addEventListener("click", openAddSectionModal);
}

if (btnEditCurrentSection) {
    btnEditCurrentSection.addEventListener("click", () => {
        if (window.activeSectionId) openEditSectionModal(window.activeSectionId);
    });
}

if (btnCultivateEmptySection) {
    btnCultivateEmptySection.addEventListener("click", () => {
        if (window.activeSectionId) openEditSectionModal(window.activeSectionId);
    });
}

if (sectionModalCloseBtn) {
    sectionModalCloseBtn.addEventListener("click", () => {
        if (sectionModal) sectionModal.style.display = "none";
    });
}

if (sectionModalBackdrop) {
    sectionModalBackdrop.addEventListener("click", () => {
        if (sectionModal) sectionModal.style.display = "none";
    });
}

if (formSectionManage) {
    formSectionManage.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!window.currentFarm) return;

        const secId = modalSectionId ? modalSectionId.value : "";
        const nameVal = modalSectionName.value.trim();
        const areaVal = parseFloat(modalSectionArea.value);
        const cropChoice = modalCropSelect.value;
        const isEmpty = (cropChoice === "Empty" || cropChoice.toLowerCase().includes("empty"));

        if (!nameVal) {
            if (sectionModalFeedback) {
                sectionModalFeedback.style.display = "block";
                sectionModalFeedback.className = "form-feedback feedback-error";
                sectionModalFeedback.textContent = "Please enter a section name.";
            }
            return;
        }

        if (isNaN(areaVal) || areaVal <= 0) {
            if (sectionModalFeedback) {
                sectionModalFeedback.style.display = "block";
                sectionModalFeedback.className = "form-feedback feedback-error";
                sectionModalFeedback.textContent = "Please enter a valid positive plot area.";
            }
            return;
        }

        const payload = {
            name: nameVal,
            area_acres: areaVal,
            is_empty: isEmpty,
            crop: isEmpty ? null : cropChoice,
        };

        try {
            const url = secId 
                ? `/api/sections/${secId}` 
                : `/api/farms/${window.currentFarm.id}/sections`;
            const method = secId ? "PUT" : "POST";

            const res = await fetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                sectionModal.style.display = "none";
                await loadFarmSections(window.currentFarm.id);
                if (secId) {
                    selectSection(secId);
                } else if (data.section && data.section.id) {
                    selectSection(data.section.id);
                }
            } else {
                if (sectionModalFeedback) {
                    sectionModalFeedback.style.display = "block";
                    sectionModalFeedback.className = "form-feedback feedback-error";
                    sectionModalFeedback.textContent = data.error || "Failed to save section.";
                }
            }
        } catch (err) {
            console.error("Save section error:", err);
            if (sectionModalFeedback) {
                sectionModalFeedback.style.display = "block";
                sectionModalFeedback.className = "form-feedback feedback-error";
                sectionModalFeedback.textContent = "Network error while saving section.";
            }
        }
    });
}

if (btnDeleteSectionAction) {
    btnDeleteSectionAction.addEventListener("click", async () => {
        const secId = modalSectionId ? modalSectionId.value : "";
        if (!secId || !window.currentFarm) return;
        if (!confirm("Are you sure you want to remove this land section?")) return;

        try {
            const res = await fetch(`/api/sections/${secId}`, { method: "DELETE" });
            if (res.ok) {
                sectionModal.style.display = "none";
                await loadFarmSections(window.currentFarm.id);
            }
        } catch (err) {
            console.error("Delete section error:", err);
        }
    });
}

// ----------------------------------------------------
// 7. Auth Modal & Location Geocoding
// ----------------------------------------------------
if (farmerAccountBtn) {
    farmerAccountBtn.addEventListener("click", () => {
        if (!farmerDropdownMenu) return;
        const isHidden = farmerDropdownMenu.style.display === "none" || !farmerDropdownMenu.style.display;
        farmerDropdownMenu.style.display = isHidden ? "block" : "none";
    });
}

// Close dropdown on outside click
document.addEventListener("click", (e) => {
    if (farmerAccountWrap && !farmerAccountWrap.contains(e.target)) {
        if (farmerDropdownMenu) farmerDropdownMenu.style.display = "none";
    }
});

// Prevent back-button viewing of stale authenticated dashboard after logout
window.addEventListener("pageshow", function(event) {
    if (event.persisted) {
        window.location.reload();
    }
});

if (dropdownAuthBtn) {
    dropdownAuthBtn.addEventListener("click", () => {
        if (window.currentFarmer) {
            logoutFarmer();
        } else {
            if (authModal) authModal.style.display = "flex";
            if (farmerDropdownMenu) farmerDropdownMenu.style.display = "none";
        }
    });
}

if (authModalCloseBtn) {
    authModalCloseBtn.addEventListener("click", () => {
        if (authModal) authModal.style.display = "none";
    });
}

if (authModalBackdrop) {
    authModalBackdrop.addEventListener("click", () => {
        if (authModal) authModal.style.display = "none";
    });
}

// Auth Tabs
if (tabAuthLoginBtn && tabAuthRegisterBtn) {
    tabAuthLoginBtn.addEventListener("click", () => {
        tabAuthLoginBtn.classList.add("active");
        tabAuthRegisterBtn.classList.remove("active");
        if (formFarmerLogin) formFarmerLogin.style.display = "block";
        if (formFarmerRegister) formFarmerRegister.style.display = "none";
    });
    tabAuthRegisterBtn.addEventListener("click", () => {
        tabAuthRegisterBtn.classList.add("active");
        tabAuthLoginBtn.classList.remove("active");
        if (formFarmerLogin) formFarmerLogin.style.display = "none";
        if (formFarmerRegister) formFarmerRegister.style.display = "block";
    });
}

// GPS Location Detection
if (btnAutoDetectGPS) {
    btnAutoDetectGPS.addEventListener("click", () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser.");
            return;
        }
        btnAutoDetectGPS.textContent = "Detecting...";
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                if (regLat) regLat.value = lat;
                if (regLon) regLon.value = lon;
                if (detectedCoordsText) {
                    detectedCoordsText.textContent = `Coordinates: ${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`;
                }

                try {
                    const res = await fetch(`/api/location/reverse?lat=${lat}&lon=${lon}`);
                    if (res.ok) {
                        const loc = await res.json();
                        if (regState && loc.state) regState.value = loc.state;
                        if (regDistrict && loc.district) regDistrict.value = loc.district;
                        if (regVillage && loc.village) regVillage.value = loc.village;
                    }
                } catch (e) {
                    console.warn("Reverse geocode failed:", e);
                }
                btnAutoDetectGPS.innerHTML = '<span>🎯</span> <span>GPS Detected</span>';
            },
            (err) => {
                console.warn("GPS error:", err);
                btnAutoDetectGPS.innerHTML = '<span>🎯</span> <span>Detect via GPS</span>';
                alert("Could not retrieve GPS location. You can enter your farm location manually.");
            },
            { timeout: 8000 }
        );
    });
}

// Canonical unit calculator
function updateCanonicalLandDisplay() {
    if (!regTotalLand || !regLandUnit || !canonicalAreaHint) return;
    const val = parseFloat(regTotalLand.value) || 1.0;
    const unit = regLandUnit.value;
    let factor = 1.0;
    if (unit === "Hectares") factor = 2.471;
    else if (unit === "Bigha") factor = 0.62;
    else if (unit === "Guntha") factor = 0.025;

    const acres = (val * factor).toFixed(2);
    canonicalAreaHint.innerHTML = `Canonical Area: <strong>${acres} Acre</strong> (used internally for water scaling)`;
}

if (regTotalLand) regTotalLand.addEventListener("input", updateCanonicalLandDisplay);
if (regLandUnit) regLandUnit.addEventListener("change", updateCanonicalLandDisplay);

// Form Login Submit
if (formFarmerLogin) {
    formFarmerLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const idVal = document.getElementById("loginIdentifier") ? document.getElementById("loginIdentifier").value.trim() : "";
        const pwdVal = document.getElementById("loginPassword") ? document.getElementById("loginPassword").value.trim() : "";

        try {
            const res = await fetch("/api/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ identifier: idVal, password: pwdVal })
            });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                const meRes = await fetch("/api/auth/me");
                if (meRes.ok) {
                    const meData = await meRes.json();
                    applyFarmerSession(meData.farmer, meData.primary_farm, meData.land_summary);
                }
                if (authModal) authModal.style.display = "none";
            } else {
                if (loginFeedback) {
                    loginFeedback.style.display = "block";
                    loginFeedback.className = "form-feedback feedback-error";
                    loginFeedback.textContent = data.error || "Login failed.";
                }
            }
        } catch (err) {
            console.error("Login error:", err);
        }
    });
}

// ========================================================
// W3C WebAuthn Passkeys & Mobile OTP Client Implementation
// ========================================================
function base64UrlToBuffer(base64url) {
    if (!base64url) return new ArrayBuffer(0);
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4;
    const padded = pad ? base64 + '='.repeat(4 - pad) : base64;
    const binary = atob(padded);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

function bufferToBase64Url(buffer) {
    if (!buffer) return '';
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function isWebAuthnSupported() {
    return window.PublicKeyCredential && typeof window.PublicKeyCredential === 'function';
}

// 1. Prominent 1-Touch Face / Fingerprint Login Button
const btnPasskeyLogin = document.getElementById("btnPasskeyLogin");
if (btnPasskeyLogin) {
    btnPasskeyLogin.addEventListener("click", async () => {
        if (!isWebAuthnSupported()) {
            if (loginFeedback) {
                loginFeedback.style.display = "block";
                loginFeedback.className = "form-feedback feedback-error";
                loginFeedback.textContent = "Biometric passkeys are not supported on this browser. Please use Mobile OTP login below.";
            }
            return;
        }

        const phoneVal = document.getElementById("loginOtpPhone") ? document.getElementById("loginOtpPhone").value.trim() : "";
        if (loginFeedback) {
            loginFeedback.style.display = "block";
            loginFeedback.className = "form-feedback feedback-info";
            loginFeedback.textContent = "Please touch your device fingerprint sensor or scan Face ID / enter PIN...";
        }

        try {
            // 1. Get authentication options from backend
            const optRes = await fetch("/api/auth/passkey/login-options", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone: phoneVal || null })
            });
            if (!optRes.ok) {
                const errData = await optRes.json();
                if (loginFeedback) {
                    loginFeedback.className = "form-feedback feedback-error";
                    loginFeedback.textContent = errData.error || "Unable to start biometric authentication.";
                }
                return;
            }

            const options = await optRes.json();

            // 2. Decode binary challenge and allowCredentials
            options.challenge = base64UrlToBuffer(options.challenge);
            if (options.allowCredentials && Array.isArray(options.allowCredentials)) {
                options.allowCredentials = options.allowCredentials.map(c => ({
                    ...c,
                    id: base64UrlToBuffer(c.id)
                }));
            }

            // 3. Trigger native device biometric prompt (Android BiometricPrompt, iOS Face ID, Windows Hello)
            const credential = await navigator.credentials.get({ publicKey: options });
            if (!credential) {
                throw new Error("No credential was returned from authenticator.");
            }

            // 4. Serialize for server verification
            const credentialJson = {
                id: credential.id,
                rawId: bufferToBase64Url(credential.rawId),
                type: credential.type,
                response: {
                    authenticatorData: bufferToBase64Url(credential.response.authenticatorData),
                    clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),
                    signature: bufferToBase64Url(credential.response.signature),
                    userHandle: credential.response.userHandle ? bufferToBase64Url(credential.response.userHandle) : null,
                }
            };

            // 5. Send to server
            const verifyRes = await fetch("/api/auth/passkey/login-verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: credentialJson })
            });

            const verifyData = await verifyRes.json();
            if (verifyRes.ok && verifyData.status === "success") {
                if (loginFeedback) {
                    loginFeedback.className = "form-feedback feedback-success";
                    loginFeedback.textContent = `Welcome, ${verifyData.farmer.name}! Authenticated with ${verifyData.device_name || 'Biometrics'}.`;
                }
                setTimeout(async () => {
                    const meRes = await fetch("/api/auth/me");
                    if (meRes.ok) {
                        const meData = await meRes.json();
                        applyFarmerSession(meData.farmer, meData.primary_farm, meData.land_summary);
                    }
                    if (authModal) authModal.style.display = "none";
                }, 500);
            } else {
                if (loginFeedback) {
                    loginFeedback.className = "form-feedback feedback-error";
                    loginFeedback.textContent = verifyData.error || "Biometric login failed. Please use Mobile OTP.";
                }
            }
        } catch (err) {
            console.warn("Passkey login error:", err);
            if (loginFeedback) {
                loginFeedback.className = "form-feedback feedback-error";
                if (err.name === "NotAllowedError") {
                    loginFeedback.textContent = "Biometric prompt was cancelled. You can log in using Mobile OTP below.";
                } else {
                    loginFeedback.textContent = "Biometric sensor unavailable. You can log in using Mobile OTP below.";
                }
            }
        }
    });
}

// 2. Mobile OTP Login Handlers
const btnSendLoginOtp = document.getElementById("btnSendLoginOtp");
const loginOtpVerifyBox = document.getElementById("loginOtpVerifyBox");
const loginOtpPhone = document.getElementById("loginOtpPhone");
const loginOtpCode = document.getElementById("loginOtpCode");
const btnSubmitOtpLogin = document.getElementById("btnSubmitOtpLogin");
const btnResendLoginOtp = document.getElementById("btnResendLoginOtp");

async function handleSendLoginOtp() {
    const phone = loginOtpPhone ? loginOtpPhone.value.trim() : "";
    if (!phone || phone.length < 10) {
        if (loginFeedback) {
            loginFeedback.style.display = "block";
            loginFeedback.className = "form-feedback feedback-error";
            loginFeedback.textContent = "Please enter a valid 10-digit mobile number.";
        }
        return;
    }

    if (btnSendLoginOtp) {
        btnSendLoginOtp.disabled = true;
        btnSendLoginOtp.textContent = "Sending...";
    }

    try {
        const res = await fetch("/api/auth/otp/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, purpose: "login" })
        });
        const data = await res.json();
        if (btnSendLoginOtp) {
            btnSendLoginOtp.disabled = false;
            btnSendLoginOtp.textContent = "Send OTP";
        }

        if (res.ok && data.success) {
            if (loginOtpVerifyBox) loginOtpVerifyBox.style.display = "block";
            const sentMsg = document.getElementById("loginOtpSentMsg");
            if (sentMsg) sentMsg.textContent = `OTP code sent to +91 ${phone}`;
            if (loginFeedback) {
                loginFeedback.style.display = "block";
                loginFeedback.className = "form-feedback feedback-success";
                loginFeedback.textContent = data.message + (data.otp_preview ? ` (Verification Code: ${data.otp_preview})` : "");
            }
            if (loginOtpCode) {
                if (data.otp_preview) loginOtpCode.value = data.otp_preview;
                loginOtpCode.focus();
            }
        } else {
            if (loginFeedback) {
                loginFeedback.style.display = "block";
                loginFeedback.className = "form-feedback feedback-error";
                loginFeedback.textContent = data.error || "Unable to send verification OTP.";
            }
        }
    } catch (e) {
        if (btnSendLoginOtp) {
            btnSendLoginOtp.disabled = false;
            btnSendLoginOtp.textContent = "Send OTP";
        }
        if (loginFeedback) {
            loginFeedback.style.display = "block";
            loginFeedback.className = "form-feedback feedback-error";
            loginFeedback.textContent = "Network error sending OTP.";
        }
    }
}

if (btnSendLoginOtp) btnSendLoginOtp.addEventListener("click", handleSendLoginOtp);
if (btnResendLoginOtp) btnResendLoginOtp.addEventListener("click", handleSendLoginOtp);

if (btnSubmitOtpLogin) {
    btnSubmitOtpLogin.addEventListener("click", async () => {
        const phone = loginOtpPhone ? loginOtpPhone.value.trim() : "";
        const otp = loginOtpCode ? loginOtpCode.value.trim() : "";
        if (!phone || !otp) {
            if (loginFeedback) {
                loginFeedback.style.display = "block";
                loginFeedback.className = "form-feedback feedback-error";
                loginFeedback.textContent = "Please enter your mobile number and 6-digit OTP code.";
            }
            return;
        }

        btnSubmitOtpLogin.disabled = true;
        btnSubmitOtpLogin.innerHTML = '<span>Verifying...</span>';

        try {
            const res = await fetch("/api/auth/otp/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone, otp, purpose: "login" })
            });
            const data = await res.json();
            btnSubmitOtpLogin.disabled = false;
            btnSubmitOtpLogin.innerHTML = '<span>Verify &amp; Login</span> <span aria-hidden="true">➜</span>';

            if (res.ok && data.status === "success") {
                const meRes = await fetch("/api/auth/me");
                if (meRes.ok) {
                    const meData = await meRes.json();
                    applyFarmerSession(meData.farmer, meData.primary_farm, meData.land_summary);
                }
                if (authModal) authModal.style.display = "none";

                // Offer Face/Fingerprint registration if farmer hasn't enrolled on this device
                if (data.offer_passkey || !data.has_passkeys) {
                    openPasskeyEnrollModal();
                }
            } else {
                if (loginFeedback) {
                    loginFeedback.style.display = "block";
                    loginFeedback.className = "form-feedback feedback-error";
                    loginFeedback.textContent = data.error || "Verification failed.";
                }
            }
        } catch (e) {
            btnSubmitOtpLogin.disabled = false;
            btnSubmitOtpLogin.innerHTML = '<span>Verify &amp; Login</span> <span aria-hidden="true">➜</span>';
            if (loginFeedback) {
                loginFeedback.style.display = "block";
                loginFeedback.className = "form-feedback feedback-error";
                loginFeedback.textContent = "Network error verifying OTP.";
            }
        }
    });
}

// 3. Registration with Verified Mobile OTP
const btnSendRegOtp = document.getElementById("btnSendRegOtp");
const regOtpVerifyBox = document.getElementById("regOtpVerifyBox");
const regPhone = document.getElementById("regPhone");
const regOtpCode = document.getElementById("regOtpCode");
const btnResendRegOtp = document.getElementById("btnResendRegOtp");

async function handleSendRegOtp() {
    const phone = regPhone ? regPhone.value.trim() : "";
    if (!phone || phone.length < 10) {
        if (registerFeedback) {
            registerFeedback.style.display = "block";
            registerFeedback.className = "form-feedback feedback-error";
            registerFeedback.textContent = "Please enter a valid 10-digit mobile number.";
        }
        return;
    }

    if (btnSendRegOtp) {
        btnSendRegOtp.disabled = true;
        btnSendRegOtp.textContent = "Sending...";
    }

    try {
        const res = await fetch("/api/auth/otp/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, purpose: "register" })
        });
        const data = await res.json();
        if (btnSendRegOtp) {
            btnSendRegOtp.disabled = false;
            btnSendRegOtp.textContent = "Send OTP";
        }

        if (res.ok && data.success) {
            if (regOtpVerifyBox) regOtpVerifyBox.style.display = "block";
            const sentMsg = document.getElementById("regOtpSentMsg");
            if (sentMsg) sentMsg.textContent = `OTP code sent to +91 ${phone}`;
            if (registerFeedback) {
                registerFeedback.style.display = "block";
                registerFeedback.className = "form-feedback feedback-success";
                registerFeedback.textContent = data.message + (data.otp_preview ? ` (Verification Code: ${data.otp_preview})` : "");
            }
            if (regOtpCode) {
                if (data.otp_preview) regOtpCode.value = data.otp_preview;
                regOtpCode.focus();
            }
        } else {
            if (registerFeedback) {
                registerFeedback.style.display = "block";
                registerFeedback.className = "form-feedback feedback-error";
                registerFeedback.textContent = data.error || "Unable to send verification OTP.";
            }
        }
    } catch (e) {
        if (btnSendRegOtp) {
            btnSendRegOtp.disabled = false;
            btnSendRegOtp.textContent = "Send OTP";
        }
        if (registerFeedback) {
            registerFeedback.style.display = "block";
            registerFeedback.className = "form-feedback feedback-error";
            registerFeedback.textContent = "Network error sending OTP.";
        }
    }
}

if (btnSendRegOtp) btnSendRegOtp.addEventListener("click", handleSendRegOtp);
if (btnResendRegOtp) btnResendRegOtp.addEventListener("click", handleSendRegOtp);

// Form Register Submit (Verified OTP registration)
if (formFarmerRegister) {
    formFarmerRegister.addEventListener("submit", async (e) => {
        e.preventDefault();
        const phoneVal = regPhone ? regPhone.value.trim() : "";
        const otpVal = regOtpCode ? regOtpCode.value.trim() : "";

        if (!otpVal) {
            if (registerFeedback) {
                registerFeedback.style.display = "block";
                registerFeedback.className = "form-feedback feedback-error";
                registerFeedback.textContent = "Please click 'Send OTP' and enter the 6-digit verification code.";
            }
            if (!regOtpVerifyBox || regOtpVerifyBox.style.display === "none") {
                handleSendRegOtp();
            }
            return;
        }

        const payload = {
            name: document.getElementById("regName").value.trim(),
            phone: phoneVal,
            otp: otpVal,
            state: regState ? regState.value.trim() : "Punjab",
            district: regDistrict ? regDistrict.value.trim() : "",
            village: regVillage ? regVillage.value.trim() : "",
            latitude: regLat ? parseFloat(regLat.value) : 30.9010,
            longitude: regLon ? parseFloat(regLon.value) : 75.8573,
            total_land: regTotalLand ? parseFloat(regTotalLand.value) : 1.0,
            unit: regLandUnit ? regLandUnit.value : "Acres"
        };

        const btnSubmit = document.getElementById("btnSubmitRegister");
        if (btnSubmit) {
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span>Creating Account...</span>';
        }

        try {
            const res = await fetch("/api/auth/register-with-otp", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<span>Verify OTP &amp; Create Account</span> <span aria-hidden="true">➜</span>';
            }

            if (res.ok && data.status === "success") {
                const meRes = await fetch("/api/auth/me");
                if (meRes.ok) {
                    const meData = await meRes.json();
                    applyFarmerSession(meData.farmer, meData.primary_farm, meData.land_summary);
                }
                if (authModal) authModal.style.display = "none";

                // Immediately offer Face/Fingerprint passkey enrollment
                if (data.offer_passkey) {
                    openPasskeyEnrollModal();
                }
            } else {
                if (registerFeedback) {
                    registerFeedback.style.display = "block";
                    registerFeedback.className = "form-feedback feedback-error";
                    registerFeedback.textContent = data.error || "Registration failed.";
                }
            }
        } catch (err) {
            if (btnSubmit) {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<span>Verify OTP &amp; Create Account</span> <span aria-hidden="true">➜</span>';
            }
            if (registerFeedback) {
                registerFeedback.style.display = "block";
                registerFeedback.className = "form-feedback feedback-error";
                registerFeedback.textContent = "Network error during registration.";
            }
        }
    });
}

// 4. Passkey Enrollment Modal Handlers
const passkeyEnrollModal = document.getElementById("passkeyEnrollModal");
const passkeyEnrollCloseBtn = document.getElementById("passkeyEnrollCloseBtn");
const passkeyEnrollBackdrop = document.getElementById("passkeyEnrollBackdrop");
const btnConfirmEnrollPasskey = document.getElementById("btnConfirmEnrollPasskey");
const btnSkipEnrollPasskey = document.getElementById("btnSkipEnrollPasskey");
const passkeyEnrollFeedback = document.getElementById("passkeyEnrollFeedback");

function openPasskeyEnrollModal() {
    if (!passkeyEnrollModal) return;
    if (passkeyEnrollFeedback) passkeyEnrollFeedback.style.display = "none";
    passkeyEnrollModal.style.display = "flex";
}

function closePasskeyEnrollModal() {
    if (passkeyEnrollModal) passkeyEnrollModal.style.display = "none";
}

if (passkeyEnrollCloseBtn) passkeyEnrollCloseBtn.addEventListener("click", closePasskeyEnrollModal);
if (passkeyEnrollBackdrop) passkeyEnrollBackdrop.addEventListener("click", closePasskeyEnrollModal);
if (btnSkipEnrollPasskey) btnSkipEnrollPasskey.addEventListener("click", closePasskeyEnrollModal);

if (btnConfirmEnrollPasskey) {
    btnConfirmEnrollPasskey.addEventListener("click", async () => {
        if (!isWebAuthnSupported()) {
            if (passkeyEnrollFeedback) {
                passkeyEnrollFeedback.style.display = "block";
                passkeyEnrollFeedback.className = "form-feedback feedback-error";
                passkeyEnrollFeedback.textContent = "Biometrics are not supported on this browser. You can always log in with Mobile OTP.";
            }
            return;
        }

        btnConfirmEnrollPasskey.disabled = true;
        btnConfirmEnrollPasskey.innerHTML = '<span>Touch Sensor or Verify Face...</span>';

        if (passkeyEnrollFeedback) {
            passkeyEnrollFeedback.style.display = "block";
            passkeyEnrollFeedback.className = "form-feedback feedback-info";
            passkeyEnrollFeedback.textContent = "Please touch your fingerprint sensor or verify with Face ID / device PIN...";
        }

        try {
            // 1. Fetch registration options
            const optRes = await fetch("/api/auth/passkey/register-options", { method: "POST" });
            if (!optRes.ok) {
                const errData = await optRes.json();
                throw new Error(errData.error || "Unable to start passkey registration.");
            }

            const options = await optRes.json();

            // 2. Decode binary challenge and user id
            options.challenge = base64UrlToBuffer(options.challenge);
            options.user.id = base64UrlToBuffer(options.user.id);
            if (options.excludeCredentials && Array.isArray(options.excludeCredentials)) {
                options.excludeCredentials = options.excludeCredentials.map(c => ({
                    ...c,
                    id: base64UrlToBuffer(c.id)
                }));
            }

            // 3. Trigger native device creation
            const credential = await navigator.credentials.create({ publicKey: options });
            if (!credential) {
                throw new Error("No credential was created.");
            }

            // 4. Format credential response
            const credentialJson = {
                id: credential.id,
                rawId: bufferToBase64Url(credential.rawId),
                type: credential.type,
                response: {
                    attestationObject: bufferToBase64Url(credential.response.attestationObject),
                    clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),
                    transports: credential.response.getTransports ? credential.response.getTransports() : [],
                }
            };

            // 5. Send to server
            const verifyRes = await fetch("/api/auth/passkey/register-verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ credential: credentialJson })
            });

            const verifyData = await verifyRes.json();
            if (verifyRes.ok && verifyData.status === "success") {
                if (passkeyEnrollFeedback) {
                    passkeyEnrollFeedback.className = "form-feedback feedback-success";
                    passkeyEnrollFeedback.textContent = "✅ Face / Fingerprint Login successfully enabled for this device!";
                }
                setTimeout(() => {
                    closePasskeyEnrollModal();
                }, 1200);
            } else {
                throw new Error(verifyData.error || "Passkey verification failed.");
            }
        } catch (err) {
            console.warn("Passkey enrollment error:", err);
            btnConfirmEnrollPasskey.disabled = false;
            btnConfirmEnrollPasskey.innerHTML = '<span>🔐 Enable Face / Fingerprint Login</span>';
            if (passkeyEnrollFeedback) {
                passkeyEnrollFeedback.className = "form-feedback feedback-error";
                if (err.name === "NotAllowedError") {
                    passkeyEnrollFeedback.textContent = "Biometric registration was cancelled. You can enable it anytime from your account menu.";
                } else {
                    passkeyEnrollFeedback.textContent = err.message || "Failed to register device sensor.";
                }
            }
        }
    });
}

// 5. Face Lock & Device Management Handlers
const deviceManageModal = document.getElementById("deviceManageModal");
const deviceManageCloseBtn = document.getElementById("deviceManageCloseBtn");
const deviceManageDoneBtn = document.getElementById("deviceManageDoneBtn");
const deviceManageBackdrop = document.getElementById("deviceManageBackdrop");
const dropdownManageDevicesBtn = document.getElementById("dropdownManageDevicesBtn");
const devicesListContainer = document.getElementById("devicesListContainer");
const faceLockStatusText = document.getElementById("faceLockStatusText");
const devicesCountText = document.getElementById("devicesCountText");
const btnEnableFaceLockSetting = document.getElementById("btnEnableFaceLockSetting");
const btnRegisterAnotherDeviceSetting = document.getElementById("btnRegisterAnotherDeviceSetting");
const btnDisableFaceLockSetting = document.getElementById("btnDisableFaceLockSetting");
const passwordConfirmBox = document.getElementById("passwordConfirmBox");
const passwordConfirmTitle = document.getElementById("passwordConfirmTitle");
const passwordConfirmDesc = document.getElementById("passwordConfirmDesc");
const inputConfirmPassword = document.getElementById("inputConfirmPassword");
const btnExecuteConfirmedAction = document.getElementById("btnExecuteConfirmedAction");
const btnCancelConfirmedAction = document.getElementById("btnCancelConfirmedAction");
const passwordConfirmError = document.getElementById("passwordConfirmError");
const deviceManageFeedback = document.getElementById("deviceManageFeedback");

let pendingSecurityAction = null;

function openDeviceManageModal() {
    if (!deviceManageModal) return;
    deviceManageModal.style.display = "flex";
    if (passwordConfirmBox) passwordConfirmBox.style.display = "none";
    if (deviceManageFeedback) deviceManageFeedback.style.display = "none";
    pendingSecurityAction = null;
    loadRegisteredDevices();
}

function closeDeviceManageModal() {
    if (deviceManageModal) deviceManageModal.style.display = "none";
    if (passwordConfirmBox) passwordConfirmBox.style.display = "none";
    pendingSecurityAction = null;
}

if (dropdownManageDevicesBtn) {
    dropdownManageDevicesBtn.addEventListener("click", () => {
        if (farmerDropdownMenu) farmerDropdownMenu.style.display = "none";
        openDeviceManageModal();
    });
}
if (deviceManageCloseBtn) deviceManageCloseBtn.addEventListener("click", closeDeviceManageModal);
if (deviceManageDoneBtn) deviceManageDoneBtn.addEventListener("click", closeDeviceManageModal);
if (deviceManageBackdrop) deviceManageBackdrop.addEventListener("click", closeDeviceManageModal);

if (btnEnableFaceLockSetting) {
    btnEnableFaceLockSetting.addEventListener("click", () => {
        closeDeviceManageModal();
        openPasskeyEnrollModal();
    });
}

if (btnRegisterAnotherDeviceSetting) {
    btnRegisterAnotherDeviceSetting.addEventListener("click", () => {
        closeDeviceManageModal();
        openPasskeyEnrollModal();
    });
}

if (btnDisableFaceLockSetting) {
    btnDisableFaceLockSetting.addEventListener("click", () => {
        if (deviceManageFeedback) deviceManageFeedback.style.display = "none";
        if (passwordConfirmError) passwordConfirmError.style.display = "none";
        if (passwordConfirmBox) {
            passwordConfirmBox.style.display = "block";
            passwordConfirmTitle.textContent = "Confirm Disabling Face Lock";
            passwordConfirmDesc.textContent = "Please enter your password to disable Face Lock and remove all registered device passkeys:";
            inputConfirmPassword.value = "";
            inputConfirmPassword.focus();
        }
        pendingSecurityAction = { type: "disable_facelock" };
    });
}

if (btnCancelConfirmedAction) {
    btnCancelConfirmedAction.addEventListener("click", () => {
        if (passwordConfirmBox) passwordConfirmBox.style.display = "none";
        if (passwordConfirmError) passwordConfirmError.style.display = "none";
        pendingSecurityAction = null;
    });
}

if (btnExecuteConfirmedAction) {
    btnExecuteConfirmedAction.addEventListener("click", async () => {
        const password = inputConfirmPassword ? inputConfirmPassword.value.trim() : "";
        if (!password) {
            if (passwordConfirmError) {
                passwordConfirmError.style.display = "block";
                passwordConfirmError.textContent = "Please enter your password.";
            }
            return;
        }

        if (!pendingSecurityAction) return;

        btnExecuteConfirmedAction.disabled = true;
        btnExecuteConfirmedAction.textContent = "Verifying...";
        if (passwordConfirmError) passwordConfirmError.style.display = "none";

        try {
            if (pendingSecurityAction.type === "revoke_device") {
                const credId = pendingSecurityAction.credentialId;
                const delRes = await fetch(`/api/auth/passkey/devices/${encodeURIComponent(credId)}`, {
                    method: "DELETE",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ password })
                });
                const data = await delRes.json();
                if (delRes.ok && data.status === "success") {
                    if (passwordConfirmBox) passwordConfirmBox.style.display = "none";
                    pendingSecurityAction = null;
                    if (deviceManageFeedback) {
                        deviceManageFeedback.style.display = "block";
                        deviceManageFeedback.className = "form-feedback feedback-success";
                        deviceManageFeedback.textContent = "✅ Device passkey revoked successfully.";
                    }
                    loadRegisteredDevices();
                } else {
                    if (passwordConfirmError) {
                        passwordConfirmError.style.display = "block";
                        passwordConfirmError.textContent = data.error || "Incorrect password.";
                    }
                }
            } else if (pendingSecurityAction.type === "disable_facelock") {
                const disRes = await fetch("/api/auth/passkey/disable", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ password })
                });
                const data = await disRes.json();
                if (disRes.ok && data.status === "success") {
                    if (passwordConfirmBox) passwordConfirmBox.style.display = "none";
                    pendingSecurityAction = null;
                    if (deviceManageFeedback) {
                        deviceManageFeedback.style.display = "block";
                        deviceManageFeedback.className = "form-feedback feedback-success";
                        deviceManageFeedback.textContent = "✅ Face Lock disabled. All device passkeys removed.";
                    }
                    loadRegisteredDevices();
                } else {
                    if (passwordConfirmError) {
                        passwordConfirmError.style.display = "block";
                        passwordConfirmError.textContent = data.error || "Incorrect password.";
                    }
                }
            }
        } catch (e) {
            if (passwordConfirmError) {
                passwordConfirmError.style.display = "block";
                passwordConfirmError.textContent = "Network error. Please try again.";
            }
        } finally {
            btnExecuteConfirmedAction.disabled = false;
            btnExecuteConfirmedAction.textContent = "Confirm";
        }
    });
}

async function loadRegisteredDevices() {
    if (!devicesListContainer) return;
    devicesListContainer.innerHTML = '<div style="padding: 12px; text-align: center; color: #64748b;">Loading registered devices...</div>';
    try {
        const res = await fetch("/api/auth/passkey/devices");
        if (!res.ok) {
            devicesListContainer.innerHTML = '<div class="alert-box-warning">Please log in to manage your biometric devices.</div>';
            return;
        }
        const data = await res.json();
        const devices = data.devices || [];

        if (devicesCountText) devicesCountText.textContent = devices.length;

        if (devices.length > 0) {
            if (faceLockStatusText) {
                faceLockStatusText.textContent = `Active (${devices.length} registered device${devices.length > 1 ? "s" : ""})`;
                faceLockStatusText.style.color = "#166534";
            }
            if (btnEnableFaceLockSetting) btnEnableFaceLockSetting.style.display = "none";
            if (btnRegisterAnotherDeviceSetting) btnRegisterAnotherDeviceSetting.style.display = "inline-flex";
            if (btnDisableFaceLockSetting) btnDisableFaceLockSetting.style.display = "inline-flex";

            devicesListContainer.innerHTML = devices.map(d => `
                <div class="device-item-card" data-id="${d.id}" style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; margin-bottom:8px;">
                    <div class="device-item-left" style="display:flex; align-items:center; gap:10px;">
                        <span class="device-icon" style="font-size:22px;">📱</span>
                        <div class="device-meta">
                            <strong style="display:block; font-size:13px; color:#0f172a;">${escapeHtml(d.device_name || "Biometric Device")}</strong>
                            <small style="color:#64748b; font-size:11px;">Registered ${escapeHtml(d.created_at ? d.created_at.split('T')[0] : '--')} ${d.last_used_at ? '· Last used ' + d.last_used_at.split('T')[0] : ''}</small>
                        </div>
                    </div>
                    <button type="button" class="btn-remove-device" data-id="${d.id}" title="Revoke this device" style="background:#fee2e2; color:#b91c1c; border:1px solid #fca5a5; padding:5px 10px; border-radius:6px; font-size:11.5px; font-weight:700; cursor:pointer;">
                        Revoke
                    </button>
                </div>
            `).join("");

            // Attach listeners to revoke buttons
            devicesListContainer.querySelectorAll(".btn-remove-device").forEach(btn => {
                btn.addEventListener("click", () => {
                    const credId = btn.getAttribute("data-id");
                    if (deviceManageFeedback) deviceManageFeedback.style.display = "none";
                    if (passwordConfirmError) passwordConfirmError.style.display = "none";
                    if (passwordConfirmBox) {
                        passwordConfirmBox.style.display = "block";
                        passwordConfirmTitle.textContent = "Confirm Device Revocation";
                        passwordConfirmDesc.textContent = "Please enter your password to revoke Face Lock access for this device:";
                        inputConfirmPassword.value = "";
                        inputConfirmPassword.focus();
                    }
                    pendingSecurityAction = { type: "revoke_device", credentialId: credId };
                });
            });
        } else {
            if (faceLockStatusText) {
                faceLockStatusText.textContent = "Not Enabled";
                faceLockStatusText.style.color = "#64748b";
            }
            if (btnEnableFaceLockSetting) btnEnableFaceLockSetting.style.display = "inline-flex";
            if (btnRegisterAnotherDeviceSetting) btnRegisterAnotherDeviceSetting.style.display = "none";
            if (btnDisableFaceLockSetting) btnDisableFaceLockSetting.style.display = "none";

            devicesListContainer.innerHTML = `
                <div style="padding: 18px; text-align: center; color: #64748b; background: #f8fafc; border-radius: 10px; border:1px dashed #cbd5e1;">
                    <span style="font-size: 28px; display: block; margin-bottom: 6px;">👤</span>
                    <strong>No Face Lock devices registered yet.</strong>
                    <p style="font-size: 12px; margin-top: 4px;">Click "Enable Face Lock" above to register this device's Face Unlock or fingerprint sensor.</p>
                </div>
            `;
        }
    } catch (e) {
        devicesListContainer.innerHTML = '<div class="alert-box-warning">Error loading devices.</div>';
    }
}

// 6. Toggle Discrete Password Login
const btnTogglePasswordLogin = document.getElementById("btnTogglePasswordLogin");
const formFarmerPasswordLogin = document.getElementById("formFarmerPasswordLogin");
if (btnTogglePasswordLogin && formFarmerPasswordLogin) {
    btnTogglePasswordLogin.addEventListener("click", () => {
        const isHidden = formFarmerPasswordLogin.style.display === "none";
        formFarmerPasswordLogin.style.display = isHidden ? "block" : "none";
        btnTogglePasswordLogin.textContent = isHidden ? "Hide password login" : "Use password login instead";
    });
}

// Global Hooks
window.openGlobalCalendar = openGlobalCalendarModal;
window.selectSection = selectSection;
window.demoLoginFarmer = demoLoginFarmer;
window.openAddSectionModal = openAddSectionModal;
window.openEditSectionModal = openEditSectionModal;
window.loadFarmSections = loadFarmSections;

// Bootstrap Multi-Farmer Engine on page load
checkAuthAndInitFarmer();


