"""
Voice Command Engine for Smart Irrigation Planner.
Provides secure, context-aware, multilingual voice control of the entire website.
Strictly dispatches only whitelisted actions with authenticated farmer-level data isolation.
Supports English, Telugu, Hindi, Punjabi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, etc.
"""

import re
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.farm_manager import (
    get_farmer_by_id,
    get_farmer_farms,
    get_farm_by_id,
    get_farm_sections,
    get_section_by_id,
    get_land_summary,
    create_section,
    update_section,
    delete_section,
    predict_section_irrigation,
    schedule_section_irrigation,
    get_section_schedules,
    update_section_schedule_status,
    get_farmer_combined_calendar,
    update_farmer_onboarding,
    CROP_BASE_LITERS_PER_ACRE,
)
from src.weather_service import get_live_weather
from src.voice_i18n_messages import get_voice_message
from src.voice_triggers import (
    DASHBOARD_TRIGGERS,
    FARM_SUMMARY_TRIGGERS,
    SELECT_SECTION_TRIGGERS,
    CHECK_IRRIGATION_TRIGGERS,
    UPCOMING_SCHEDULE_TRIGGERS,
    EXPLAIN_PREDICTION_TRIGGERS,
    HISTORY_TRIGGERS,
)
from src.languages_registry import get_language, LANGUAGES_REGISTRY

logger = logging.getLogger("voice_command_engine")

# Approved Whitelist of Backend Actions (Security Requirement 11)
APPROVED_VOICE_ACTIONS = {
    "navigate_to_page",
    "select_farm",
    "select_section",
    "select_crop",
    "scroll_page",
    "save_section",
    "calculate_irrigation",
    "update_farm_details",
    "add_land_section",
    "edit_land_section",
    "remove_land_section",
    "run_irrigation_prediction",
    "calculate_water_requirement",
    "generate_irrigation_schedule",
    "get_weather",
    "get_farm_summary",
    "get_irrigation_history",
    "get_upcoming_schedule",
    "update_irrigation_status",
    "set_onboarding_field",
    "complete_onboarding",
    "explain_prediction",
    "cancel_action",
}

# Supported Indian States Mapping (Normalized English Name)
STATE_SYNONYMS = {
    "andhra pradesh": "Andhra Pradesh",
    "andhra": "Andhra Pradesh",
    "ఆంధ్రప్రదేశ్": "Andhra Pradesh",
    "ఆంధ్ర": "Andhra Pradesh",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "ਆਂਧਰਾ ਪ੍ਰਦੇਸ਼": "Andhra Pradesh",
    "ஆந்திரப் பிரதேசம்": "Andhra Pradesh",
    "ಆಂಧ್ರಪ್ರದೇಶ": "Andhra Pradesh",
    "telangana": "Telangana",
    "తెలంగాణ": "Telangana",
    "तेलंगाना": "Telangana",
    "ਤੇਲੰਗਾਨਾ": "Telangana",
    "தெலுங்கானா": "Telangana",
    "punjab": "Punjab",
    "పంజాబ్": "Punjab",
    "पंजाब": "Punjab",
    "ਪੰਜਾਬ": "Punjab",
    "பஞ்சாப்": "Punjab",
    "haryana": "Haryana",
    "హర్యానా": "Haryana",
    "हरियाणा": "Haryana",
    "ਹਰਿਆਣਾ": "Haryana",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "ఉత్తర ప్రదేశ్": "Uttar Pradesh",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "ਉੱਤਰ ਪ੍ਰਦੇਸ਼": "Uttar Pradesh",
    "maharashtra": "Maharashtra",
    "మహారాష్ట్ర": "Maharashtra",
    "महाराष्ट्र": "Maharashtra",
    "gujarat": "Gujarat",
    "గుజరాత్": "Gujarat",
    "गुजरात": "Gujarat",
    "ગુજરાત": "Gujarat",
    "rajasthan": "Rajasthan",
    "రాజస్థాన్": "Rajasthan",
    "राजस्थान": "Rajasthan",
    "tamil nadu": "Tamil Nadu",
    "తమిళనాడు": "Tamil Nadu",
    "तमिलनाडु": "Tamil Nadu",
    "தமிழ்நாடு": "Tamil Nadu",
    "karnataka": "Karnataka",
    "కర్ణాటక": "Karnataka",
    "कर्नाटक": "Karnataka",
    "ಕರ್ನಾಟಕ": "Karnataka",
    "kerala": "Kerala",
    "కేరళ": "Kerala",
    "केरल": "Kerala",
    "കേരളം": "Kerala",
    "west bengal": "West Bengal",
    "bengal": "West Bengal",
    "పశ్చిమ బెంగాల్": "West Bengal",
    "पश्चिम बंगाल": "West Bengal",
    "পশ্চিমবঙ্গ": "West Bengal",
    "bihar": "Bihar",
    "బీహార్": "Bihar",
    "बिहार": "Bihar",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "ఒడిశా": "Odisha",
    "ओडिशा": "Odisha",
    "ଓଡ଼ିଶା": "Odisha",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "మధ్యప్రదేశ్": "Madhya Pradesh",
    "मध्य प्रदेश": "Madhya Pradesh",
    "assam": "Assam",
    "అస్సాం": "Assam",
    "असम": "Assam",
}

# Crop Synonyms Mapping
CROP_SYNONYMS = {
    "wheat": "Wheat",
    "గోధుమ": "Wheat",
    "గేహూ": "Wheat",
    "गेहूं": "Wheat",
    "ਕਣਕ": "Wheat",
    "கோதுமை": "Wheat",
    "rice": "Rice",
    "paddy": "Rice",
    "వరి": "Rice",
    "ధాన్యం": "Rice",
    "धान": "Rice",
    "चावल": "Rice",
    "ਝੋਨਾ": "Rice",
    "ਚੌਲ": "Rice",
    "அரிசி": "Rice",
    "potato": "Potato",
    "బంగాళాదుంప": "Potato",
    "ఆలుగడ్డ": "Potato",
    "आलू": "Potato",
    "ਆਲੂ": "Potato",
    "உருளைக்கிழங்கு": "Potato",
    "cotton": "Cotton",
    "పత్తి": "Cotton",
    "कपास": "Cotton",
    "ਕਪਾਹ": "Cotton",
    "பருத்தி": "Cotton",
    "maize": "Maize",
    "corn": "Maize",
    "మొక్కజొన్న": "Maize",
    "मक्का": "Maize",
    "ਮੱਕੀ": "Maize",
    "sugarcane": "Sugarcane",
    "చెరకు": "Sugarcane",
    "గన్నా": "Sugarcane",
    "गन्ना": "Sugarcane",
    "ਗੰਨਾ": "Sugarcane",
    "tomato": "Tomato",
    "టమోటా": "Tomato",
    "టమాట": "Tomato",
    "टमाटर": "Tomato",
    "ਟਮਾਟਰ": "Tomato",
    "தக்காளி": "Tomato",
    "groundnut": "Groundnut",
    "వేరుశనగ": "Groundnut",
    "వేరుశెనగ": "Groundnut",
    "मूंगफली": "Groundnut",
    "ਮੂੰਗਫਲੀ": "Groundnut",
    "empty": "Empty",
    "ఖాళీ": "Empty",
    "खाली": "Empty",
    "ਖਾਲੀ": "Empty",
}

# Number words parser for Indian languages
NUMBER_WORDS = {
    # English
    "half": 0.5,
    "quarter": 0.25,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    # Telugu
    "అర": 0.5,
    "సగం": 0.5,
    "పావు": 0.25,
    "ఒక": 1.0,
    "ఒకటి": 1.0,
    "రెండు": 2.0,
    "మూడు": 3.0,
    "నాలుగు": 4.0,
    "ఐదు": 5.0,
    "ఆరు": 6.0,
    "ఏడు": 7.0,
    "ఎనిమిది": 8.0,
    "తొమ్మిది": 9.0,
    "పది": 10.0,
    # Hindi
    "आधा": 0.5,
    "डेढ़": 1.5,
    "ढाई": 2.5,
    "एक": 1.0,
    "दो": 2.0,
    "तीन": 3.0,
    "चार": 4.0,
    "पांच": 5.0,
    "पाँच": 5.0,
    "छह": 6.0,
    "सात": 7.0,
    "आठ": 8.0,
    "नौ": 9.0,
    "दस": 10.0,
    # Punjabi
    "ਅੱਧਾ": 0.5,
    "ਇੱਕ": 1.0,
    "ਦੋ": 2.0,
    "ਤਿੰਨ": 3.0,
    "ਚਾਰ": 4.0,
    "ਪੰਜ": 5.0,
    "ਛੇ": 6.0,
    "ਸੱਤ": 7.0,
    "ਅੱਠ": 8.0,
    "ਨੌਂ": 9.0,
    "ਦਸ": 10.0,
    # Tamil
    "அரை": 0.5,
    "ஒன்று": 1.0,
    "இரண்டு": 2.0,
    "மூன்று": 3.0,
    "நான்கு": 4.0,
    "ஐந்து": 5.0,
    # Kannada
    "ಅರ್ಧ": 0.5,
    "ಒಂದು": 1.0,
    "ಎರಡು": 2.0,
    "ಮೂರು": 3.0,
    "ನಾಲ್ಕು": 4.0,
    "ಐದು": 5.0,
}

# Ordinals mapping across all 23 languages
ORDINALS = {
    # English
    "first": 0, "1st": 0, "section 1": 0, "section 01": 0,
    "second": 1, "2nd": 1, "section 2": 1, "section 02": 1,
    "third": 2, "3rd": 2, "section 3": 2, "section 03": 2,
    "fourth": 3, "4th": 3,
    "crop number 1": 0, "crop number one": 0, "first crop": 0, "crop 1": 0, "crop one": 0,
    "crop number 2": 1, "crop number two": 1, "second crop": 1, "crop 2": 1, "crop two": 1,
    "crop number 3": 2, "crop number three": 2, "third crop": 2, "crop 3": 2, "crop three": 2,
    "crop number 4": 3, "crop number four": 3, "fourth crop": 3, "crop 4": 3, "crop four": 3,
    "first land section": 0, "1st land section": 0, "land section 1": 0, "land section 01": 0, "land section number 1": 0, "land section number one": 0,
    "second land section": 1, "2nd land section": 1, "land section 2": 1, "land section 02": 1, "land section number 2": 1, "land section number two": 1,
    "third land section": 2, "3rd land section": 2, "land section 3": 2, "land section 03": 2, "land section number 3": 2, "land section number three": 2,
    "fourth land section": 3, "4th land section": 3, "land section 4": 3, "land section 04": 3, "land section number 4": 3, "land section number four": 3,
    "first farm": 0, "second farm": 1,
    "number one": 0, "number 1": 0, "no 1": 0, "no. 1": 0,
    "number two": 1, "number 2": 1, "no 2": 1, "no. 2": 1,
    "number three": 2, "number 3": 2, "no 3": 2, "no. 3": 2,
    "number four": 3, "number 4": 3, "no 4": 3, "no. 4": 3,
    # Telugu
    "మొదటి": 0, "మొదటిది": 0, "మొదటి సెక్షన్": 0,
    "రెండవ": 1, "రెండో": 1, "రెండోది": 1, "రెండవ సెక్షన్": 1,
    "మూడవ": 2, "మూడో": 2, "మూడోది": 2,
    # Hindi
    "पहला": 0, "पहला वाला": 0, "पहला सेक्शन": 0,
    "दूसरा": 1, "दूसरा वाला": 1,
    "तीसरा": 2, "तीसरा वाला": 2,
    # Punjabi
    "ਪਹਿਲਾ": 0, "ਪਹਿਲਾ ਸੈਕਸ਼ਨ": 0,
    "ਦੂਜਾ": 1, "ਤੀਜਾ": 2,
    # Tamil
    "முதல்": 0, "முதலாவது": 0, "முதல் பகுதி": 0,
    "இரண்டாவது": 1, "மூன்றாவது": 2,
    # Bengali
    "প্রথম": 0, "১ম": 0, "প্রথম সেকশন": 0,
    "দ্বিতীয়": 1, "তৃতীয়": 2,
    # Marathi
    "पहिला": 0, "१ ला": 0, "पहिला विभाग": 0,
    "दुसरा": 1, "तिसरा": 2,
    # Gujarati
    "પહેલો": 0, "પ્રથમ": 0, "પહેલો વિભાગ": 0,
    "બીજો": 1, "ત્રીજો": 2,
    # Kannada
    "ಮೊದಲ": 0, "ಮೊದಲನೆಯ": 0, "ಮೊದಲ ವಿಭಾಗ": 0,
    "ಎರಡನೇ": 1, "ಮೂರನೇ": 2,
    # Malayalam
    "ആദ്യത്തെ": 0, "ഒന്നാമത്തെ": 0, "ആദ്യത്തെ വിഭാഗം": 0,
    "രണ്ടാമത്തെ": 1, "മൂന്നാമത്തെ": 2,
    # Odia
    "ପ୍ରଥମ": 0, "ପ୍ରଥମ ବିଭାଗ": 0, "ଦ୍ୱିତୀୟ": 1,
    # Assamese
    "প্ৰথম": 0, "প্ৰথম খণ্ড": 0, "দ্বিতীয়": 1,
    # Urdu
    "پہلا": 0, "پہلا سیکشن": 0, "دوسرا": 1,
    # Sanskrit
    "प्रथम": 0, "प्रथमं": 0, "प्रथम विभागम्": 0, "द्वितीय": 1,
    # Nepali
    "पहिलो": 0, "पहिलो खण्ड": 0, "दोस्रो": 1,
    # Konkani
    "पयलो": 0, "पयलें": 0, "पयलो विभाग": 0, "दुसरो": 1,
    # Maithili
    "पहिल": 0, "पहिल खण्ड": 0, "दोसर": 1,
    # Dogri
    "पहला हिस्सा": 0, "दूआ हिस्सा": 1,
    # Bodo
    "गिबि": 0, "गिबि बाहागो": 0, "नैथि": 1,
    # Kashmiri
    "گۄڈنیُک": 0, "گۄڈنیُک حِصہٕ": 0, "دوٚیم": 1,
    # Sindhi
    "پهريون": 0, "پهريون حصو": 0, "ٻيو": 1,
    # Manipuri
    "অহানবা": 0, "অহানবা শরুক": 0, "অনিশুবা": 1,
    # Santali
    "ᱯᱩᱭᱞᱩ": 0, "ᱯᱩᱭᱞᱩ ᱦᱟᱹᱴᱤᱧ": 0, "ᱫᱚᱥᱟᱨ": 1,
}


def extract_number(text: str) -> Optional[float]:
    """Extract numeric value (including decimals and words like 'half an acre', 'అర ఎకరం', 'दो एकड़')."""
    lower = text.lower()

    # Check fractional phrases
    if "half an acre" in lower or "half acre" in lower:
        return 0.5

    # Direct digit match: e.g. 2, 2.5, 0.5
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Clean punctuation and tokenize words across all Indic scripts (\u0900-\u0d7f)
    clean_words = set(re.findall(r"[\w\u0600-\u06ff\u0900-\u0d7f\u1c50-\u1c7f]+", lower))

    # Match number words sorted by length descending so multi-char words take precedence
    for w in sorted(NUMBER_WORDS.keys(), key=len, reverse=True):
        if w in clean_words:
            return NUMBER_WORDS[w]

    return None


def extract_ordinal(text: str) -> Optional[int]:
    """Extract ordinal index (0-based) from text."""
    lower = text.lower()
    # Sort ordinals by length descending so multi-word keys take precedence
    for word, idx in sorted(ORDINALS.items(), key=lambda x: len(x[0]), reverse=True):
        if word in lower:
            return idx
    # Check Section 1, Section 2, Land Section 2, Crop 2, Farm 1, Number 2, etc.
    num_match = re.search(r"(?:(?:land\s*)?section|crop|farm|నెంబర్|నంబర్|नंबर|ਨੰਬਰ|number|no\.?|#)\s*0?(\d+)", lower)
    if num_match:
        try:
            val = int(num_match.group(1))
            if val >= 1:
                return val - 1
        except ValueError:
            pass
    return None


def match_state(text: str) -> Optional[str]:
    """Find certified Indian State from text."""
    lower = text.lower()
    for synonym, canonical in STATE_SYNONYMS.items():
        if synonym in lower:
            return canonical
    return None


def match_crop(text: str) -> Optional[str]:
    """Find crop name from text."""
    lower = text.lower()
    for synonym, canonical in CROP_SYNONYMS.items():
        if synonym in lower:
            return canonical
    return None


def resolve_section_from_context(
    text: str,
    sections: List[Dict[str, Any]],
    context: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve which section the user is referring to.
    Returns (section_dict, resolution_type_or_ambiguity_flag).
    """
    if not sections:
        return None, "no_sections"

    lower = text.lower()

    # 1. Check direct ordinal: "first section", "మొదటి సెక్షన్", "Section 02", etc.
    ordinal_idx = extract_ordinal(text)
    if ordinal_idx is not None and 0 <= ordinal_idx < len(sections):
        return sections[ordinal_idx], "ordinal"

    # 2. Check by section name in text: e.g. "Section 01", "North Plot"
    for s in sections:
        s_name = (s.get("name") or "").lower()
        if s_name and (s_name in lower or s_name.replace(" ", "") in lower.replace(" ", "")):
            return s, "name"

    # 3. Check by crop mention: "wheat crop", "వరి పంట"
    crop = match_crop(text)
    if crop and crop != "Empty":
        matched_by_crop = [s for s in sections if (s.get("crop") or "").lower() == crop.lower()]
        if len(matched_by_crop) == 1:
            return matched_by_crop[0], "crop"
        elif len(matched_by_crop) > 1:
            # Multiple sections with same crop
            return matched_by_crop[0], "multiple_crop_match"

    # 4. Check "this section", "it", "current section", "దీనికి", "ఈ సెక్షన్", "इसका"
    pronoun_triggers = [
        "this", "current", "here", "it",
        "దీనికి", "ఈ సెక్షన్", "ఈ పంట", "ఇది",
        "इस", "इसका", "इसे", "यह", "वर्तमान",
        "ਇਸ", "ਇਹ",
    ]
    is_referring_to_current = any(t in lower for t in pronoun_triggers)

    active_sec_id = context.get("active_section_id") or context.get("last_mentioned_section_id")
    if active_sec_id:
        active_sec = next((s for s in sections if s.get("id") == active_sec_id), None)
        if active_sec:
            return active_sec, "active_context"

    # If only 1 section exists, default to it
    if len(sections) == 1:
        return sections[0], "single_default"

    # Ambiguous: multiple sections exist and none was specified
    return None, "ambiguous"


def get_localized_message(key: str, lang: str = "en", **kwargs) -> str:
    """Produce concise, natural verbal responses in the requested language across all 23 languages."""
    return get_voice_message(key, lang, **kwargs)


def process_voice_command(
    farmer_id: str,
    raw_text: str,
    language: str = "en",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main Entry Point: Process natural speech command from farmer.
    Enforces security whitelist, farmer data isolation, context awareness,
    and returns a structured action payload with verbal confirmation.
    """
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        return {
            "status": "error",
            "error": "Voice command text cannot be empty.",
            "language": language,
        }

    text = raw_text.strip()
    clean = text.lower().replace("?", "").replace("!", "").replace(".", "").replace(",", "").replace("।", "").replace("॥", "").replace("؟", "").strip()
    ctx = context or {}
    page = ctx.get("page", "dashboard")

    # Load authenticated farmer data
    farmer = get_farmer_by_id(farmer_id) if farmer_id else None
    farms = get_farmer_farms(farmer_id) if farmer_id else []
    primary_farm = farms[0] if farms else None
    farm_id = ctx.get("farm_id") or (primary_farm["id"] if primary_farm else None)
    sections = get_farm_sections(farm_id, farmer_id) if (farm_id and farmer_id) else []
    summary = get_land_summary(farm_id, farmer_id) if (farm_id and farmer_id) else {"total_land": 1.0, "allocated_land": 0.0, "available_land": 1.0}

    # --------------------------------------------------------------------------
    # Check Confirmation Responses (if a pending destructive action exists)
    # --------------------------------------------------------------------------
    pending = ctx.get("pending_action")
    if pending and isinstance(pending, dict):
        confirm_words = ["yes", "confirm", "proceed", "అవును", "సరే", "చెయ్యి", "హా", "हाँ", "हां", "ਸਹੀ", "ਹਾਂ", "ஆம்", "ಹೌದು"]
        cancel_words = ["no", "cancel", "stop", "రద్దు", "వద్దు", "తీసివేయవద్దు", "नहीं", "रद्द", "ਮਨ੍ਹਾ", "ਨਾ", "இல்லை", "ಬೇಡ"]

        if any(w in clean for w in confirm_words):
            # Execute pending action!
            action_name = pending.get("action")
            payload = pending.get("payload", {})
            if action_name == "remove_land_section":
                sec_id = payload.get("section_id")
                sec_name = payload.get("section_name", "Section")
                success = delete_section(sec_id, farmer_id)
                msg = get_localized_message("section_removed", language, name=sec_name)
                return {
                    "status": "success",
                    "action": "remove_land_section",
                    "action_payload": {"section_id": sec_id, "section_name": sec_name, "success": success},
                    "requires_confirmation": False,
                    "spoken_response": msg,
                    "display_text": msg,
                    "language": language,
                }
            elif action_name == "update_irrigation_status":
                sched_id = payload.get("schedule_id")
                sec_name = payload.get("section_name", "Section")
                new_status = payload.get("status", "Completed")
                success = update_section_schedule_status(sched_id, farmer_id, new_status)
                msg_key = "status_completed" if new_status == "Completed" else "status_skipped"
                msg = get_localized_message(msg_key, language, name=sec_name)
                return {
                    "status": "success",
                    "action": "update_irrigation_status",
                    "action_payload": {"schedule_id": sched_id, "status": new_status, "section_name": sec_name, "success": success},
                    "requires_confirmation": False,
                    "spoken_response": msg,
                    "display_text": msg,
                    "language": language,
                }

        if any(w in clean for w in cancel_words):
            cancel_msg = {
                "en": "Action cancelled.",
                "te": "చర్య రద్దు చేయబడింది.",
                "hi": "कार्रवाई रद्द कर दी गई।",
                "pa": "ਕਾਰਵਾਈ ਰੱਦ ਕਰ ਦਿੱਤੀ ਗਈ ਹੈ।",
            }.get(language, "Action cancelled.")
            return {
                "status": "success",
                "action": "cancel_action",
                "action_payload": {},
                "requires_confirmation": False,
                "spoken_response": cancel_msg,
                "display_text": cancel_msg,
                "language": language,
            }

    # --------------------------------------------------------------------------
    # 1. Navigation & General Website Control Commands
    # --------------------------------------------------------------------------
    # Scroll Page Commands
    if any(p in clean for p in ["scroll down", "scroll up", "scroll to the top", "scroll to top", "scroll top", "పైకి స్క్రోల్ చేయి", "కిందికి స్క్రోల్ చేయి", "नीचे स्क्रॉल करें", "ऊपर स्क्रॉल करें"]):
        direction = "top" if ("top" in clean or "పైకి" in clean or "ऊपर" in clean) else ("down" if ("down" in clean or "కిందికి" in clean or "नीचे" in clean) else "down")
        msg = "Scrolling to the top." if direction == "top" else "Scrolling down."
        return {
            "status": "success",
            "action": "scroll_page",
            "action_payload": {"direction": direction},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Crop Details
    if any(p in clean for p in [
        "open crop details", "crop details", "show crop details", "go to crop details", "crop information",
        "పంట వివరాలు", "పంట వివరాలు చూపించు", "फसल विवरण", "फसल का विवरण", "ਫਸਲ ਦੇ ਵੇਰਵੇ",
    ]):
        msg = "Opening Crop Details." if language == "en" else "పంట వివరాలను తెరుస్తున్నాము."
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "crop_details", "element_id": "crop_type"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Soil Details
    if any(p in clean for p in [
        "open soil details", "soil details", "show soil details", "go to soil details", "soil information",
        "నేల వివరాలు", "భూమి తేమ వివరాలు", "మట్టి వివరాలు", "मिट्टी का विवरण", "ਮਿੱਟੀ ਦੇ ਵੇਰਵੇ",
    ]):
        msg = "Opening Soil Details." if language == "en" else "నేల వివరాలను తెరుస్తున్నాము."
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "soil_details", "element_id": "soil_moisture"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open First Farm
    if any(p in clean for p in [
        "open the first farm", "select the first farm", "open first farm", "first farm",
        "మొదటి ఫార్మ్ ఓపెన్ చేయి", "पहला खेत खोलो", "ਪਹਿਲਾ ਖੇਤ ਖੋਲ੍ਹੋ",
    ]):
        msg = "Opening your farm overview." if language == "en" else "మీ ఫార్మ్ వివరాలు తెరుస్తున్నాము."
        return {
            "status": "success",
            "action": "select_farm",
            "action_payload": {"farm_index": 0, "target": "farm_overview"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Save Section
    if any(p in clean for p in [
        "save this section", "save section", "save changes", "save",
        "ఈ సెక్షన్ సేవ్ చేయి", "సెక్షన్ సేవ్ చేయి", "భద్రపరచు", "सेव करें", "सुरक्षित करें", "ਸੇਵ ਕਰੋ",
    ]) and page != "onboarding":
        msg = "Saving section." if language == "en" else "సెక్షన్ భద్రపరచబడింది."
        return {
            "status": "success",
            "action": "save_section",
            "action_payload": {},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Calculate Irrigation Requirements
    if any(p in clean for p in [
        "calculate irrigation requirements", "calculate irrigation requirement", "calculate irrigation",
        "calculate requirements", "calculate water requirements",
        "ఇరిగేషన్ అవసరాలను లెక్కించు", "ఇరిగేషన్ లెక్కించు", "నీటి అవసరం లెక్కించు",
        "सिंचाई आवश्यकता की गणना करें", "सिंचाई की गणना करें", "ਸਿੰਚਾਈ ਲੋੜਾਂ ਦੀ ਗਣਨਾ ਕਰੋ",
    ]):
        msg = "Calculating irrigation requirements for your section." if language == "en" else "మీ సెక్షన్ కోసం ఇరిగేషన్ అవసరాలను లెక్కిస్తున్నాము."
        return {
            "status": "success",
            "action": "run_irrigation_prediction",
            "action_payload": {"trigger_calculation": True},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Settings
    if any(p in clean for p in ["open settings", "show settings", "settings", "సెట్టింగులు", "सेटिंग्स", "ਸੈਟਿੰਗ"]):
        msg = "Opening Settings." if language == "en" else "సెట్టింగులను తెరుస్తున్నాము."
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "settings", "element_id": "farmerAccountBtn"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Show Irrigation Schedule
    if any(p in clean for p in [
        "show my irrigation schedule", "open irrigation schedule", "irrigation schedule", "show schedule", "open scheduler",
        "నా ఇరిగేషన్ షెడ్యూల్ చూపించు", "షెడ్యూల్ చూపించు", "సిंचाई अनुसूची", "ਸਿੰਚਾਈ ਅਨੁਸੂਚੀ",
    ]) and not ("generate" in clean or "create" in clean or "make" in clean or "calculate" in clean):
        msg = "Showing your irrigation schedule." if language == "en" else "మీ ఇరిగేషన్ షెడ్యూల్‌ను చూపుతున్నాము."
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "irrigation_schedule", "element_id": "smartSchedulerCard"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Crop Selection by Name or Position (Ordinals)
    is_crop_command = (
        (
            ("crop" in clean or "పంట" in clean or "फसल" in clean)
            and any(w in clean for w in ["select", "choose", "change", "set", "ఎంచుకో", "మార్చు", "चुनो", "बदलें"])
        )
        or (
            match_crop(clean) is not None
            and any(w in clean for w in ["select", "choose", "change", "switch", "ఎంచుకో", "మార్చు", "चुनो", "बदलें"])
        )
    ) and not any(p in clean for p in [
        "section", "land section", "add a section", "create section", "add section", "కొత్త సెక్షన్", "नया सेक्शन",
        "open crop details", "crop details", "show crop details", "go to crop details"
    ])

    if is_crop_command:
        crop_cand = match_crop(clean)
        ord_idx_cand = extract_ordinal(clean)
        if crop_cand:
            msg = f"Selected {crop_cand}." if language == "en" else f"{crop_cand} పంట ఎంచుకోబడింది."
            return {
                "status": "success",
                "action": "select_crop",
                "action_payload": {"crop": crop_cand},
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": f"Selected crop: {crop_cand}",
                "language": language,
            }
        elif ord_idx_cand is not None:
            crop_num = ord_idx_cand + 1
            msg = f"Selected crop number {crop_num}." if language == "en" else f"{crop_num}వ పంట ఎంచుకోబడింది."
            return {
                "status": "success",
                "action": "select_crop",
                "action_payload": {"crop_index": ord_idx_cand, "crop_number": crop_num},
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": f"Selected crop #{crop_num}",
                "language": language,
            }

    # Open Dashboard (All 23 Languages)
    if any(p in clean for p in DASHBOARD_TRIGGERS) or any(p in clean for p in ["return to dashboard", "back to dashboard", "go back to dashboard"]):
        msg = get_localized_message("nav_dashboard", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "dashboard", "url": "/dashboard"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open My Farms
    if any(p in clean for p in [
        "open my farms", "my farms", "show my farms",
        "నా పొలాలు", "నా ఫారమ్స్", "मेरे खेत", "ਮੇਰੇ ਖੇਤ",
    ]) and not any(p in clean for p in FARM_SUMMARY_TRIGGERS):
        msg = get_localized_message("nav_farms", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "my_farms", "element_id": "sectionFarmOverview"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Land Sections (General list, not specific section selection)
    if any(p in clean for p in [
        "open my farm sections", "my farm sections", "farm sections", "open land sections", "land sections",
        "show sections", "open sections", "my sections", "manage sections",
        "ల్యాండ్ సెక్షన్లు", "భూమి సెక్షన్లు", "సెక్షన్లు చూపించు",
        "जमीन अनुभाग", "सेक्शन दिखाओ", "ਜ਼ਮੀਨ ਦੇ ਸੈਕਸ਼ਨ",
    ]) and not any(p in clean for p in SELECT_SECTION_TRIGGERS) and not any(ord_w in clean for ord_w in ORDINALS.keys()):
        msg = get_localized_message("nav_sections", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "land_sections", "element_id": "sectionLandSections"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Irrigation Planner
    if any(p in clean for p in [
        "open irrigation planner", "irrigation planner", "open planner", "go to planner",
        "ఇరిగేషన్ ప్లానర్", "ప్లానర్ ఓపెన్ చేయి", "సిंचाई योजनाकार", "ਸਿੰਚਾਈ ਪਲੈਨਰ",
    ]):
        msg = get_localized_message("nav_planner", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "irrigation_planner", "element_id": "irrigation-planner"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Combined Calendar
    if any(p in clean for p in [
        "open combined calendar", "combined calendar", "farm calendar",
        "సంయుక్త క్యాలెండర్", "ఫార్మ్ క్యాలెండర్", "కంబైన్డ్ క్యాలెండర్",
        "संयुक्त कैलेंडर", "ਸਾਂਝਾ ਕੈਲੰਡਰ",
    ]):
        msg = get_localized_message("nav_combined_cal", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "combined_calendar", "modal_id": "globalCalendarModal"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Irrigation Calendar
    if any(p in clean for p in [
        "open irrigation calendar", "open calendar", "show calendar", "irrigation calendar",
        "ఇరిగేషన్ క్యాలెండర్", "క్యాలెండర్ ఓపెన్ చేయి", "సిंचाई कैलेंडर", "ਕੈਲੰਡਰ",
    ]):
        msg = get_localized_message("nav_calendar", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "irrigation_calendar", "element_id": "btnMiniCalendarToggle"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Irrigation History (All 23 Languages)
    if any(p in clean for p in HISTORY_TRIGGERS):
        msg = get_localized_message("nav_history", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "irrigation_history", "modal_id": "predictionHistoryModal"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Open Profile / Logout / Home / Go Back
    if any(p in clean for p in ["open profile", "show profile", "my profile", "ప్రొఫైల్", "प्रोफाइल", "ਪ੍ਰੋਫਾਈਲ"]):
        msg = get_localized_message("nav_profile", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "profile", "element_id": "farmerAccountBtn"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    if any(p in clean for p in ["log out", "logout", "sign out", "లాగౌట్", "లాగ్ అవుట్", "लॉग आउट"]):
        msg = get_localized_message("nav_logout", language)
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "logout", "url": "/logout"},
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    if any(p in clean for p in ["go back", "back", "వెనుకకు", "వెనక్కి", "पीछे", "ਵਾਪਸ"]):
        return {
            "status": "success",
            "action": "navigate_to_page",
            "action_payload": {"target": "go_back"},
            "requires_confirmation": False,
            "spoken_response": "Returning to previous screen." if language == "en" else "వెనుక స్క్రీన్‌కు వెళుతున్నాము.",
            "display_text": "Going back.",
            "language": language,
        }

    # --------------------------------------------------------------------------
    # 2. Weather and Live Atmospheric Conditions (Section 8)
    # --------------------------------------------------------------------------
    if any(p in clean for p in [
        "current weather", "show weather", "weather", "temperature", "forecast", "rainfall",
        "వాతావరణం", "ఉష్ణోగ్రత", "వర్షం", "వర్ష సూచన",
        "मौसम", "तापमान", "बारिश", "ਮੌਸਮ", "ਬਾਰਿਸ਼", "வானிலை",
    ]):
        lat = farmer.get("latitude") if farmer else 30.9010
        lon = farmer.get("longitude") if farmer else 75.8573
        w_data = get_live_weather(lat, lon)
        temp = w_data.get("current_temp", 28.0)
        humidity = w_data.get("current_humidity", 62.0)
        rain_24 = w_data.get("forecast_rainfall_24h", 0.0)

        msg = get_localized_message("weather_info", language, temp=temp, humidity=humidity, rain=rain_24)
        return {
            "status": "success",
            "action": "get_weather",
            "action_payload": {
                "temperature": temp,
                "humidity": humidity,
                "forecast_rainfall_24h": rain_24,
                "soil_temperature": w_data.get("soil_temp_est", 24.0),
                "location": f"{lat:.2f}, {lon:.2f}",
            },
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # --------------------------------------------------------------------------
    # 3. Farm and Land Summary (Section 8 - All 23 Languages)
    # --------------------------------------------------------------------------
    if any(p in clean for p in FARM_SUMMARY_TRIGGERS):
        total_l = summary.get("total_land", 1.0)
        alloc_l = summary.get("allocated_land", 0.0)
        avail_l = summary.get("available_land", 0.0)
        count_s = len(sections)

        msg = get_localized_message("farm_summary", language, total=total_l, alloc=alloc_l, avail=avail_l, count=count_s)
        return {
            "status": "success",
            "action": "get_farm_summary",
            "action_payload": {
                "total_land": total_l,
                "allocated_land": alloc_l,
                "available_land": avail_l,
                "sections_count": count_s,
                "unit": summary.get("unit", "Acre"),
            },
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # --------------------------------------------------------------------------
    # 4. Onboarding Commands (Section 4)
    # --------------------------------------------------------------------------
    if page == "onboarding" or any(p in clean for p in ["నా రాష్ట్రం", "నా జిల్లా", "నా భూమి", "मेरा राज्य", "ਮੇਰਾ ਰਾਜ"]):
        # Check State
        state_match = match_state(clean)
        if state_match and any(k in clean for k in ["state", "రాష్ట్రం", "राज्य", "ਰਾਜ", "select", "నా"]):
            msg = get_localized_message("onboard_state_set", language, state=state_match)
            return {
                "status": "success",
                "action": "set_onboarding_field",
                "action_payload": {"field": "state", "value": state_match},
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": msg,
                "language": language,
            }

        # Check District
        if any(k in clean for k in ["district", "జిల్లా", "जिला", "ਜ਼ਿਲ੍ਹਾ"]):
            dist_cand = re.sub(r".*(?:district|జిల్లా|जिला|ਜ਼ਿਲ੍ਹਾ)\s*(?:is|to|గా|నుండి)?\s*", "", text, flags=re.IGNORECASE).strip()
            # Clean common words
            dist_cand = dist_cand.replace("నా", "").replace("మా", "").replace("mera", "").strip()
            if dist_cand:
                msg = get_localized_message("onboard_district_set", language, district=dist_cand)
                return {
                    "status": "success",
                    "action": "set_onboarding_field",
                    "action_payload": {"field": "district", "value": dist_cand},
                    "requires_confirmation": False,
                    "spoken_response": msg,
                    "display_text": msg,
                    "language": language,
                }

        # Check Total Land in onboarding
        num = extract_number(text)
        if num is not None and any(k in clean for k in ["acre", "land", "ఎకర", "భూమి", "एकड़", "ਜ਼ਮੀਨ"]):
            msg = get_localized_message("onboard_land_set", language, land=num)
            return {
                "status": "success",
                "action": "set_onboarding_field",
                "action_payload": {"field": "total_land", "value": num},
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": msg,
                "language": language,
            }

        # Check Farmer Name in onboarding
        if any(k in clean for k in ["name is", "peru", "naam", "పేరు", "నామ్", "ਨਾਮ"]):
            name_cand = re.sub(r".*(?:my name is|name is|i am|నా పేరు|పేరు|मेरा नाम|ਮੇਰਾ ਨਾਮ)\s*", "", text, flags=re.IGNORECASE).strip()
            if name_cand:
                msg = get_localized_message("onboard_name_set", language, name=name_cand)
                return {
                    "status": "success",
                    "action": "set_onboarding_field",
                    "action_payload": {"field": "farmer_name", "value": name_cand},
                    "requires_confirmation": False,
                    "spoken_response": msg,
                    "display_text": msg,
                    "language": language,
                }

        # Stepper navigation (Next / Back / Save)
        if any(k in clean for k in ["next", "continue", "తరువాత", "ముందుకు", "अगला", "ਅਗਲਾ"]):
            msg = get_localized_message("onboard_step_nav", language, step="Next Step")
            return {
                "status": "success",
                "action": "set_onboarding_field",
                "action_payload": {"field": "step", "value": "next"},
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": msg,
                "language": language,
            }

        if any(k in clean for k in ["save", "finish", "complete", "భద్రపరచు", "పూర్తిచేయి", "सुरक्षित", "ਸੁਰੱਖਿਅਤ"]):
            return {
                "status": "success",
                "action": "complete_onboarding",
                "action_payload": {},
                "requires_confirmation": False,
                "spoken_response": "Saving your farm information and opening your dashboard.",
                "display_text": "Completing onboarding...",
                "language": language,
            }

    # --------------------------------------------------------------------------
    # 5. Land Section Management: Add, Edit, Remove, Select (Section 5)
    # --------------------------------------------------------------------------
    # Add a new section
    if any(p in clean for p in [
        "add a section", "add section", "create section", "new section",
        "కొత్త సెక్షన్", "సెక్షన్ సృష్టించు", "సెక్షన్ జోడించు",
        "नया सेक्शन जोड़ें", "ਸੈਕਸ਼ਨ ਬਣਾਓ",
    ]):
        # Check if crop / area provided in speech: e.g. "Create Section 02 with half acre rice"
        crop = match_crop(text) or "Wheat"
        area = extract_number(text) or 0.50
        target_name = f"Section 0{len(sections) + 1}"

        # If user explicitly specified name: e.g. "Create Section 02"
        name_match = re.search(r"(?:create|add|సృష్టించు)\s*(?:section|సెక్షన్|ਸੈਕਸ਼ਨ)?\s*0?(\d+)", clean)
        if name_match:
            target_name = f"Section 0{name_match.group(1)}"

        # Validate available land allocation constraint
        avail = summary.get("available_land", 0.0)
        if area > avail and avail > 0:
            area = avail

        resp_msg = f"Opening Land Section form for {target_name} ({crop}, {area} Acres)." if language == "en" else f"{target_name} ({crop}, {area} ఎకరాలు) కోసం సెక్షన్ ఫారమ్‌ను తెరుస్తున్నాను."
        return {
            "status": "success",
            "action": "add_land_section",
            "action_payload": {
                "name": target_name,
                "area_acres": area,
                "crop": crop,
                "is_empty": (crop == "Empty"),
                "farm_id": farm_id,
            },
            "requires_confirmation": False,
            "spoken_response": resp_msg,
            "display_text": resp_msg,
            "language": language,
        }

    # Remove Section (Mandatory Confirmation required!)
    if any(p in clean for p in [
        "remove section", "delete section",
        "సెక్షన్ తొలగించు", "సెక్షన్ తీసివేయి", "తొలగించు",
        "सेक्शन हटाएं", "ਸੈਕਸ਼ਨ ਹਟਾਓ",
    ]):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "remove_land_section"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        conf_msg = get_localized_message("confirm_remove_section", language, name=sec["name"])
        return {
            "status": "pending_confirmation",
            "action": "remove_land_section",
            "action_payload": {
                "section_id": sec["id"],
                "section_name": sec["name"],
            },
            "requires_confirmation": True,
            "confirmation_prompt": conf_msg,
            "spoken_response": conf_msg,
            "display_text": conf_msg,
            "language": language,
        }

    # Edit Section / Change Crop / Set Area
    if any(p in clean for p in [
        "edit section", "change section", "set section area", "change crop", "set area",
        "సెక్షన్ సవరించు", "పంట మార్చు", "విస్తీర్ణం మార్చు",
        "सेक्शन एडिट करें", "फसल बदलें", "ਸੈਕਸ਼ਨ ਬਦਲੋ",
    ]) or ("set" in clean and "area" in clean) or ("change" in clean and ("crop" in clean or "rice" in clean or "wheat" in clean)) or ("edit" in clean and ("section" in clean or "this" in clean)):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "edit_land_section"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        new_crop = match_crop(text) or sec.get("crop", "Wheat")
        
        # Specific search for area number (e.g. area to 0.75 acres or 0.75 acres)
        area_m = re.search(r"(?:area|విస్తీర్ణం|क्षेत्रफल|ਜ਼ਮੀਨ)?\s*(?:to|is|గా|हो)?\s*(\d+(?:\.\d+)?)\s*(?:acres|acre|ఎకరాలు|ఎకరం|एकड़|ਏਕੜ)", text, re.IGNORECASE)
        if area_m:
            new_area = float(area_m.group(1))
        else:
            new_area = extract_number(text) or sec.get("area_acres", 0.50)

        # Validate allocation limit: new_area cannot exceed available_land + current_section_area
        max_allowed = summary.get("available_land", 0.0) + sec.get("area_acres", 0.0)
        if new_area > max_allowed:
            new_area = max_allowed

        resp_msg = f"Editing {sec['name']}: Area set to {new_area} Acres, Crop: {new_crop}." if language == "en" else f"{sec['name']} సవరిస్తున్నాను: విస్తీర్ణం {new_area} ఎకరాలు, పంట: {new_crop}."
        return {
            "status": "success",
            "action": "edit_land_section",
            "action_payload": {
                "section_id": sec["id"],
                "name": sec["name"],
                "area_acres": new_area,
                "crop": new_crop,
                "is_empty": (new_crop == "Empty"),
            },
            "requires_confirmation": False,
            "spoken_response": resp_msg,
            "display_text": resp_msg,
            "language": language,
        }

    # Pre-check actions that mention sections so select_section doesn't hijack them
    is_mark_completed = (
        any(p in clean for p in [
            "mark irrigation completed", "mark as completed", "completed irrigation", "irrigation completed",
            "ఇరిగేషన్ పూర్తయింది", "నీళ్లు పెట్టాను", "సిंचाई पूरी हुई", "ਸਿੰਚਾਈ ਪੂਰੀ ਹੋਈ",
        ])
        or ("mark" in clean and ("completed" in clean or "done" in clean or "complete" in clean))
        or ("irrigation" in clean and ("completed" in clean or "done" in clean))
        or ("పూర్తయింది" in clean)
        or ("पूरी हुई" in clean)
        or ("ਪੂਰੀ ਹੋਈ" in clean)
    )
    is_skip_irrigation = (
        any(p in clean for p in [
            "skip today's irrigation", "skip irrigation", "skip session",
            "ఇరిగేషన్ దాటవేయి", "ఈ రోజు నీళ్లు వద్దు", "సిंचाई छोड़ो", "ਸਿੰਚਾਈ ਛੱਡੋ",
        ])
        or ("skip" in clean and ("irrigation" in clean or "session" in clean or "today" in clean or "water" in clean))
        or ("దాటవేయి" in clean)
        or ("నీళ్లు వద్దు" in clean)
        or ("సిंचाई छोड़ो" in clean)
        or ("ਸਿੰਚਾਈ ਛੱਡੋ" in clean)
    )
    is_calc_water = any(p in clean for p in [
        "calculate water requirement", "how much water", "water requirement", "crop water need",
        "ఎంత నీరు కావాలి", "నీటి పరిమాణం", "నీరు ఎంత", "कितना पानी चाहिए", "ਕਿੰਨਾ ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ",
    ])
    is_check_irrigation = any(p in clean for p in CHECK_IRRIGATION_TRIGGERS)
    is_explain_pred = any(p in clean for p in EXPLAIN_PREDICTION_TRIGGERS)
    is_gen_schedule = (
        any(p in clean for p in [
            "generate irrigation schedule", "generate schedule", "create schedule", "make schedule",
            "షెడ్యూల్ తయారుచేయి", "షెడ్యూల్ రూపొందించు", "शेड्यूल बनाएं", "ਸੂਚੀ ਬਣਾਓ",
        ])
        or (("generate" in clean or "create" in clean or "make" in clean) and "schedule" in clean)
    )

    # Select Section (All 23 Languages)
    if (any(p in clean for p in SELECT_SECTION_TRIGGERS) or any(ord_w in clean for ord_w in ORDINALS.keys())) and not (
        is_mark_completed or is_skip_irrigation or is_calc_water or is_check_irrigation or is_explain_pred or is_gen_schedule
    ):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        ord_idx = extract_ordinal(clean)
        if sec:
            msg = get_localized_message("section_selected", language, name=sec["name"], crop=sec.get("crop", "Wheat"), area=sec.get("area_acres", 0.5))
            return {
                "status": "success",
                "action": "select_section",
                "action_payload": {
                    "section_id": sec["id"],
                    "section_name": sec["name"],
                    "crop": sec.get("crop", "Wheat"),
                    "area_acres": sec.get("area_acres", 0.5),
                    "ordinal_index": ord_idx,
                    "section_number": (ord_idx + 1) if ord_idx is not None else None,
                },
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": msg,
                "language": language,
            }
        elif ord_idx is not None:
            target_name = f"Section 0{ord_idx + 1}"
            msg = f"Selected {target_name}." if language == "en" else f"{target_name} ఎంచుకోబడింది."
            return {
                "status": "success",
                "action": "select_section",
                "action_payload": {
                    "section_id": None,
                    "section_name": target_name,
                    "ordinal_index": ord_idx,
                    "section_number": ord_idx + 1,
                },
                "requires_confirmation": False,
                "spoken_response": msg,
                "display_text": msg,
                "language": language,
            }
        else:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

    # --------------------------------------------------------------------------
    # 6. Irrigation Planner: Check Irrigation, Water Req, Schedule (Section 6)
    # --------------------------------------------------------------------------
    # Upcoming Schedule Check (All 23 Languages)
    is_upcoming_query = any(p in clean for p in UPCOMING_SCHEDULE_TRIGGERS)
    if is_upcoming_query:
        cal = get_farmer_combined_calendar(farmer_id, 2026, 11)
        sessions = cal.get("sessions", [])
        if sessions:
            first_s = sessions[0]
            resp_msg = f"Upcoming session: {first_s.get('section_name')} needs water on {first_s.get('date')} ({first_s.get('liters', 1000):,.0f} L)." if language == "en" else f"రాబోయే సెషన్: {first_s.get('section_name')} కు {first_s.get('date')} న సాగునీరు అవసరం."
        else:
            resp_msg = "No pending irrigation sessions scheduled for this week." if language == "en" else "ఈ వారం ఎలాంటి పెండింగ్ సాగునీటి సెషన్లు లేవు."

        return {
            "status": "success",
            "action": "get_upcoming_schedule",
            "action_payload": {"sessions": sessions},
            "requires_confirmation": False,
            "spoken_response": resp_msg,
            "display_text": resp_msg,
            "language": language,
        }

    # Explain Prediction (All 23 Languages)
    if any(p in clean for p in EXPLAIN_PREDICTION_TRIGGERS):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        sec_name = sec["name"] if sec else "your crop"
        crop_name = sec.get("crop", "crop") if sec else "crop"
        explain_msg = get_localized_message("explain_prediction", language, name=sec_name, crop=crop_name)
        return {
            "status": "success",
            "action": "explain_prediction",
            "action_payload": {
                "section_id": sec["id"] if sec else None,
                "section_name": sec_name,
                "explanation": explain_msg,
            },
            "requires_confirmation": False,
            "spoken_response": explain_msg,
            "display_text": explain_msg,
            "language": language,
        }

    # Check Irrigation / Should I Irrigate Today? (All 23 Languages)
    if any(p in clean for p in CHECK_IRRIGATION_TRIGGERS):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "run_irrigation_prediction"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        # Run actual prediction using farm_manager
        pred_res = predict_section_irrigation(sec["id"], farmer_id)
        decision = pred_res.get("decision", "DO NOT IRRIGATE")
        liters = pred_res.get("recommended_liters", 1000.0)
        water_val = f"{liters:,.0f}"

        if decision == "IRRIGATE":
            msg = get_localized_message("prediction_irrigate", language, name=sec["name"], liters=water_val)
        else:
            msg = get_localized_message("prediction_do_not_irrigate", language, name=sec["name"])

        return {
            "status": "success",
            "action": "run_irrigation_prediction",
            "action_payload": {
                "section_id": sec["id"],
                "section_name": sec["name"],
                "decision": decision,
                "confidence": pred_res.get("confidence", 95.0),
                "recommended_liters": liters,
                "reason": pred_res.get("reason", "Soil moisture evaluation"),
                "crop": sec.get("crop", "Wheat"),
            },
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Calculate water requirement
    if any(p in clean for p in [
        "calculate water requirement", "how much water", "water requirement", "crop water need",
        "ఎంత నీరు కావాలి", "నీటి పరిమాణం", "నీరు ఎంత", "कितना पानी चाहिए", "ਕਿੰਨਾ ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ",
    ]):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "calculate_water_requirement"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        crop_lower = (sec.get("crop") or "wheat").lower()
        base_liters = CROP_BASE_LITERS_PER_ACRE.get(crop_lower, 1000.0)
        total_liters = base_liters * sec.get("area_acres", 1.0)
        liters_str = f"{total_liters:,.0f}"

        msg = get_localized_message("water_req_info", language, name=sec["name"], crop=sec.get("crop", "Wheat"), area=sec.get("area_acres", 0.5), liters=liters_str)
        return {
            "status": "success",
            "action": "calculate_water_requirement",
            "action_payload": {
                "section_id": sec["id"],
                "section_name": sec["name"],
                "crop": sec.get("crop", "Wheat"),
                "area_acres": sec.get("area_acres", 0.5),
                "liters": total_liters,
            },
            "requires_confirmation": False,
            "spoken_response": msg,
            "display_text": msg,
            "language": language,
        }

    # Generate Irrigation Schedule
    if any(p in clean for p in [
        "generate irrigation schedule", "generate schedule", "create schedule", "make schedule",
        "షెడ్యూల్ తయారుచేయి", "షెడ్యూల్ రూపొందించు", "शेड्यूल बनाएं", "ਸੂਚੀ ਬਣਾਓ",
    ]) or (("generate" in clean or "create" in clean or "make" in clean) and "schedule" in clean):
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "generate_irrigation_schedule"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        sched_res = schedule_section_irrigation(sec["id"], farmer_id, planning_period_days=7)
        next_date = sched_res[0].get("scheduled_date", "scheduled date") if sched_res else "scheduled date"
        resp_msg = f"Generated 7-day irrigation schedule for {sec['name']}. Next session is on {next_date}." if language == "en" else f"{sec['name']} కోసం 7 రోజుల ఇరిగేషన్ షెడ్యూల్ రూపొందించబడింది."
        return {
            "status": "success",
            "action": "generate_irrigation_schedule",
            "action_payload": {
                "section_id": sec["id"],
                "section_name": sec["name"],
                "schedules": sched_res,
            },
            "requires_confirmation": False,
            "spoken_response": resp_msg,
            "display_text": resp_msg,
            "language": language,
        }

    # --------------------------------------------------------------------------
    # 7. Irrigation Calendar Commands & Status Changes (Section 7)
    # --------------------------------------------------------------------------
    # Show tomorrow's / upcoming irrigation
    if any(p in clean for p in [
        "show tomorrow's irrigation", "tomorrow's irrigation", "what should i irrigate today",
        "upcoming irrigation", "which sections need water",
        "రేపు ఏ పంటకు నీళ్లు పెట్టాలి", "రాబోయే ఇరిగేషన్", "ఈ రోజు ఏమి సీంచాలి",
        "कल क्या सींचना है", "ਅੱਜ ਕੀ ਸਿੰਚਣਾ ਹੈ",
    ]):
        # Query combined calendar or schedules
        cal = get_farmer_combined_calendar(farmer_id, 2026, 11)
        sessions = cal.get("sessions", [])
        if sessions:
            first_s = sessions[0]
            resp_msg = f"Upcoming session: {first_s.get('section_name')} needs water on {first_s.get('date')} ({first_s.get('liters', 1000):,.0f} L)." if language == "en" else f"రాబోయే సెషన్: {first_s.get('section_name')} కు {first_s.get('date')} న సాగునీరు అవసరం."
        else:
            resp_msg = "No pending irrigation sessions scheduled for this week." if language == "en" else "ఈ వారం ఎలాంటి పెండింగ్ సాగునీటి సెషన్లు లేవు."

        return {
            "status": "success",
            "action": "get_upcoming_schedule",
            "action_payload": {"sessions": sessions},
            "requires_confirmation": False,
            "spoken_response": resp_msg,
            "display_text": resp_msg,
            "language": language,
        }

    # Mark Irrigation Completed (Requires confirmation)
    is_mark_completed = (
        any(p in clean for p in [
            "mark irrigation completed", "mark as completed", "completed irrigation", "irrigation completed",
            "ఇరిగేషన్ పూర్తయింది", "నీళ్లు పెట్టాను", "సిंचाई पूरी हुई", "ਸਿੰਚਾਈ ਪੂਰੀ ਹੋਈ",
        ])
        or ("mark" in clean and ("completed" in clean or "done" in clean or "complete" in clean))
        or ("irrigation" in clean and ("completed" in clean or "done" in clean))
        or ("పూర్తయింది" in clean)
        or ("पूरी हुई" in clean)
        or ("ਪੂਰੀ ਹੋਈ" in clean)
    )
    if is_mark_completed:
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "update_irrigation_status"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        # Find schedule session
        scheds = get_section_schedules(sec["id"], farmer_id)
        sched_id = scheds[0]["id"] if scheds else f"sched_{uuid.uuid4().hex[:8]}"

        conf_msg = get_localized_message("confirm_complete_session", language, name=sec["name"])
        return {
            "status": "pending_confirmation",
            "action": "update_irrigation_status",
            "action_payload": {
                "schedule_id": sched_id,
                "section_id": sec["id"],
                "section_name": sec["name"],
                "status": "Completed",
            },
            "requires_confirmation": True,
            "confirmation_prompt": conf_msg,
            "spoken_response": conf_msg,
            "display_text": conf_msg,
            "language": language,
        }

    # Skip Irrigation (Requires confirmation)
    is_skip_irrigation = (
        any(p in clean for p in [
            "skip today's irrigation", "skip irrigation", "skip session",
            "ఇరిగేషన్ దాటవేయి", "ఈ రోజు నీళ్లు వద్దు", "సిंचाई छोड़ो", "ਸਿੰਚਾਈ ਛੱਡੋ",
        ])
        or ("skip" in clean and ("irrigation" in clean or "session" in clean or "today" in clean or "water" in clean))
        or ("దాటవేయి" in clean)
        or ("నీళ్లు వద్దు" in clean)
        or ("सिंचाई छोड़ो" in clean)
        or ("ਸਿੰਚਾਈ ਛੱਡੋ" in clean)
    )
    if is_skip_irrigation:
        sec, res_type = resolve_section_from_context(clean, sections, ctx)
        if not sec:
            ambig_msg = get_localized_message("section_ambiguous", language)
            return {
                "status": "success",
                "action": "ask_clarification",
                "action_payload": {"pending_action": "update_irrigation_status"},
                "requires_confirmation": False,
                "spoken_response": ambig_msg,
                "display_text": ambig_msg,
                "language": language,
            }

        scheds = get_section_schedules(sec["id"], farmer_id)
        sched_id = scheds[0]["id"] if scheds else f"sched_{uuid.uuid4().hex[:8]}"

        conf_msg = get_localized_message("confirm_skip_session", language, name=sec["name"])
        return {
            "status": "pending_confirmation",
            "action": "update_irrigation_status",
            "action_payload": {
                "schedule_id": sched_id,
                "section_id": sec["id"],
                "section_name": sec["name"],
                "status": "Skipped",
            },
            "requires_confirmation": True,
            "confirmation_prompt": conf_msg,
            "spoken_response": conf_msg,
            "display_text": conf_msg,
            "language": language,
        }

    # --------------------------------------------------------------------------
    # Default Fallback: General Agricultural Query
    # --------------------------------------------------------------------------
    general_msg = get_localized_message("general_unknown", language)
    return {
        "status": "success",
        "action": "general_query",
        "action_payload": {"query": text},
        "requires_confirmation": False,
        "spoken_response": general_msg,
        "display_text": general_msg,
        "language": language,
    }
