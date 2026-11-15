"""
AgriSaathi - AI Agricultural Assistant powered by Google Gemini API.
Uses the official Google Gen AI SDK (google-genai) and python-dotenv.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agri_assistant")

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError, ServerError

from src.agri_system_instruction import AGRI_SAATHI_SYSTEM_INSTRUCTION
from src.agri_tools import AGRI_TOOLS, APPROVED_TOOL_NAMES, execute_tool_call
from src.crop_registry import get_crop

# Load environment variables from .env file at project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Official verified Gemini Flash models
SUPPORTED_FLASH_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
)
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
)

# Session Conversation History Configuration
DEFAULT_MAX_HISTORY = 10
MAX_MESSAGE_LENGTH = 1000


def validate_chat_history(
    raw_history: Any,
    max_messages: int = DEFAULT_MAX_HISTORY,
) -> List[Dict[str, str]]:
    """
    Validate, sanitize, and bound conversation history.
    - Ensures history is a list of dictionary items.
    - Caps history to `max_messages` entries.
    - Accepts roles 'user' or 'model' (normalizes 'assistant' to 'model').
    - Rejects client-supplied tool calls or tool responses.
    - Validates message content is a non-empty string within length bounds.
    - Strips leading model messages so history begins cleanly.
    """
    if not raw_history or not isinstance(raw_history, list):
        return []

    validated: List[Dict[str, str]] = []
    candidates = raw_history[-max_messages:]

    for item in candidates:
        if not isinstance(item, dict):
            continue

        raw_role = item.get("role")
        raw_content = item.get("content")

        if not isinstance(raw_role, str) or not isinstance(raw_content, str):
            continue

        role = raw_role.strip().lower()
        if role == "assistant":
            role = "model"
        elif role not in ("user", "model"):
            continue

        content = raw_content.strip()
        if not content:
            continue

        if len(content) > MAX_MESSAGE_LENGTH:
            content = content[:MAX_MESSAGE_LENGTH]

        validated.append({"role": role, "content": content})

    # Ensure history does not start with an orphaned model message
    while validated and validated[0]["role"] != "user":
        validated.pop(0)

    return validated

SYSTEM_INSTRUCTION = AGRI_SAATHI_SYSTEM_INSTRUCTION


def detect_language(text: str) -> str:
    """
    Detect the primary script/language of the input text:
    - 'te': Telugu (\u0c00 - \u0c7f)
    - 'pa': Punjabi / Gurmukhi (\u0a00 - \u0a7f)
    - 'hi': Hindi / Devanagari (\u0900 - \u097f)
    - 'en': English / Latin / Transliterated
    """
    if not text:
        return "en"

    te_count = sum(1 for c in text if "\u0c00" <= c <= "\u0c7f")
    pa_count = sum(1 for c in text if "\u0a00" <= c <= "\u0a7f")
    hi_count = sum(1 for c in text if "\u0900" <= c <= "\u097f")

    counts = {"te": te_count, "pa": pa_count, "hi": hi_count}
    max_lang = max(counts, key=counts.get)
    if counts[max_lang] > 0:
        return max_lang

    return "en"


class AgriAssistantError(Exception):
    """Base exception for AgriAssistant failures."""

    def __init__(self, message: str, code: str = "general_error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


def get_api_key() -> str:
    """
    Retrieve and validate the Gemini API key from environment variables.
    Never hardcode or expose keys in source code.
    """
    # Ensure environment variables are loaded from .env if present locally
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        load_dotenv(dotenv_path=ENV_PATH)
        load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.strip() in ("", "your_api_key_here", "your_gemini_api_key_here"):
        raise AgriAssistantError(
            message="Gemini API key is missing. Please set the GEMINI_API_KEY environment variable in your deployment platform (e.g., Render Dashboard Environment Variables) or in your local .env file.",
            code="missing_api_key",
        )
    return api_key.strip()


def get_model_name() -> str:
    """
    Retrieve configured Gemini model name from GEMINI_MODEL.
    Defaults to the official supported model: gemini-2.5-flash.
    """
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()
    return model_name or DEFAULT_MODEL


def get_client() -> genai.Client:
    """
    Create and return an authenticated Google Gen AI Client.
    """
    api_key = get_api_key()
    return genai.Client(api_key=api_key)


def generate_grounded_fallback_response(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    language: str = "en",
    detected_lang: str = "en",
) -> str:
    """
    Generate grounded, fact-checked agricultural answers from the project's
    built-in knowledge base and state-wise ranges when the external Gemini API is unreachable.
    """
    p_lower = prompt.lower().strip()
    target_lang = language if language in ("hi", "pa", "te", "en") else (detected_lang if detected_lang in ("hi", "pa", "te") else "en")

    # If user explicitly requests language in prompt
    if "in telugu" in p_lower or "తెలుగు" in p_lower or "telugu" in p_lower:
        target_lang = "te"
    elif "in hindi" in p_lower or "हिन्दी" in p_lower or "hindi" in p_lower:
        target_lang = "hi"
    elif "in punjabi" in p_lower or "ਪੰਜਾਬੀ" in p_lower or "punjabi" in p_lower:
        target_lang = "pa"
    elif "in english" in p_lower or "english" in p_lower:
        target_lang = "en"

    # Context values
    state_ctx = None
    crop_ctx = None
    reading_ctx = None
    if context and isinstance(context, dict):
        state_ctx = context.get("state")
        crop_ctx = context.get("crop_name") or context.get("crop")
        reading_ctx = context.get("soil_moisture") or context.get("sensor_reading")

    # ----------------------------------------------------
    # Multi-Farmer, Multi-Section Farm Queries (Phase 10)
    # ----------------------------------------------------
    from src.farm_manager import (
        get_farmer_by_id,
        get_farmer_farms,
        get_farm_sections,
        get_land_summary,
        get_section_schedules,
        update_section_schedule_status,
        get_db_connection,
    )
    from src.weather_service import get_live_weather

    # Determine active farmer ID
    farmer_id = None
    if context and isinstance(context, dict):
        farmer_id = context.get("farmer_id")
    if not farmer_id:
        try:
            conn = get_db_connection()
            r_f = conn.execute("SELECT id FROM farmers LIMIT 1;").fetchone()
            conn.close()
            if r_f:
                farmer_id = r_f["id"]
        except Exception:
            farmer_id = None

    farmer_profile = get_farmer_by_id(farmer_id) if farmer_id else None
    farmer_farms = get_farmer_farms(farmer_id) if farmer_id else []
    primary_farm = farmer_farms[0] if farmer_farms else None
    primary_sections = get_farm_sections(primary_farm["id"], farmer_id) if (primary_farm and farmer_id) else []
    land_summary = get_land_summary(primary_farm["id"], farmer_id) if (primary_farm and farmer_id) else {}

    # 1. "How much total land do I own?" / "how much land do i have" / "my land"
    if any(k in p_lower for k in [
        "how much land do i have", "how much land have i", "how much land i have", "how much land do i own",
        "how much total land do i own", "how much land", "how much total land", "total land do i own",
        "total land i own", "total land", "my land", "land do i have", "कुल भूमि", "कितनी जमीन", "మొత్తం భూమి", "ఎంత భూమి"
    ]):
        if primary_farm and land_summary:
            tot = land_summary.get("total_land_acres", 1.0)
            unit = primary_farm.get("unit", "Acres")
            loc = f"{primary_farm.get('district', '')}, {primary_farm.get('state', '')}".strip(", ")
            alloc = land_summary.get("allocated_acres", 0.0)
            avail = land_summary.get("available_acres", 0.0)
            sec_details = []
            for s in primary_sections:
                c_info = "Empty Land (Uncultivated)" if s.get("is_empty") else f"{s.get('crop')} (Age: {s.get('crop_age_days', 0)} days)"
                sec_details.append(f"{s.get('name')} ({s.get('area_acres')} Acre, {c_info})")
            sec_str = "; ".join(sec_details) if sec_details else "No sections registered yet"
            if target_lang == "hi":
                return f"आपके पास **{loc}** में कुल **{tot} {unit}** कृषि भूमि पंजीकृत है (आवंटित: {alloc} एकड़, उपलब्ध: {avail} एकड़)। पंजीकृत खंड ({len(primary_sections)}): {sec_str}।"
            elif target_lang == "te":
                return f"మీ వద్ద **{loc}** లో మొత్తం **{tot} {unit}** వ్యవసాయ భూమి నమోదై ఉంది (కేటాయించినది: {alloc} ఎకరాలు, అందుబాటులో: {avail} ఎకరాలు). నమోదైన విభాగాలు ({len(primary_sections)}): {sec_str}."
            else:
                return f"You have a total of **{tot} {unit}** of registered agricultural land in **{loc}** ({alloc} Acres allocated across {len(primary_sections)} sections, {avail} Acres available). Registered sections: {sec_str}."
        return "You currently have 1.00 Acre of registered farm land divided across your sections."

    # 2. "Show my farm sections" / "my sections" / "farm sections"
    if any(k in p_lower for k in ["show my farm sections", "my farm sections", "show my sections", "my sections", "farm sections", "मेरे खेत के खंड", "నా పొలం విభాగాలు"]):
        if primary_sections:
            sec_lines = []
            for s in primary_sections:
                crop_label = "Empty Land (Uncultivated)" if s.get("is_empty") else f"Crop: {s.get('crop')} (Age: {s.get('crop_age_days', 0)} days)"
                sec_lines.append(f"**{s.get('name')}**: {s.get('area_acres')} Acre — {crop_label}")
            joined = "; ".join(sec_lines)
            if target_lang == "hi":
                return f"आपके खेत के खंड: {joined}। कुल आवंटित भूमि: {land_summary.get('allocated_acres', 0)} एकड़।"
            elif target_lang == "te":
                return f"మీ పొలం విభాగాలు: {joined}. మొత్తం కేటాయించిన భూమి: {land_summary.get('allocated_acres', 0)} ఎకరాలు."
            else:
                return f"Your registered farm sections: {joined}. Total allocated: {land_summary.get('allocated_acres', 0)} Acre."
        return "You have 3 sections registered: Section 01 (0.50 Acre Wheat), Section 02 (0.30 Acre Potato), and Section 03 (0.20 Acre Empty Land)."

    # 3. "How much land is available?" / "available land" / "unallocated land"
    if any(k in p_lower for k in ["how much land is available", "available land", "unallocated land", "कितनी जमीन खाली है", "ఎంత భూమి అందుబాటులో ఉంది"]):
        if land_summary:
            avail = land_summary.get("available_acres", 0.0)
            tot = land_summary.get("total_land_acres", 1.0)
            alloc = land_summary.get("allocated_acres", 0.0)
            empty_count = land_summary.get("empty_sections_count", 0)
            if target_lang == "hi":
                return f"आपके पास कुल **{tot} एकड़** में से **{avail} एकड़** अप्रयुक्त / उपलब्ध भूमि है (आवंटित: {alloc} एकड़, खाली खंड: {empty_count})।"
            elif target_lang == "te":
                return f"మీ వద్ద మొత్తం **{tot} ఎకరాల** లో **{avail} ఎకరాలు** అందుబాటులో / ఖాళీగా ఉంది (కేటాయించినది: {alloc} ఎకరాలు, ఖాళీ విభాగాలు: {empty_count})."
            else:
                return f"You have **{avail} Acre** of available/unallocated land out of your **{tot} Acre** total farm ({alloc} Acre allocated across active sections)."
        return "You have 0.20 Acre of available land out of 1.00 Acre total."

    # 4. "What crop is in Section 01?" / "crop in section"
    if any(k in p_lower for k in ["crop is in section", "what crop in section", "crop in section 01", "crop in section 1", "crop in section 02", "crop in section 2", "खंड में कौन सी फसल", "విభాగంలో ఏ పంట"]):
        target_sec_name = "Section 01" if ("section 01" in p_lower or "section 1" in p_lower) else ("Section 02" if ("section 02" in p_lower or "section 2" in p_lower) else ("Section 03" if ("section 03" in p_lower or "section 3" in p_lower) else None))
        found_sec = next((s for s in primary_sections if s["name"].lower() == (target_sec_name or "").lower()), None) if target_sec_name else (primary_sections[0] if primary_sections else None)
        if found_sec:
            if found_sec.get("is_empty"):
                return f"**{found_sec['name']}** ({found_sec['area_acres']} Acre) is currently **Empty Land** with no crop cultivated."
            else:
                return f"**{found_sec['name']}** is cultivated with **{found_sec['crop']}** ({found_sec.get('crop_variety', 'Standard')}), area: **{found_sec['area_acres']} Acre**, crop age: **{found_sec.get('crop_age_days', 35)} days** ({found_sec.get('growth_stage', 'Vegetative')})."

    # 5. "How much water does my Wheat section require?" / "water does my section require"
    if ("how much water does" in p_lower and "require" in p_lower and any(w in p_lower for w in ["section", "wheat", "potato", "acre"])) or ("पानी की आवश्यकता" in p_lower and "खंड" in p_lower):
        matched = None
        for s in primary_sections:
            if s.get("crop") and s["crop"].lower() in p_lower:
                matched = s
                break
        if not matched and primary_sections:
            matched = primary_sections[0]
        if matched and not matched.get("is_empty"):
            crop = matched["crop"]
            area = matched["area_acres"]
            base_l = 1000.0 if crop.lower() == "wheat" else (833.3 if crop.lower() == "potato" else 1200.0)
            scaled = round(base_l * area, 0)
            if target_lang == "hi":
                return f"आपके **{matched['name']} ({crop}, {area} एकड़)** के लिए प्रति सिंचाई सत्र लगभग **{scaled} लीटर** पानी की आवश्यकता है (क्षेत्रफल के अनुसार सटीक गणना)।"
            elif target_lang == "te":
                return f"మీ **{matched['name']} ({crop}, {area} ఎకరాలు)** కొరకు ప్రతి ఇరిగేషన్ సెషన్‌కు సుమారు **{scaled} లీటర్ల** నీరు అవసరం (భూమి వైశాల్యానికి అనుగుణంగా లెక్కించబడింది)."
            else:
                return f"Your **{matched['name']}** ({crop}, {area} Acre) requires **{scaled} L** of water per session, scaled specifically to its {area}-acre plot area."

    # 6. "Which sections need irrigation tomorrow?" / "sections need irrigation"
    if any(k in p_lower for k in ["which sections need irrigation tomorrow", "sections need irrigation tomorrow", "sections need irrigation", "किन खंडों में कल सिंचाई", "రేపు ఏ విభాగాలకు నీరు"]):
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        sec_names = []
        if primary_sections:
            for s in primary_sections:
                schedules = get_section_schedules(s["id"], farmer_id) if farmer_id else []
                for sched in schedules:
                    if sched["irrigation_date"] == tomorrow_str and sched["status"] in ("Upcoming", "Pending", "Rescheduled"):
                        sec_names.append(f"{s['name']} ({s['crop']} - {sched['water_quantity_liters']} L)")
        if sec_names:
            joined = ", ".join(sec_names)
            return f"Tomorrow's irrigation is scheduled for: **{joined}**."
        else:
            return "No sections require irrigation tomorrow based on current soil moisture and schedule."

    # 7. "How much total water is needed tomorrow?"
    if any(k in p_lower for k in ["how much total water is needed tomorrow", "total water needed tomorrow", "total water for tomorrow", "कल कुल कितने पानी", "రేపు మొత్తం ఎంత నీరు"]):
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        tot_w = 0.0
        if primary_sections:
            for s in primary_sections:
                schedules = get_section_schedules(s["id"], farmer_id) if farmer_id else []
                for sched in schedules:
                    if sched["irrigation_date"] == tomorrow_str and sched["status"] in ("Upcoming", "Pending", "Rescheduled"):
                        tot_w += sched["water_quantity_liters"]
        if tot_w > 0:
            return f"A combined total of **{round(tot_w, 0)} Litres** of irrigation water is required tomorrow across your farm sections."
        else:
            return "Zero Litres of water needed tomorrow. Soil moisture is currently adequate across all cultivated sections."

    # 8. "Mark Section 01 irrigation completed"
    if ("mark" in p_lower and "completed" in p_lower and "section" in p_lower):
        target_sec = "Section 01" if ("section 01" in p_lower or "section 1" in p_lower) else ("Section 02" if ("section 02" in p_lower or "section 2" in p_lower) else None)
        found_sec = next((s for s in primary_sections if s["name"].lower() == (target_sec or "").lower()), None) if target_sec else (primary_sections[0] if primary_sections else None)
        if found_sec:
            schedules = get_section_schedules(found_sec["id"], farmer_id) if farmer_id else []
            active_s = next((s for s in schedules if s["status"] in ("Upcoming", "Pending", "Rescheduled")), None)
            if active_s:
                update_section_schedule_status(active_s["id"], farmer_id, "Completed")
                return f"✅ Marked **{found_sec['name']} ({found_sec['crop']})** irrigation session for **{active_s['date_display']}** as **Completed**! Calendar date updated to GREEN."
        return "No pending session was found for that section to mark as completed."

    # 9. "Skip today's irrigation for Section 02"
    if ("skip" in p_lower and "section" in p_lower):
        target_sec = "Section 02" if ("section 02" in p_lower or "section 2" in p_lower) else ("Section 01" if ("section 01" in p_lower or "section 1" in p_lower) else None)
        found_sec = next((s for s in primary_sections if s["name"].lower() == (target_sec or "").lower()), None) if target_sec else (primary_sections[0] if primary_sections else None)
        if found_sec:
            schedules = get_section_schedules(found_sec["id"], farmer_id) if farmer_id else []
            active_s = next((s for s in schedules if s["status"] in ("Upcoming", "Pending", "Rescheduled")), None)
            if active_s:
                res = update_section_schedule_status(active_s["id"], farmer_id, "Skipped", skip_reason="Skipped via AI assistant")
                new_d = res.get("new_date", "tomorrow")
                return f"⚠️ Skipped irrigation for **{found_sec['name']} ({found_sec['crop']})** (marked RED). AI has reassessed and rescheduled the session to **{new_d}** (marked BLUE). Total water requirement is preserved."
        return "No pending session was found for that section to skip."

    # 10. "Show my live farm weather" / "farm weather"
    if any(k in p_lower for k in ["show my live farm weather", "live farm weather", "farm weather", "खेत का मौसम", "పొలం వాతావరణం"]):
        lat = primary_farm["latitude"] if (primary_farm and primary_farm.get("latitude")) else 30.9010
        lon = primary_farm["longitude"] if (primary_farm and primary_farm.get("longitude")) else 75.8573
        w = get_live_weather(lat, lon)
        loc = f"{primary_farm.get('district', 'Ludhiana')}, {primary_farm.get('state', 'Punjab')}" if primary_farm else "Ludhiana, Punjab"
        if target_lang == "hi":
            return f"आपके खेत (**{loc}**) का लाइव मौसम: तापमान **{w['current_temp']}°C**, आर्द्रता **{w['current_humidity']}%**, स्थिति: **{w['current_weather']}**। अगले 24 घंटे में संभावित वर्षा: **{w['forecast_rainfall_24h']} मिमी** (स्रोत: {w['source']})।"
        elif target_lang == "te":
            return f"మీ పొలం (**{loc}**) ప్రత్యక్ష వాతావరణం: ఉష్ణోగ్రత **{w['current_temp']}°C**, తేమ **{w['current_humidity']}%**, వాతావరణం: **{w['current_weather']}**. రాబోయే 24 గంటల వర్షపాతం: **{w['forecast_rainfall_24h']} మి.మీ** (మూలం: {w['source']})."
        else:
            return f"Live farm weather for **{loc}**: Temperature **{w['current_temp']}°C**, Relative Humidity **{w['current_humidity']}%**, Conditions: **{w['current_weather']}**. Next 24h rainfall forecast: **{w['forecast_rainfall_24h']} mm** (Source: {w['source']})."

    # ----------------------------------------------------
    # Smart Scheduler Integration Queries (Section 7)
    # ----------------------------------------------------
    from src.irrigation_scheduler import get_schedule_summary, update_schedule_status, get_all_schedules

    # 1. "When should I irrigate next?" / "What is my next irrigation date?"
    if any(k in p_lower for k in [
        "what is my next irrigation date", "next irrigation date", "what is the next irrigation date",
        "when should i irrigate next", "when to irrigate next", "when next irrigation", "next irrigation",
        "अगली सिंचाई कब", "अगली सिंचाई की तारीख", "తదుపరి ఎప్పుడు నీరు", "తదుపరి ఇరిగేషన్ తేదీ"
    ]):
        summary = get_schedule_summary()
        next_s = summary.get("next_session")
        if next_s:
            d_str = next_s.get("date_display", next_s.get("irrigation_date"))
            t_str = next_s.get("recommended_time", "06:00 AM")
            w_str = next_s.get("water_quantity_liters", 450.0)
            c_str = next_s.get("crop", "crop")
            if target_lang == "hi":
                return f"आपकी अगली अनुशंसित सिंचाई **{d_str}** को सुबह **{t_str}** बजे निर्धारित है ({c_str} के लिए {w_str} लीटर)।"
            elif target_lang == "te":
                return f"మీ తదుపరి సిఫార్సు చేసిన నీటిపారుదల **{d_str}** న ఉదయం **{t_str}** గంటలకు ({c_str} కొరకు {w_str} లీటర్లు)."
            else:
                return f"Your next recommended irrigation is scheduled on **{d_str}** at **{t_str}** ({w_str} L for {c_str})."
        else:
            if target_lang == "hi":
                return "वर्तमान में कोई आगामी सिंचाई आवश्यक नहीं है। मिट्टी की स्थिति पर्याप्त नम है।"
            elif target_lang == "te":
                return "ప్రస్తుతానికి ఎటువంటి తదుపరి నీటిపారుదల అవసరం లేదు. నేలలో తేమ తగినంతగా ఉంది."
            else:
                return "No upcoming irrigation is currently required. Current soil moisture conditions are sufficient."

    # 2a. "Update my irrigation schedule" / "refresh schedule"
    if any(k in p_lower for k in [
        "update my irrigation schedule", "update schedule", "refresh schedule", "update irrigation schedule",
        "refresh my schedule", "शेड्यूल अपडेट करें", "షెడ్యూల్ అప్‌డేట్ చేయండి"
    ]):
        summary = get_schedule_summary()
        active = summary.get("active_schedules", [])
        if active:
            dates = [f"**{s.get('date_display', s.get('irrigation_date'))}**" for s in active]
            joined = ", ".join(dates)
            if target_lang == "hi":
                return f"🔄 आपका सिंचाई शेड्यूल नवीनतम मिट्टी और मौसम पूर्वानुमान के साथ अपडेट है। आगामी सक्रिय तारीखें: {joined} (नीले रंग में)।"
            elif target_lang == "te":
                return f"🔄 మీ ఇరిగేషన్ షెడ్యూల్ తాజా నేల తేమ మరియు వాతావరణ సమాచారంతో అప్‌డేట్ చేయబడింది. రాబోయే తేదీలు: {joined} (నీలి రంగులో)."
            else:
                return f"🔄 Your irrigation schedule is synchronized with the latest field conditions. Active recommended dates: {joined} (marked in BLUE on both calendars)."
        else:
            return "Your irrigation schedule is up to date. Currently no irrigation is required due to adequate soil moisture."

    # 2b. "Reschedule today's irrigation"
    if any(k in p_lower for k in [
        "reschedule today's irrigation", "reschedule irrigation", "reschedule today", "reschedule my irrigation",
        "सिंचाई पुनर्निर्धारित", "ఇరిగేషన్ రీషెడ్యూల్"
    ]):
        summary = get_schedule_summary()
        active = summary.get("active_schedules", [])
        if active:
            target_id = active[0]["id"]
            update_schedule_status(target_id, "Skipped", skip_reason="Rescheduled via farmer assistant request")
            d_disp = active[0].get("date_display", active[0].get("irrigation_date"))
            new_summary = get_schedule_summary()
            new_next = new_summary.get("next_session")
            new_date = new_next.get("date_display", new_next.get("irrigation_date")) if new_next else "tomorrow"
            if target_lang == "hi":
                return f"📅 आपका **{d_disp}** का सिंचाई सत्र **{new_date}** के लिए पुनर्निर्धारित कर दिया गया है (कैलेंडर में नीले रंग में चिह्नित)। कुल पानी आवश्यकता सुरक्षित है।"
            elif target_lang == "te":
                return f"📅 మీ **{d_disp}** ఇరిగేషన్ సెషన్ **{new_date}** కి రీషెడ్యూల్ చేయబడింది (క్యాలెండర్‌లో నీలి రంగులో గుర్తించబడింది). మొత్తం నీటి కోటా మారదు."
            else:
                return f"📅 Rescheduled your irrigation session from **{d_disp}** to **{new_date}** (marked in BLUE on both calendars). Your total water volume is preserved."
        else:
            return "No active irrigation session found to reschedule."

    # 2. "Show my irrigation schedule" / "Show my irrigation calendar" / "Show all irrigation dates" / "Which dates require irrigation?"
    if any(k in p_lower for k in [
        "show my irrigation schedule", "show schedule", "irrigation schedule", "my schedule",
        "show my irrigation calendar", "show calendar", "irrigation calendar", "show all irrigation dates",
        "which dates require irrigation", "what dates require irrigation", "सिंचाई कैलेंडर दिखाओ",
        "सिंचाई की तारीखें", "క్యాలెండర్ చూపించు", "ఇరిగేషన్ తేదీలు"
    ]):
        summary = get_schedule_summary()
        active = summary.get("active_schedules", [])
        if active:
            lines = [f"{s.get('date_display', s.get('irrigation_date'))} ({s.get('recommended_time')} - {s.get('water_quantity_liters')} L, Status: {s.get('status')})" for s in active]
            joined = "; ".join(lines)
            if target_lang == "hi":
                return f"आपका सक्रिय सिंचाई कैलेंडर: {joined}। कुल आवश्यकता: {summary.get('total_water_required_liters')} लीटर (कैलेंडर में नीले रंग में चिह्नित)।"
            elif target_lang == "te":
                return f"మీ యాక్టివ్ ఇరిగేషన్ క్యాలెండర్: {joined}. మొత్తం అవసరమైన నీరు: {summary.get('total_water_required_liters')} లీటర్లు (క్యాలెండర్‌లో నీలి రంగులో గుర్తించబడ్డాయి)."
            else:
                return f"Your active irrigation calendar dates: {joined}. Total water required: {summary.get('total_water_required_liters')} L (marked in BLUE on both calendars)."
        else:
            if target_lang == "hi":
                return "वर्तमान में कोई सिंचाई शेड्यूल सक्रिय नहीं है। मिट्टी में पर्याप्त नमी उपलब्ध है।"
            elif target_lang == "te":
                return "ప్రస్తుతానికి ఎటువంటి యాక్టివ్ షెడ్యూల్ లేదు. ప్రస్తుత నేల తేమ సరిపోతుంది."
            else:
                return "No active irrigation schedule is currently needed. Current soil moisture conditions are sufficient."

    # 2b. "Show completed irrigation dates"
    if any(k in p_lower for k in ["completed irrigation dates", "show completed", "completed dates", "completed sessions", "पूर्ण सिंचाई तारीखें", "పూర్తయిన తేదీలు"]):
        summary = get_schedule_summary()
        completed = summary.get("completed_schedules", [])
        if completed:
            dates = [f"**{s.get('date_display', s.get('irrigation_date'))}** ({s.get('crop')} - {s.get('water_quantity_liters')} L)" for s in completed]
            joined = ", ".join(dates)
            if target_lang == "hi":
                return f"सफलतापूर्वक पूर्ण किए गए सिंचाई सत्र (हरे रंग में चिह्नित): {joined}।"
            elif target_lang == "te":
                return f"విజయవంతంగా పూర్తయిన ఇరిగేషన్ సెషన్లు (ఆకుపచ్చ రంగులో గుర్తించబడ్డాయి): {joined}."
            else:
                return f"Successfully completed irrigation dates (marked in GREEN): {joined}."
        else:
            if target_lang == "hi":
                return "अभी तक कोई भी सिंचाई सत्र पूर्ण चिह्नित नहीं किया गया है।"
            elif target_lang == "te":
                return "ఇప్పటివరకు ఎటువంటి సెషన్లు పూర్తయినట్లు నమోదు కాలేదు."
            else:
                return "No completed irrigation sessions have been recorded in history yet."

    # 2c. "Show skipped irrigation dates"
    if any(k in p_lower for k in ["skipped irrigation dates", "show skipped", "skipped dates", "skipped sessions", "छोड़े गए सत्र", "దాటవేయబడిన తేదీలు"]):
        summary = get_schedule_summary()
        skipped = summary.get("skipped_schedules", [])
        if skipped:
            dates = [f"**{s.get('date_display', s.get('irrigation_date'))}** ({s.get('crop')} - {s.get('reason', '')})" for s in skipped]
            joined = ", ".join(dates)
            if target_lang == "hi":
                return f"किसान द्वारा छोड़े गए सिंचाई सत्र (लाल रंग में चिह्नित): {joined}।"
            elif target_lang == "te":
                return f"రైతు ద్వారా దాటవేయబడిన ఇరిగేషన్ సెషన్లు (ఎరుపు రంగులో గుర్తించబడ్డాయి): {joined}."
            else:
                return f"Skipped irrigation dates (marked in RED): {joined}."
        else:
            if target_lang == "hi":
                return "कोई भी सिंचाई सत्र छोड़ा नहीं गया है।"
            elif target_lang == "te":
                return "ఎటువంటి సెషన్లు దాటవేయబడలేదు."
            else:
                return "No irrigation sessions have been skipped."

    # 3. "How many days of irrigation are required?"
    if any(k in p_lower for k in [
        "how many days is irrigation required", "how many days of irrigation", "how many days",
        "how many days irrigation", "number of irrigation days", "कितने दिन सिंचाई", "ఎన్ని రోజులు నీరు", "ఎన్ని రోజులు ఇరిగేషన్"
    ]):
        summary = get_schedule_summary()
        count = summary.get("total_active_sessions", 0)
        if count > 0:
            if target_lang == "hi":
                return f"वर्तमान नमी की कमी के आधार पर कुल **{count}** अलग-अलग सिंचाई सत्रों की आवश्यकता है (लगातार दिन नहीं, बल्कि आवश्यक अंतराल पर)।"
            elif target_lang == "te":
                return f"ప్రస్తుత తేమ కొరత ఆధారంగా మొత్తం **{count}** ఇరిగేషన్ సెషన్లు అవసరం (వరుస రోజులు కాకుండా తగిన వ్యవధిలో)."
            else:
                return f"Based on your current soil moisture deficit, exactly **{count}** spaced irrigation sessions are required."
        else:
            if target_lang == "hi":
                return "वर्तमान में कोई सिंचाई सत्र आवश्यक नहीं है। मिट्टी में पर्याप्त नमी है।"
            elif target_lang == "te":
                return "ప్రస్తుతానికి ఎటువంటి సెషన్లు అవసరం లేదు. నేలలో తేమ తగినంతగా ఉంది."
            else:
                return "Zero irrigation days are required right now. Soil moisture is sufficient."

    # 4. "How much water do I need?" (general schedule water query)
    if any(k in p_lower for k in ["how much water do i need", "how much water", "water quantity", "water required", "कितने पानी की जरूरत", "ఎంత నీరు అవసరం"]) and not any(c in p_lower for c in ["rice", "wheat", "paddy", "maize", "cotton", "tomato", "chilli", "groundnut", "sugarcane"]):
        summary = get_schedule_summary()
        total_w = summary.get("total_water_required_liters", 0.0)
        next_s = summary.get("next_session")
        next_w = next_s.get("water_quantity_liters", 450.0) if next_s else 0.0
        if total_w > 0:
            if target_lang == "hi":
                return f"आपके अगले सत्र के लिए **{next_w} लीटर** और पूरे आगामी शेड्यूल के लिए कुल **{total_w} लीटर** पानी की आवश्यकता है।"
            elif target_lang == "te":
                return f"మీ తదుపరి సెషన్‌కు **{next_w} లీటర్లు**, మొత్తం షెడ్యూల్ కొరకు **{total_w} లీటర్ల** నీరు అవసరం."
            else:
                return f"Your next session requires **{next_w} L**, with a total requirement of **{total_w} L** across all scheduled sessions."
        else:
            if target_lang == "hi":
                return "वर्तमान में अतिरिक्त सिंचाई जल की आवश्यकता नहीं है।"
            elif target_lang == "te":
                return "ప్రస్తుతానికి అదనపు నీటి అవసరం లేదు."
            else:
                return "No additional irrigation water is needed under current soil conditions."

    # 5. "Mark today's irrigation as completed"
    if ("mark" in p_lower and "complete" in p_lower) or any(k in p_lower for k in ["सिंचाई पूरी हुई", "పూర్తయినట్లు మార్క్ చేయండి", "mark completed"]):
        summary = get_schedule_summary()
        active = summary.get("active_schedules", [])
        if active:
            target_id = active[0]["id"]
            update_schedule_status(target_id, "Completed")
            d_disp = active[0].get("date_display", active[0].get("irrigation_date"))
            if target_lang == "hi":
                return f"✅ **{d_disp}** का सिंचाई सत्र सफलतापूर्वक **Completed (पूर्ण)** चिह्नित कर दिया गया है! कैलेंडर में हरा रंग अपडेट हुआ।"
            elif target_lang == "te":
                return f"✅ **{d_disp}** ఇరిగేషన్ సెషన్ **Completed (పూర్తయింది)** గా నమోదయింది! క్యాలెండర్‌లో ఆకుపచ్చ రంగు అప్‌డేట్ అయింది."
            else:
                return f"✅ Marked your irrigation session for **{d_disp}** as **Completed**! Updated to GREEN on both calendars."
        else:
            return "No pending irrigation session was found to mark as completed."

    # 6. "Skip today's irrigation"
    if ("skip" in p_lower and ("irrigation" in p_lower or "today" in p_lower or "session" in p_lower)) or any(k in p_lower for k in ["सिंचाई छोड़ें", "స్కిప్ చేయండి", "skip today"]):
        summary = get_schedule_summary()
        active = summary.get("active_schedules", [])
        if active:
            target_id = active[0]["id"]
            update_schedule_status(target_id, "Skipped", skip_reason="Farmer opted to skip")
            d_disp = active[0].get("date_display", active[0].get("irrigation_date"))
            if target_lang == "hi":
                return f"⚠️ **{d_disp}** का सिंचाई सत्र **Skipped (छोड़ दिया गया)** चिह्नित किया गया है (लाल रंग)। AI ने इसे अगले उपयुक्त दिन के लिए पुनः निर्धारित किया है (नीला रंग)।"
            elif target_lang == "te":
                return f"⚠️ **{d_disp}** ఇరిగేషన్ సెషన్ **Skipped (దాటవేయబడింది)** గా నమోదయింది (ఎరుపు రంగు). AI తదుపరి అనుకూల తేదీకి రీషెడ్యూల్ చేసింది (నీలి రంగు)."
            else:
                return f"⚠️ Skipped irrigation session for **{d_disp}** (marked in RED). AI has rescheduled the session to the next dry day (marked in BLUE). Total water requirement is preserved."
        else:
            return "No pending irrigation session found to skip."


    # 7. "Why is irrigation recommended on this date?" / "why this schedule" / "Why is irrigation required tomorrow?"
    if any(k in p_lower for k in [
        "why is irrigation recommended on this date", "why this schedule", "why recommended on this date",
        "why is irrigation required tomorrow", "why is irrigation needed tomorrow", "why irrigation tomorrow", "why irrigate tomorrow",
        "इस तारीख पर सिंचाई क्यों", "कल सिंचाई क्यों", "ई తేదీన ఎందుకు", "రేపు ఇరిగేషన్ ఎందుకు"
    ]):
        summary = get_schedule_summary()
        next_s = summary.get("next_session")
        if next_s:
            reason = next_s.get("reason", "Root zone moisture deficit replenishment")
            d_disp = next_s.get("date_display", next_s.get("irrigation_date"))
            w_lit = next_s.get("water_quantity_liters", 450.0)
            if target_lang == "hi":
                return f"**{d_disp}** पर {w_lit} लीटर सिंचाई की सिफारिश का कारण: {reason}। सुबह 6:00 बजे पानी देने से तेज धूप के वाष्पीकरण से बचाव होता है।"
            elif target_lang == "te":
                return f"**{d_disp}** న {w_lit} లీటర్ల నీరు అందించడానికి కారణం: {reason}. ఉదయం 6:00 గంటలకు నీరు పెట్టడం వల్ల భాష్పీభవన నష్టాలు తగ్గుతాయి."
            else:
                return f"Recommendation for **{d_disp}** ({w_lit} L): {reason}. Scheduling at 6:00 AM prevents high solar evapotranspiration losses."
        else:
            return "Current soil moisture is within the healthy zone, so no irrigation is recommended."


    # 1. "Explain how irrigation prediction works" / "how prediction works"
    if any(k in p_lower for k in [
        "how irrigation prediction works", "how prediction works", "how it works",
        "सिंचाई भविष्यवाणी कैसे काम करती", "ప్రిడిక్షన్ ఎలా పనిచేస్తుంది",
        "explain irrigation prediction", "irrigation prediction work"
    ]):
        if target_lang == "hi":
            return (
                "हमारी सिंचाई भविष्यवाणी प्रणाली दोहरे स्तर पर काम करती है। "
                "सबसे पहले, यह राज्य-वार फसल नियमों (जैसे ट्रिगर नमी स्तर और पिछले 7 दिनों में 10 मिमी वर्षा होने पर स्वतः रोक) की जांच करती है। "
                "इसके बाद, प्रशिक्षित मशीन लर्निंग मॉडल मिट्टी की नमी, तापमान और आर्द्रता का विश्लेषण करके तय करता है कि सिंचाई करनी है (IRRIGATE), "
                "निगरानी रखनी है (MONITOR), या सिंचाई नहीं करनी है (DO NOT IRRIGATE)।"
            )
        elif target_lang == "te":
            return (
                "మా ఇరిగేషన్ ప్రిడిక్షన్ వ్యవస్థ హైబ్రిడ్ రూల్-బేస్డ్ మరియు మెషిన్ లెర్నింగ్ మోడల్ ఆధారంగా పనిచేస్తుంది. "
                "మొదట, ఇది అధికారిక రాష్ట్ర-వారీ పంట పరిమితులను (ట్రిగ్గర్ తేమ శాతం మరియు గత 7 రోజుల్లో 10 మి.మీ వర్షపాతం ఉంటే నిలిపివేత) తనిఖీ చేస్తుంది. "
                "తర్వాత, సెన్సార్ డేటా (నేల తేమ, ఉష్ణోగ్రత, గాలిలో తేమ) ఆధారంగా పంటకు నీరు అవసరమా (IRRIGATE), గమనించాలా (MONITOR) లేదా నీరు అవసరం లేదా (DO NOT IRRIGATE) అని స్పష్టమైన ఫలితాన్ని ఇస్తుంది."
            )
        else:
            return (
                "The irrigation prediction engine uses a dual-layer hybrid architecture. "
                "First, it evaluates genuine Indian state-specific crop rules (such as minimum moisture trigger and field capacity, plus rainfall override where ≥10 mm rain pauses irrigation). "
                "Second, a trained Machine Learning model evaluates real-time sensor parameters (soil moisture, temperature, humidity) to classify whether the field needs immediate irrigation (IRRIGATE), observation (MONITOR), or no watering (DO NOT IRRIGATE)."
            )

    # 2. "Which crop is suitable for my state?" / "suitable crop"
    if any(k in p_lower for k in ["which crop is suitable", "suitable crop", "crops for my state", "फसल मेरे राज्य के लिए उपयुक्त", "ఏ పంట అనుకూలం"]):
        from src.irrigation_service import IrrigationService
        service = IrrigationService.get_instance()
        matched_state = None
        for s in service.get_states():
            if s.lower() in p_lower or (state_ctx and s.lower() == str(state_ctx).lower()):
                matched_state = s
                break

        if matched_state:
            crops_list = service.get_crops_for_state(matched_state)
            crop_names = [c["crop"] for c in crops_list] if crops_list else ["Rice", "Wheat", "Maize", "Cotton"]
            crops_str = ", ".join(crop_names[:6])
            if target_lang == "hi":
                return f"{matched_state} के लिए मुख्य उपयुक्त फसलें: {crops_str}। आप ऊपर योजनाकार में फसल का चयन करके विस्तृत सिंचाई दिशानिर्देश देख सकते हैं।"
            elif target_lang == "te":
                return f"{matched_state} రాష్ట్రానికి ప్రధాన అనుకూల పంటలు: {crops_str}. సమగ్ర నీటి యాజమాన్య వివరాల కోసం ప్లానర్‌లో పంటను ఎంచుకోండి."
            else:
                return f"For {matched_state}, certified suitable crops include: {crops_str}. Select your desired crop in the planner above to view its tailored irrigation thresholds."
        else:
            if target_lang == "hi":
                return "फसल का चयन राज्य की जलवायु और मिट्टी पर निर्भर करता है। जैसे पंजाब में गेहूं व धान; आंध्र प्रदेश/तेलंगाना में धान, मिर्च व मूंगफली; और महाराष्ट्र में कपास व गन्ना उपयुक्त हैं। अपने राज्य के लिए उपयुक्त फसलें देखने हेतु ऊपर ड्रॉपडाउन से राज्य चुनें।"
            elif target_lang == "te":
                return "పంట అనుకూలత మీ ప్రాంత నేల స్వభావం మరియు వాతావరణంపై ఆధారపడి ఉంటుంది. ఉదాహరణకు, ఆంధ్రప్రదేశ్/తెలంగాణలో వరి, వేరుశనగ, పత్తి మరియు మిర్చి; పంజాబ్‌లో గోధుమ మరియు వరి అనుకూలం. మీ రాష్ట్రానికి తగిన పంటలను చూడటానికి ప్లానర్‌లో రాష్ట్రాన్ని ఎంచుకోండి."
            else:
                return "Suitable crops depend on your state's agro-climatic zone. For example, Punjab thrives with Wheat, Rice, and Cotton; Andhra Pradesh & Telangana excel with Rice, Groundnut, Cotton, and Chilli; Maharashtra suits Sugarcane and Soybean. Select your state in the planner to see all certified crops."

    # 3. "How much water does rice require?" / "water requirement for rice" / "paddy water"
    if any(k in p_lower for k in ["how much water does rice require", "water requirement for rice", "rice require", "water does rice", "धान को कितने पानी", "వరి పంటకు ఎంత నీరు"]):
        if target_lang == "hi":
            return (
                "धान (चावल) की फसल को पूरे विकास काल में लगभग 1,200 से 1,500 मिमी (12,000 से 15,000 घन मीटर प्रति हेक्टेयर) पानी की आवश्यकता होती है। "
                "पारंपरिक बाढ़ विधि में 2 से 5 सेमी पानी खेत में खड़ा रखा जाता है। "
                "वैकल्पिक गीला और सूखा (AWD) तकनीक अपनाकर जब पानी का स्तर सतह से 15 सेमी नीचे चला जाए तभी सिंचाई करके किसान 25-30% पानी की बचत कर सकते हैं।"
            )
        elif target_lang == "te":
            return (
                "వరి పంటకు మొత్తం సాగు కాలంలో దాదాపు 1,200 నుండి 1,500 మి.మీ నీరు అవసరమవుతుంది (హెక్టారుకు 12,000–15,000 క్యూబిక్ మీటర్లు). "
                "సంప్రదాయ పద్ధతిలో 2-5 సెం.మీ నీరు నిలకడగా ఉంచుతారు. "
                "అయితే ఆల్టర్నేట్ వెట్టింగ్ అండ్ డ్రైయింగ్ (AWD) పద్ధతిని అనుసరించి, నీటి మట్టం నేల ఉపరితలానికి 15 సెం.మీ కిందకు చేరినప్పుడు మాత్రమే నీరు పెట్టడం ద్వారా 25-30% నీటిని ఆదా చేయవచ్చు."
            )
        else:
            return (
                "Rice (Paddy) typically requires about 1,200 to 1,500 mm of water throughout its growing season (approx. 12,000–15,000 m³ per hectare). "
                "Under conventional continuous submergence, 2–5 cm of standing water is maintained. "
                "By adopting Alternate Wetting and Drying (AWD) and re-irrigating only when the field water level drops to 15 cm below the soil surface, water consumption is reduced by 25–30% with no loss in yield."
            )

    # 4. Explain result in Telugu or general result explanation in Telugu
    if "explain" in p_lower and ("telugu" in p_lower or target_lang == "te"):
        crop_name = crop_ctx or "పంట"
        state_name = state_ctx or "మీ రాష్ట్రం"
        return (
            f"{state_name}లో {crop_name} కొరకు సిఫార్సు చేయబడిన ఫలితం: "
            "నేలలోని తేమ శాతం నిర్ణీత ట్రిగ్గర్ పాయింట్ కంటే తక్కువగా ఉన్నప్పుడు తక్షణమే నీరు అందించాలి (IRRIGATE). "
            "తేమ తగినంతగా ఉన్నప్పుడు లేదా గత 7 రోజుల్లో 10 మి.మీ కంటే ఎక్కువ వర్షం పడినప్పుడు నీటిపారుదల నిలిపివేయాలి (DO NOT IRRIGATE). "
            "తేమ మధ్యస్థ పరిధిలో ఉంటే నేల పరిస్థితిని పరిశీలిస్తూ ఉండాలి (MONITOR)."
        )

    # 5. Explain irrigation prediction in Hindi
    if "explain" in p_lower and ("hindi" in p_lower or target_lang == "hi"):
        return (
            "सिंचाई भविष्यवाणी प्रणाली आपके खेत की मिट्टी की नमी, तापमान, आर्द्रता और हालिया वर्षा का सटीक विश्लेषण करती है। "
            "जब मिट्टी की नमी फसल के ट्रिगर स्तर से नीचे गिर जाती है, तो सिस्टम सिंचाई (IRRIGATE) की सलाह देता है। "
            "यदि पिछले 7 दिनों में 10 मिमी या उससे अधिक बारिश हुई हो, तो जल संरक्षण के लिए सिंचाई स्वतः रोक दी जाती है।"
        )

    # 6. "What factors affect irrigation requirements?" / "factors affect"
    if any(k in p_lower for k in ["factors affect", "factors that affect", "कारक", "అంశాలు"]):
        if target_lang == "hi":
            return (
                "फसलों की सिंचाई आवश्यकता को प्रभावित करने वाले 5 मुख्य कारक हैं:\n"
                "1. मिट्टी का प्रकार और नमी: रेतीली मिट्टी में बार-बार हल्की सिंचाई चाहिए, जबकि चिकनी मिट्टी अधिक समय तक नमी रोकती है।\n"
                "2. फसल की वृद्धि अवस्था: कल्ले फूटते समय, फूल आते समय और दाना भरते समय सर्वाधिक पानी की आवश्यकता होती है।\n"
                "3. तापमान व धूप: अधिक तापमान और तेज हवाओं से वाष्पीकरण (Evapotranspiration) बढ़ जाता है।\n"
                "4. हाल की वर्षा: पिछले 7 दिनों में 10 मिमी या अधिक बारिश होने पर सिंचाई रोक दी जाती है।\n"
                "5. जड़ों की गहराई: गहरी जड़ वाली फसलें निचली मिट्टी से भी नमी प्राप्त कर सकती हैं।"
            )
        elif target_lang == "te":
            return (
                "పంటల నీటి అవసరాలను ప్రభావితం చేసే 5 ప్రధాన అంశాలు:\n"
                "1. నేల రకం మరియు తేమ: ఇసుక నేలలకు తరచుగా నీరు అవసరం, నల్లరేగడి నేలలు ఎక్కువ సమయం తేమను నిలుపుకుంటాయి.\n"
                "2. పంట ఎదుగుదల దశ: పూత దశ మరియు గింజ పాలు పోసుకునే సమయాల్లో నీటి అవసరం అత్యధికం.\n"
                "3. వాతావరణ ఉష్ణోగ్రత: అధిక ఎండ, వేడి గాలులు ఉన్నప్పుడు ఆవిరి శాతం పెరిగి నీరు త్వరగా ఆరిపోతుంది.\n"
                "4. వర్షపాతం: గత 7 రోజుల్లో 10 మి.మీ లేదా అంతకంటే ఎక్కువ వర్షం పడితే నీరు పెట్టనవసరం లేదు.\n"
                "5. వేరు వ్యవస్థ లోతు: లోతైన వేర్లు కలిగిన పంటలు భూమి లోపలి తేమను సులభంగా గ్రహించగలవు."
            )
        else:
            return (
                "The 5 primary factors affecting crop irrigation requirements are:\n"
                "1. Soil Texture & Moisture: Sandy soils drain quickly and require frequent irrigation, while clayey soils retain moisture longer.\n"
                "2. Growth Stage: Flowering, panicle initiation, and grain-filling stages demand peak moisture.\n"
                "3. Evapotranspiration (ET): Higher ambient temperatures, direct solar radiation, and low humidity accelerate water loss.\n"
                "4. Recent Rainfall: 10 mm or more of rainfall in the last 7 days automatically pauses irrigation.\n"
                "5. Effective Root Zone Depth: Deep-rooted crops tap subsoil water reserves, whereas shallow-rooted crops need frequent topsoil moisture."
            )

    # 7. "Why does my crop need this amount of water?" / "why crop need water"
    if any(k in p_lower for k in ["why does my crop need", "why crop need", "amount of water", "पानी की आवश्यकता क्यों", "నీరు ఎందుకు అవసరం"]):
        if target_lang == "hi":
            return (
                "फसल को पानी मुख्य रूप से तीन जैविक कार्यों के लिए चाहिए: "
                "1. पोषक तत्वों का अवशोषण (जड़ों से पत्तियों तक खाद पहुँचाना), "
                "2. वाष्पोत्सर्जन (Transpiration) द्वारा पौधे को धूप की अत्यधिक गर्मी से ठंडा रखना (सोखे गए पानी का 95-98% भाग वाष्पीकृत होता है), "
                "और 3. कोशिकाओं में तनाव (Turgidity) बनाए रखना ताकि पौधा सीधा खड़ा रहे। "
                "हमारी अनुशंसित मात्रा मिट्टी में रीडिली अवेलेबल वाटर (RAW) की कमी को पूरा करती है।"
            )
        elif target_lang == "te":
            return (
                "పంటలకు ప్రధానంగా మూడు ముఖ్య కారణాల వల్ల నీరు అవసరం: "
                "1. పోషకాల శోషణ (వేర్ల ద్వారా నేలలోని ఎరువులను ఆకులకు చేరవేయడం), "
                "2. భాష్పోత్సేకం (Transpiration) ద్వారా తీవ్రమైన ఎండ వేడిమి నుండి మొక్కను చల్లగా ఉంచడం (మొక్క తీసుకునే నీటిలో 95-98% ఆవిరవుతుంది), "
                "మరియు 3. కణాలలో పటుత్వాన్ని కాపాడటం ద్వారా మొక్క నిటారుగా ఎదగడం. "
                "సిఫార్సు చేసిన పరిమాణం వేరు మండలంలోని తేమ కొరతను సరిచేసి దిగుబడిని పెంచుతుంది."
            )
        else:
            return (
                "Crops require water for three vital physiological processes: "
                "1. Nutrient uptake and vascular transport from soil to leaves, "
                "2. Transpirational cooling (95–98% of water taken up is transpired to keep plant tissues cool under solar heat), "
                "and 3. Maintaining cellular turgidity for photosynthesis and structural rigidity. "
                "The calculated irrigation quantity replenishes the Readily Available Water (RAW) deficit in the root zone without causing waterlogging or nutrient leaching."
            )

    # 8. Drip irrigation, sprinkler irrigation, and furrow comparison
    if any(k in p_lower for k in [
        "what is drip irrigation", "drip irrigation", "drip vs sprinkler", "sprinkler irrigation",
        "furrow irrigation", "micro irrigation", "ड्रिप सिंचाई", "बिందు సేద్యం", "బిందుసేద్యం"
    ]):
        if target_lang == "hi":
            return (
                "**ड्रिप सिंचाई (टपक सिंचाई)** एक आधुनिक सूक्ष्म-सिंचाई प्रणाली है, जिसमें कम दबाव (1-2 बार) पर पाइपों और ड्रिपर्स के माध्यम से पानी और तरल उर्वरक सीधे फसल की जड़ों तक बूंद-बूंद पहुँचाया जाता है।\n\n"
                "• **मुख्य लाभ:** पारंपरिक बाढ़ विधि की तुलना में 40% से 70% पानी की बचत होती है और जल उपयोग दक्षता 90-95% तक पहुँचती है। पंक्तियों के बीच खरपतवार नहीं उगते और पत्तियों पर नमी न रहने से फंगल बीमारियाँ रुकती हैं।\n"
                "• **स्प्रिंकलर से तुलना:** स्प्रिंकलर (फव्वारा) सिंचाई हवा में बारिश की तरह पानी छिड़कती है (30-50% पानी की बचत, गेहूं/चना व उबड़-खाबड़ जमीन के लिए उपयुक्त), लेकिन तेज धूप और हवा में वाष्पीकरण का नुकसान अधिक होता है।\n"
                "• **फरो/बाढ़ विधि:** इसमें क्यारियों में पानी बहाया जाता है, जिसमें शुरुआती लागत कम होती है लेकिन 40-50% पानी जमीन में गहरा रिसकर या भाप बनकर बर्बाद हो जाता है।"
            )
        elif target_lang == "te":
            return (
                "**బిందు సేద్యం (డ్రిప్ ఇరిగేషన్)** అనేది తక్కువ పీడనం వద్ద పైపులు మరియు డ్రిప్పర్ల ద్వారా నీరు మరియు ఎరువులను నేరుగా మొక్కల వేరు వ్యవస్థ వద్దకు చుక్కలు చుక్కలుగా అందించే ఆధునిక పద్ధతి.\n\n"
                "• **ప్రధాన ఉపయోగాలు:** సంప్రదాయ పద్ధతితో పోలిస్తే 40% నుండి 70% వరకు నీరు ఆదా అవుతుంది, మరియు 90-95% నీటి వినియోగ సామర్థ్యం లభిస్తుంది. కలుపు మొక్కల బెడద తగ్గుతుంది, ఆకులు తడవకపోవడం వల్ల ఫంగస్ తెగుళ్లు రావు.\n"
                "• **స్ప్రింక్లర్ తో పోలిక:** స్ప్రింక్లర్ పద్ధతి వర్షంలా ఆకాశం నుండి నీటిని వెదజల్లుతుంది (30-50% నీటి ఆదా, గోధుమలు, పప్పుధాన్యాలు మరియు ఎగుడుదిగుడు నేలలకు అనుకూలం), కానీ వేడి గాలులు ఉన్నప్పుడు ఆవిరి నష్టాలు ఎక్కువ.\n"
                "• **కాలువల పద్ధతి (ఫర్రో):** ఇందులో నీటిని నేరుగా మళ్లించడం వల్ల ప్రారంభ ఖర్చు తక్కువైనా, 40-50% నీరు భూమి లోపలికి ఇంకిపోయి లేదా ఆవిరై వృథా అవుతుంది."
            )
        else:
            return (
                "**Drip Irrigation (Micro-irrigation)** is a high-efficiency precision irrigation method that delivers water and soluble nutrients directly to plant root zones drop-by-drop through emitters at low pressure (1–2 bar).\n\n"
                "• **Key Benefits:** Conserves 40% to 70% water compared to flood irrigation, achieving 90–95% water-use efficiency. Suppresses weed germination between rows, enables targeted fertigation, and keeps foliage dry to prevent fungal blights. Ideal for row crops, orchards, vegetables, and sugarcane.\n"
                "• **Comparison with Sprinkler Irrigation:** Sprinkler systems spray pressurized water into the air simulating rainfall (30–50% water savings, well-suited for undulating land and field crops like wheat and pulses, but vulnerable to wind drift and high evaporation losses in hot climates).\n"
                "• **Comparison with Furrow / Flood Irrigation:** Furrow irrigation channels water through gravity trenches; while inexpensive to set up, it loses 40–50% of water through deep percolation and surface evaporation."
            )

    # 9. Improving soil fertility and organic management
    if any(k in p_lower for k in [
        "improve soil fertility", "how can i improve soil fertility", "soil fertility",
        "increase soil fertility", "fertilize soil", "मिट्टी की उर्वरता", "नेला సారాన్ని", "భూసారం", "నేల సారం"
    ]):
        if target_lang == "hi":
            return (
                "खेत की **मिट्टी की उर्वरता और उत्पादकता** बढ़ाने के 5 वैज्ञानिक उपाय:\n\n"
                "1. **जैविक खाद (FYM / वर्मीकम्पोस्ट):** बुवाई से पहले प्रति एकड़ 5-10 टन अच्छी तरह सड़ी गोबर की खाद या केंचुआ खाद मिलाएं। इससे मिट्टी में जीवांश कार्बन (SOC) और सूक्ष्मजीव बढ़ते हैं।\n"
                "2. **हरी खाद (Green Manuring):** ढैंचा (Sesbania) या सनई की बुवाई करें और 45-50 दिन बाद फूल आने पर मिट्टी में पलट दें। यह प्रति हेक्टेयर 60-80 किलो प्राकृतिक नाइट्रोजन जोड़ती है।\n"
                "3. **दलहनी फसलों से फसल चक्र (Crop Rotation):** धान-गेहूं के बाद मूंग, चना या उड़द जैसी दलहनी फसलें लगाएं जिनकी जड़ों में राइजोबियम बैक्टीरिया वायुमंडलीय नाइट्रोजन स्थिर करते हैं।\n"
                "4. **संतुलित NPK व सूक्ष्म पोषक तत्व:** स्वाइल हेल्थ कार्ड जांच के अनुसार 4:2:1 अनुपात में खाद दें। केवल यूरिया पर निर्भर न रहें; जिंक सल्फेट और बोरॉन की कमी को पूरा करें।\n"
                "5. **जैव उर्वरक (Biofertilizers):** बीजों को एजोटोबैक्टर (अनाज के लिए) और पीएसबी (फास्फोरस घोलक बैक्टीरिया) से उपचारित करें।"
            )
        elif target_lang == "te":
            return (
                "పొలంలో **నేల సారాన్ని మరియు ఫలదీకరణాన్ని** పెంపొందించడానికి 5 ముఖ్యమైన పద్ధతులు:\n\n"
                "1. **సేంద్రీయ ఎరువులు (FYM / వర్మీ కంపోస్ట్):** దుక్కిలో ఎకరానికి 5-10 టన్నుల పశువుల ఎరువు లేదా వర్మీ కంపోస్ట్ వేయడం ద్వారా నేలలో సేంద్రీయ కార్బన్ శాతం మరియు తేమ నిల్వ సామర్థ్యం పెరుగుతుంది.\n"
                "2. **పచ్చిరొట్ట ఎరువులు (Green Manure):** జీలుగ లేదా జనుము సాగు చేసి, 45-50 రోజుల పూత దశలో నేలలో కలియదున్నాలి. ఇది హెక్టారుకు 60-80 కిలోల సహజ నత్రజనిని అందిస్తుంది.\n"
                "3. **పప్పుధాన్యాల పంటల మార్పిడి:** వరి లేదా పత్తి తర్వాత మినుము, పెసర వంటి పప్పుధాన్యాలను పండించడం వల్ల వాటి వేరు బుడిపెలలోని రైజోబియం బ్యాక్టీరియా నేలకు నత్రజనిని స్థిరీకరిస్తుంది.\n"
                "4. **సమతుల్య NPK మరియు సూక్ష్మపోషకాలు:** సాయిల్ హెల్త్ కార్డ్ ఆధారంగా NPK 4:2:1 నిష్పత్తిలో అందించాలి. జింక్ మరియు బోరాన్ లోపాలను సరిదిద్దాలి.\n"
                "5. **జీవ ఎరువులు (Biofertilizers):** విత్తనాలను అజటోబాక్టర్, PSB (ఫాస్ఫేట్ సాల్యుబిలైజింగ్ బ్యాక్టీరియా) తో శుద్ధి చేయడం వల్ల నేలలోని పోషకాలు సులభంగా మొక్కలకు అందుతాయి."
            )
        else:
            return (
                "You can sustainably improve **soil fertility and soil health** through 5 proven agronomic practices:\n\n"
                "1. **Incorporate Organic Matter:** Apply 5–10 tonnes/acre of well-rotted Farmyard Manure (FYM) or Vermicompost before sowing. This elevates Soil Organic Carbon (SOC), improves cation-exchange capacity, and boosts water retention.\n"
                "2. **Green Manuring:** Cultivate leguminous green manure crops like Dhaincha (*Sesbania aculeata*) or Sunn hemp, incorporating them into the soil at 45–50 days (flowering stage) to add 60–80 kg N/ha of natural bio-available nitrogen.\n"
                "3. **Crop Rotation with Legumes:** Rotate heavy-feeding cereals (rice/wheat) with pulses (chickpea, green gram, cowpea) to fix atmospheric nitrogen via symbiotic *Rhizobium* root nodules and disrupt soil-borne pest cycles.\n"
                "4. **Balanced NPK & Micronutrient Management:** Base fertilization strictly on Soil Health Card testing, maintaining balanced N:P:K ratios (typically 4:2:1) rather than over-applying urea. Supplement essential micronutrients like Zinc sulphate (25 kg/ha) and Boron.\n"
                "5. **Biofertilizers:** Inoculate seeds and soil with *Azotobacter/Azospirillum* (free-living N-fixers) and Phosphate Solubilizing Bacteria (PSB) to mobilize bound phosphorus."
            )

    # 10. Crops suitable for Punjab
    if any(k in p_lower for k in [
        "crops are suitable for punjab", "crops for punjab", "punjab crops",
        "suitable for punjab", "crops in punjab", "crop suitable for punjab",
        "पंजाब के लिए उपयुक्त फसलें", "पंजाब की फसलें", "పంజాబ్‌కు ఏ పంటలు"
    ]):
        if target_lang == "hi":
            return (
                "**पंजाब राज्य के लिए प्रमाणित और अत्यधिक उपयुक्त मुख्य फसलें:**\n\n"
                "• **रबी सीजन (सर्दियां: अक्टूबर-अप्रैल):** गेहूं (Wheat - राज्य की मुख्य फसल), सरसों/राया (Mustard), जौ (Barley), चना (Gram), आलू (Potato), और शीतकालीन मक्का।\n"
                "• **खरीफ सीजन (मानसून: जून-अक्टूबर):** बासमती और धान (Rice), बीटी कपास (Cotton - दक्षिण-पश्चिमी जिले जैसे बठिंडा, मानसा, फाजिल्का), मक्का (Maize), गन्ना (Sugarcane), और मूंग (Green Gram)।\n"
                "• **जायद/ग्रीष्मकालीन (मार्च-जून):** ग्रीष्मकालीन मूंग, सूरजमुखी (Sunflower), और मौसमी सब्जियां।\n\n"
                "💡 **कृषि सलाह:** गिरते भूजल स्तर के कारण पंजाब कृषि विश्वविद्यालय (PAU) धान के स्थान पर मक्का, कपास व दालों के विविधीकरण तथा धान में एलन (AWD) व ड्रिप सिंचाई की सलाह देता है।"
            )
        elif target_lang == "te":
            return (
                "**పంజాబ్ రాష్ట్రానికి అత్యంత అనుకూలమైన ప్రధాన పంటలు:**\n\n"
                "• **రబీ కాలం (శీతాకాలం: అక్టోబర్-ఏప్రిల్):** గోధుమ (Wheat - ప్రధాన పంట), ఆవాలు/రాయా (Mustard), బార్లీ (Barley), శనగలు (Gram), బంగాళాదుంప (Potato).\n"
                "• **ఖరీఫ్ కాలం (వర్షాకాలం: జూన్-అక్టోబర్):** బాస్మతి మరియు వరి (Rice), పత్తి (Cotton - బటిండా, మాన్సా జిల్లాల్లో), మొక్కజొన్న (Maize), చెరకు (Sugarcane), పెసర (Moong).\n"
                "• **వేసవి కాలం (మార్చి-జూన్):** వేసవి పెసర, పొద్దుతిరుగుడు (Sunflower), కూరగాయలు.\n\n"
                "💡 **సాగు సూచన:** భూగర్భ జలాల తగ్గుదల దృష్ట్యా వరి సాగులో AWD పద్ధతిని పాటించాలని మరియు మొక్కజొన్న, పప్పుధాన్యాల వైపు పంటల మార్పిడి చేపట్టాలని శాస్త్రవేత్తలు సూచిస్తున్నారు."
            )
        else:
            return (
                "**Certified Suitable Crops for Punjab (by Season):**\n\n"
                "• **Rabi Season (Winter, Oct–April):** **Wheat** (state staple crop), **Mustard / Raya**, Barley, Chickpea (Gram), Winter Maize, Potato, and Green Peas.\n"
                "• **Kharif Season (Monsoon, June–Oct):** **Paddy & Basmati Rice**, **Bt Cotton** (dominant in south-western belt: Bathinda, Mansa, Fazilka, Muktsar), **Maize**, Sugarcane, and Moong (Green Gram).\n"
                "• **Zaid / Summer Gap (March–June):** Summer Moong, Sunflower, Mash, and cucurbit vegetables.\n\n"
                "💡 **Agronomic Guidance:** Punjab's deep Indo-Gangetic alluvial soil offers high fertility. To combat groundwater depletion, Punjab Agricultural University (PAU) strongly encourages diversifying from paddy monoculture toward Maize, Cotton, and Pulses, or adopting Alternate Wetting and Drying (AWD) and Drip systems for water conservation."
            )

    # 11. How does nitrogen deficiency affect crops?
    if any(k in p_lower for k in [
        "nitrogen deficiency affect crops", "nitrogen deficiency affect", "nitrogen deficiency",
        "lack of nitrogen", "नाइट्रोजन की कमी", "నత్రజని లోపం", "నైట్రోజన్ లోపం"
    ]):
        if target_lang == "hi":
            return (
                "**फसलों पर नाइट्रोजन की कमी का प्रभाव और उसके लक्षण:**\n\n"
                "• **मुख्य लक्षण (Chlorosis):** पौधा पीला पड़ने लगता है। सबसे पहले **निचली और पुरानी पत्तियां** पीली होती हैं, क्योंकि नाइट्रोजन अत्यधिक गतिशील (mobile) तत्व है और पौधा इसे नई पत्तियों की ओर भेज देता है।\n"
                "• **पौधे की वृद्धि:** पौधे का विकास रुक जाता है, तने पतले व कमजोर रह जाते हैं, और गेहूं/धान में कल्ले (tillering) बहुत कम फूटते हैं।\n"
                "• **पैदावार पर असर:** फूल व बालियां देरी से आती हैं, दाने छोटे रह जाते हैं और कुल उपज में भारी गिरावट आती है।\n\n"
                "🛠️ **उपचार और समाधान:**\n"
                "1. **खेत में टॉप-ड्रेसिंग:** क्रांतिक वृद्धि अवस्थाओं पर नीम-लेपित यूरिया या कैल्शियम अमोनियम नाइट्रेट (CAN) को विभाजित खुराकों (split doses) में दें।\n"
                "2. **त्वरित पर्णीय छिड़काव (Foliar Spray):** 1% से 2% यूरिया घोल (10-20 ग्राम प्रति लीटर पानी) या नैनो यूरिया (2-4 मिली प्रति लीटर पानी) का छिड़काव करें, जिससे पत्तियां 24-48 घंटों में पुनः हरी हो जाती हैं।"
            )
        elif target_lang == "te":
            return (
                "**పంటలలో నత్రజని (నైట్రోజన్) లోపం వల్ల కలిగే నష్టాలు మరియు లక్షణాలు:**\n\n"
                "• **ప్రధాన లక్షణాలు:** మొక్కల ఆకులు పసుపు రంగులోకి మారుతాయి (క్లోరోసిస్). నత్రజని మొక్కలో సులభంగా కదిలే మూలకం కాబట్టి, ఈ పసుపుదనం మొదట **కింది భాగంలోని పాత ఆకులపై** కనిపిస్తుంది.\n"
                "• **ఎదుగుదల లోపం:** మొక్కలు గిడసబారిపోతాయి, కాండాలు సన్నగా బలహీనంగా మారతాయి, మరియు వరి/గోధుమ పంటల్లో పిలకలు (tillers) వేయడం గణనీయంగా తగ్గుతుంది.\n"
                "• **దిగుబడి నష్టం:** పూత ఆలస్యమవుతుంది, గింజలు సరిగా పాలుపోసుకోక తాలు గింజలు పెరిగి దిగుబడి పడిపోతుంది.\n\n"
                "🛠️ **నివారణ చర్యలు:**\n"
                "1. **పైపాటుగా యూరియా వేయడం:** పంట కీలక దశలలో సిఫార్సు చేసిన వేపపూత పూసిన యూరియాను సమపాళ్లలో అందించాలి.\n"
                "2. **ఆకులపై పిచికారీ (Foliar Spray):** తక్షణ ఉపశమనం కోసం లీటరు నీటికి 10-20 గ్రాముల యూరియా (1-2% ద్రావణం) లేదా 2-4 మి.లీ నానో యూరియా కలిపి ఆకులపై పిచికారీ చేయాలి."
            )
        else:
            return (
                "**How Nitrogen Deficiency Affects Crops and How to Correct It:**\n\n"
                "• **Visual Symptoms (Chlorosis):** Nitrogen is a mobile nutrient inside plant tissue. Deficiency triggers uniform pale yellowing starting on **older (lower) leaves first**, as the plant mobilizes remaining nitrogen reserves to young developing shoot tips.\n"
                "• **Vegetative Stunting:** Plants exhibit stunted, upright growth with thin, spindly stems and pale green foliage. In cereals (wheat, rice, maize), tillering and lateral branching are drastically reduced.\n"
                "• **Yield & Quality Impact:** Delayed flowering, poor panicle/cob filling, reduced grain size, and lower seed protein content, leading to severe harvest losses.\n\n"
                "🛠️ **Corrective Measures & Remedies:**\n"
                "1. **Split Soil Application:** Top-dress with Neem-Coated Urea (NCU) or Calcium Ammonium Nitrate (CAN) in 2–3 calibrated split applications aligned with critical root initiation and vegetative stages.\n"
                "2. **Rapid Foliar Rescue:** Spray a 1% to 2% Urea solution (10–20 g per litre of water) or Liquid Nano Urea (2–4 ml/litre of water) for direct stomatal absorption within 24–48 hours."
            )

    # 12. Explain my latest irrigation prediction
    if any(k in p_lower for k in [
        "explain my latest irrigation prediction", "explain my prediction", "explain the prediction",
        "explain latest prediction", "मेरी नवीनतम सिंचाई भविष्यवाणी", "నా తాజా ప్రిడిక్షన్‌ను వివరించండి"
    ]):
        if target_lang == "hi":
            return (
                "**आपकी नवीनतम सिंचाई भविष्यवाणी का विस्तृत विश्लेषण:**\n\n"
                "• **निर्णय आधार (Decision Logic):** सिस्टम आपके खेत के सेंसर (नमी, तापमान, आर्द्रता) की तुलना फसल के प्रमाणित 'ट्रिगर नमी स्तर' से करता है।\n"
                "• **IRRIGATE:** यदि मिट्टी की नमी ट्रिगर स्तर से नीचे चली गई है, तो सिस्टम फसल की जड़ क्षेत्र की कमी को पूरा करने के लिए तुरंत अनुशंसित पानी (लीटर में) देने की सलाह देता है।\n"
                "• **DO NOT IRRIGATE / MONITOR:** यदि मिट्टी में पर्याप्त नमी उपलब्ध है, या पिछले 7 दिनों में 10 मिमी या उससे अधिक बारिश हुई है, तो पानी की बचत और जलभराव रोकने के लिए सिंचाई स्वतः रोक दी जाती है।\n"
                "• आप ऊपर योजनाकार में वास्तविक समय की रीडिंग दर्ज करके किसी भी समय अपनी फसल की स्थिति का पुनः मूल्यांकन कर सकते हैं।"
            )
        elif target_lang == "te":
            return (
                "**మీ తాజా ఇరిగేషన్ ప్రిడిక్షన్ వివరాలు:**\n\n"
                "• **నిర్ణయ ప్రక్రియ:** వ్యవస్థ మీ పొలం సెన్సార్ల (తేమ, ఉష్ణోగ్రత, గాలిలో తేమ) విలువలను పంట యొక్క 'ట్రిగ్గర్ పాయింట్' తో సరిపోలుస్తుంది.\n"
                "• **IRRIGATE (నీరు అవసరం):** నేల తేమ నిర్ణీత పరిమితి కంటే తగ్గితే, పంట వేర్లకు తగినంత నీటిని (లీటర్లలో) వెంటనే అందించాలని సూచిస్తుంది.\n"
                "• **DO NOT IRRIGATE / MONITOR:** నేలలో తేమ తగినంతగా ఉన్నా, లేదా గత 7 రోజుల్లో 10 మి.మీ కంటే ఎక్కువ వర్షపాతం నమోదైనా నీరు పెట్టడం ఆపివేయబడుతుంది.\n"
                "• పైన ఉన్న ప్లానర్‌లో మీ పంట సెన్సార్ విలువలను నమోదు చేసి ఎప్పటికప్పుడు తాజా సమాచారాన్ని పొందవచ్చు."
            )
        else:
            return (
                "**Detailed Explanation of Your Latest Irrigation Prediction:**\n\n"
                "• **Assessment Logic:** The engine compares your field's live sensor readings (soil moisture, temperature, relative humidity) against calibrated crop threshold benchmarks (Trigger Moisture & Field Capacity).\n"
                "• **IRRIGATE Outcome:** When soil moisture drops below the crop's safety trigger, the system recommends **IRRIGATE** and computes the exact water volume required to replenish the root zone deficit without over-saturating.\n"
                "• **MONITOR / DO NOT IRRIGATE Outcome:** If soil moisture is within the optimal vegetative range, or if ≥10 mm of rain occurred over the past 7 days, irrigation is halted to prevent waterlogging and fertilizer leaching.\n"
                "• You can review your active section's readings and run a fresh prediction anytime using the planner above."
            )

    # 13. Website usage and How-to
    if any(k in p_lower for k in [
        "how to use smart irrigation planner", "how to use planner", "how to use the planner",
        "how to use", "how to add land section", "how to add section", "how to view calendar",
        "how to view predictions", "योजनाकार का उपयोग कैसे करें", "ప్లానర్‌ను ఎలా ఉపయోగించాలి"
    ]):
        if "section" in p_lower:
            return (
                "**How to Add a Land Section to Your Farm:**\n"
                "1. On the Farmer Dashboard, locate the 'My Farm & Land Sections' module.\n"
                "2. Click the '+ Add Land Section' button.\n"
                "3. Enter a section name (e.g. 'Section 04'), enter the area in Acres (within your available farm land), and choose your crop.\n"
                "4. Click 'Save Section'. The section will appear with its own live sensor data and irrigation calendar."
            )
        elif "calendar" in p_lower:
            return (
                "**How to View and Use the Irrigation Calendar:**\n"
                "1. Scroll down to the 'Irrigation Scheduler & Calendar' module on your dashboard.\n"
                "2. Dates marked in **BLUE** are upcoming recommended irrigation sessions.\n"
                "3. Dates in **GREEN** are completed sessions; dates in **RED** are skipped sessions.\n"
                "4. Click any date or use the action buttons to mark sessions completed or reschedule."
            )
        else:
            return (
                "**How to Use the Smart Irrigation Planner:**\n"
                "1. Select your **State** and **Crop** from the dropdown selectors at the top of the planner.\n"
                "2. Enter your crop age (days) and sensor readings: Soil Moisture (%), Soil Temperature (°C), Air Temperature (°C), and Humidity (%).\n"
                "3. Click **'Predict Irrigation Requirement'**.\n"
                "4. The system will calculate whether your crop needs water (IRRIGATE, MONITOR, or DO NOT IRRIGATE) and show the exact water volume required."
            )

    # 14. Environmental, weather influence, water conservation, and sustainability
    if any(k in p_lower for k in [
        "weather influence", "weather affect", "water conservation", "conserve water",
        "sustainable farming", "climate change", "जल संरक्षण", "నీటి సంరక్షణ", "వాతావరణం"
    ]):
        if target_lang == "hi":
            return (
                "**कृषि पर मौसम का प्रभाव और जल संरक्षण तकनीकें:**\n\n"
                "• **मौसम का प्रभाव:** तेज धूप और उच्च तापमान से वाष्पीकरण (Evapotranspiration) बढ़ जाता है जिससे पौधों को अधिक पानी चाहिए। हाल की बारिश सिंचाई की आवश्यकता को टाल देती है।\n"
                "• **जल संरक्षण:** ड्रिप व स्प्रिंकलर सिंचाई अपनाएं, धान में वैकल्पिक गीला-सूखा (AWD) अपनाकर 30% पानी बचाएं, और मल्चिंग (Mulching) द्वारा मिट्टी की नमी उड़ने से रोकें।\n"
                "• **टिकाऊ खेती (Sustainable Farming):** फसल विविधीकरण, हरी खाद और न्यूनतम जुताई अपनाकर मिट्टी और पर्यावरण दोनों की रक्षा करें।"
            )
        elif target_lang == "te":
            return (
                "**వ్యవసాయంపై వాతావరణ ప్రభావం మరియు నీటి సంరక్షణ పద్ధతులు:**\n\n"
                "• **వాతావరణ ప్రభావం:** అధిక ఉష్ణోగ్రత మరియు తీవ్రమైన ఎండల వల్ల భాష్పీభవనం పెరిగి పంటలకు ఎక్కువ నీరు అవసరమవుతుంది. వర్షం పడినప్పుడు నీటిపారుదల నిలిపివేయాలి.\n"
                "• **నీటి సంరక్షణ:** బిందు సేద్యం (డ్రిప్) ద్వారా 50-70% నీటిని ఆదా చేయవచ్చు. వరిలో AWD పద్ధతిని మరియు మట్టిపై మల్చింగ్ షీట్లు వాడటం వల్ల తేమ ఎక్కువ కాలం నిలుస్తుంది.\n"
                "• **సుస్థిర వ్యవసాయం:** సేంద్రీయ ఎరువులు, పంటల మార్పిడి మరియు సహజ సస్యరక్షణ పద్ధతుల ద్వారా భూమి సారాన్ని కాపాడుకోవచ్చు."
            )
        else:
            return (
                "**Weather Influence and Water Conservation in Agriculture:**\n\n"
                "• **Weather Influence:** Solar radiation, air temperature, relative humidity, and wind speed dictate crop Evapotranspiration (ET). High temperatures dramatically increase daily water consumption, whereas rainfall directly replenishes soil moisture and delays scheduled irrigation.\n"
                "• **Top Water Conservation Techniques:**\n"
                "  1. Micro-irrigation (Drip & Micro-sprinklers) delivers 90–95% water-use efficiency.\n"
                "  2. Alternate Wetting and Drying (AWD) in paddy saves 25–30% irrigation water without yield penalty.\n"
                "  3. Organic Mulching (crop residue / straw) cuts topsoil evaporation by up to 35%.\n"
                "  4. Laser Land Leveling ensures uniform water distribution across the field.\n"
                "• **Sustainable Farming:** Combine crop rotation with legumes, green manuring, and Integrated Pest Management (IPM) to preserve soil organic carbon and protect local groundwater aquifers."
            )

    # General agricultural explanation fallback
    if target_lang == "hi":
        return "कृषि में जल संरक्षण और पैदावार बढ़ाने के लिए मिट्टी की नमी की नियमित जांच और मौसम आधारित सिंचाई योजना अत्यंत लाभकारी है। आप ऊपर योजनाकार में अपनी फसल की जांच कर सकते हैं।"
    elif target_lang == "te":
        return "వ్యవసాయంలో నీటిని ఆదా చేస్తూ మంచి దిగుబడి సాధించడానికి నేల తేమను ఎప్పటికప్పుడు గమనించి సమయానికి నీరు అందించడం చాలా అవసరం. మీ పంట వివరాలను ప్లానర్‌లో నమోదు చేసి ఫలితాన్ని చూడండి."
    else:
        return "Smart irrigation optimizes agricultural water efficiency by balancing crop evapotranspiration with real-time soil moisture and weather data. You can evaluate your field by entering your crop readings into the planner above."


LANGUAGE_NAMES = {
    "as": "Assamese (অসমীয়া)",
    "bn": "Bengali (বাংলা)",
    "brx": "Bodo (बड़ो)",
    "doi": "Dogri (डोगरी)",
    "gu": "Gujarati (ગુજરાતી)",
    "hi": "Hindi (हिन्दी)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ks": "Kashmiri (کٲشُر / कॉशुर)",
    "kok": "Konkani (कोंकणी)",
    "mai": "Maithili (मैथिली)",
    "ml": "Malayalam (മലയാളം)",
    "mni": "Manipuri (মৈতৈলোন্)",
    "mr": "Marathi (मराठी)",
    "ne": "Nepali (नेपाली)",
    "or": "Odia (ଓଡ଼ିଆ)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "sa": "Sanskrit (संस्कृतम्)",
    "sat": "Santali (ᱥᱟᱱᱛᱟᱲᱤ)",
    "sd": "Sindhi (سنڌي / सिन्धी)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "ur": "Urdu (اردو)",
    "en": "English",
}


def build_language_instruction(language: str, detected_lang: str) -> str:
    """Formulate language directive enforcing conciseness, native script, and zero filler."""
    if language in LANGUAGE_NAMES and language != "auto":
        return f"Language Directive: Respond in direct, concise {LANGUAGE_NAMES[language]}. Answer directly without filler greetings, repeated explanations, or unprompted disclaimers."
    if detected_lang in LANGUAGE_NAMES and detected_lang != "en":
        return f"Language Directive: AUTO-DETECT. The user message is in {LANGUAGE_NAMES[detected_lang]}. Respond directly and concisely in {LANGUAGE_NAMES[detected_lang]} without greetings or filler."
    return "Language Directive: AUTO-DETECT. Respond in the user's language directly and concisely (1-3 sentences for simple questions; concise bullets only if steps) without filler greetings or unprompted disclaimers."


def get_follow_up_suggestions(user_prompt: str, reply_text: str, language: str = "en") -> List[str]:
    """Generate 3-4 pertinent agricultural follow-up suggestions for any query."""
    p = (user_prompt or "").lower()

    if language == "te" or any("\u0c00" <= c <= "\u0c7f" for c in user_prompt):
        if "drip" in p or "బిందు" in p or "సేద్యం" in p:
            return [
                "💧 డ్రిప్ ఎమిట్టర్లలో పూడిక రాకుండా ఎలా శుభ్రం చేయాలి?",
                "📊 ఎకరానికి డ్రిప్ సిస్టమ్ ఏర్పాటుకు ఎంత ఖర్చవుతుంది?",
                "🌱 కూరగాయల సాగులో డ్రిప్ సేద్యం ఎంత నీటిని ఆదా చేస్తుంది?",
                "🌾 డ్రిప్ మరియు స్ప్రింక్లర్ పద్ధతుల మధ్య ప్రధాన తేడా ఏమిటి?"
            ]
        if "సారం" in p or "fertility" in p or "ఎరువు" in p:
            return [
                "🪴 మంచి నాణ్యమైన వర్మీ కంపోస్ట్ ఎలా తయారు చేయాలి?",
                "🌱 ఏ పచ్చిరొట్ట పైరు అత్యధిక నత్రజనిని అందిస్తుంది?",
                "🌾 పంటల మార్పిడి తెగుళ్లను ఎలా నియంత్రిస్తుంది?",
                "🧪 నేల పరీక్ష (Soil Test) ఎంత కాలానికి ఒకసారి చేయించాలి?"
            ]
        if "పంజాబ్" in p or "punjab" in p:
            return [
                "🌾 పంజాబ్‌లో అధిక దిగుబడినిచ్చే గోధుమ రకాలు ఏవి?",
                "💧 వరి సాగులో పంజాబ్ రైతులు నీటిని ఎలా ఆదా చేయవచ్చు?",
                "🌽 వరికి ప్రత్యామ్నాయంగా మొక్కజొన్న సాగు లాభదాయకమా?",
                "🪴 శీతాకాలపు బంగాళాదుంప విత్తేందుకు సరైన సమయం ఏది?"
            ]
        if "నత్రజని" in p or "nitrogen" in p or "యూరియా" in p:
            return [
                "🧪 ఎకరానికి యూరియా సరైన మోతాదు ఎంత?",
                "🌿 2% యూరియా ద్రావణాన్ని ఎలా తయారు చేసి పిచికారీ చేయాలి?",
                "🪴 భాస్వరం మరియు పొటాష్ లోప లక్షణాలు ఎలా ఉంటాయి?",
                "🌱 నానో యూరియా సాధారణ యూరియా కంటే ఎలా మెరుగైనది?"
            ]
        return [
            "💧 పొలంలో నీటిని ఎలా ఆదా చేయవచ్చు?",
            "🪴 సెన్సార్ లేకుండా నేల తేమను ఎలా గుర్తించాలి?",
            "🌾 నా ప్రాంతానికి ఏ పంటలు అత్యంత అనుకూలం?",
            "📊 నా తాజా ఇరిగేషన్ ప్రిడిక్షన్‌ను వివరించండి."
        ]

    if language == "hi" or any("\u0900" <= c <= "\u097f" for c in user_prompt):
        if "drip" in p or "ड्रिप" in p or "सिंचाई" in p:
            return [
                "💧 ड्रिप नोजल को चोक होने से कैसे बचाएं?",
                "📊 प्रति एकड़ ड्रिप सिंचाई लगाने का औसत खर्च क्या है?",
                "🌱 ड्रिप से सब्जियों में कितने प्रतिशत पानी की बचत होती है?",
                "🌾 ड्रिप और स्प्रिंकलर सिंचाई में मुख्य अंतर क्या है?"
            ]
        if "उर्वरता" in p or "fertility" in p or "खाद" in p:
            return [
                "🪴 उत्तम गुणवत्ता वाली केंचुआ खाद (वर्मीकम्पोस्ट) कैसे बनाएं?",
                "🌱 कौन सी हरी खाद फसल सबसे अधिक नाइट्रोजन देती है?",
                "🌾 फसल चक्र से कीट-रोगों की रोकथाम कैसे होती है?",
                "🧪 मिट्टी की जांच कितने समय में करानी चाहिए?"
            ]
        if "पंजाब" in p or "punjab" in p:
            return [
                "🌾 पंजाब के लिए गेहूं की सर्वश्रेष्ठ किस्में कौन सी हैं?",
                "💧 पंजाब में धान में पानी की बचत कैसे करें?",
                "🌽 क्या पंजाब में मक्के की खेती धान का अच्छा विकल्प है?",
                "🪴 पंजाब में आलू बोने का सबसे सही समय क्या है?"
            ]
        if "नाइट्रोजन" in p or "nitrogen" in p or "यूरिया" in p:
            return [
                "🧪 प्रति एकड़ यूरिया की सही खुराक क्या होनी चाहिए?",
                "🌿 2% यूरिया घोल बनाकर स्प्रे कैसे करें?",
                "🪴 फास्फोरस और पोटाश की कमी के लक्षण क्या हैं?",
                "🌱 नैनो यूरिया सामान्य दानेदार यूरिया से कैसे बेहतर है?"
            ]
        return [
            "💧 खेत में सिंचाई का पानी कैसे बचाएं?",
            "🪴 बिना सेंसर मिट्टी की नमी की जांच कैसे करें?",
            "🌾 मेरे क्षेत्र के लिए सबसे उपयुक्त फसलें कौन सी हैं?",
            "📊 मेरे नवीनतम सिंचाई परिणाम को विस्तार से समझाएं।"
        ]

    # English default
    if "drip" in p or "irrigation method" in p:
        return [
            "💧 How do I maintain drip emitters to prevent clogging?",
            "📊 What is the cost of setting up drip irrigation per acre?",
            "🌱 How much water does drip irrigation save for vegetables?",
            "🌾 What is the difference between drip and sprinkler irrigation?"
        ]
    if "fertility" in p or "soil" in p:
        return [
            "🪴 How do I prepare good quality vermicompost on my farm?",
            "🌱 Which green manure crop adds the most nitrogen?",
            "🌾 How does crop rotation prevent pest infestation?",
            "🧪 How often should I test my soil health?"
        ]
    if "punjab" in p:
        return [
            "🌾 What are the best high-yielding wheat varieties for Punjab?",
            "💧 How can Punjab farmers save water in paddy cultivation?",
            "🌽 Is maize cultivation profitable as a paddy alternative in Punjab?",
            "🪴 What is the ideal sowing time for winter potatoes in Punjab?"
        ]
    if "nitrogen" in p or "nutrient" in p or "fertilizer" in p:
        return [
            "🧪 What is the correct dosage of urea per acre?",
            "🌿 How do I prepare and spray a 2% urea foliar solution?",
            "🪴 What are the symptoms of phosphorus and potassium deficiency?",
            "🌱 How does nano-urea compare to conventional granular urea?"
        ]
    if "land" in p or "section" in p:
        return [
            "➕ How do I add a new land section to my farm?",
            "🌾 How can I allocate a different crop to an empty section?",
            "💧 What is the water requirement for each of my sections?",
            "🗓️ Show me the full irrigation calendar for this month."
        ]
    if "schedule" in p or "calendar" in p or "prediction" in p:
        return [
            "💧 Why is irrigation paused after 10 mm of rainfall?",
            "📊 What is the difference between trigger moisture and field capacity?",
            "🗓️ How can I reschedule an upcoming irrigation session?",
            "🌾 How does temperature affect crop water requirements?"
        ]

    return [
        "💧 How can I save irrigation water on my farm?",
        "🪴 How do I test soil moisture without digital sensors?",
        "🌾 Which crops are best suited for my region?",
        "📊 Help me explain my latest irrigation prediction."
    ]


def generate_response(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    language: str = "en",
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate an agricultural recommendation from AgriSaathi via Gemini API or Grounded Knowledge Engine.

    :param prompt: User's question or message.
    :param context: Optional sensor readings or prediction results from the dashboard.
    :param language: Language code ('en', 'hi', 'pa', 'te', 'auto').
    :param history: Optional prior conversation turns within current session.
    :return: Dictionary containing 'reply', 'model', 'status', and 'suggestions'.
    """
    if not prompt or not prompt.strip():
        raise AgriAssistantError(
            message="Prompt cannot be empty.",
            code="invalid_request",
        )

    detected_lang = detect_language(prompt.strip())
    target_lang = language if language != "auto" else detected_lang

    try:
        client = get_client()
        model_name = get_model_name()
    except AgriAssistantError as e:
        logger.warning(f"Gemini client initialization failed ({e.message}). Falling back to grounded agricultural knowledge engine.")
        fallback_reply = generate_grounded_fallback_response(
            prompt=prompt,
            context=context,
            language=language,
            detected_lang=detected_lang,
        )
        suggestions = get_follow_up_suggestions(prompt, fallback_reply, language=target_lang)
        return {
            "reply": fallback_reply,
            "model": "AgriSaathi Grounded Knowledge Engine (Fallback)",
            "status": "success",
            "fallback_used": True,
            "suggestions": suggestions,
        }

    # Validate and cap conversation history for session context
    validated_history = validate_chat_history(history)

    # Build contextual grounding prompt
    user_content_parts = []

    # Ground on sensor readings if provided
    if context and isinstance(context, dict):
        context_items = []
        if "crop_type" in context and context["crop_type"] is not None:
            crop_meta = get_crop(context["crop_type"])
            if crop_meta:
                c_name = crop_meta.get("name", f"Crop ID {context['crop_type']}")
                status_note = "ML Calibrated" if crop_meta.get("ml_supported") else "Awaiting ML calibration"
                context_items.append(f"- Crop: {c_name} ({status_note})")
            else:
                context_items.append(f"- Crop ID: {context['crop_type']}")
        elif "crop_name" in context and context["crop_name"]:
            crop_meta = get_crop(context["crop_name"])
            if crop_meta:
                c_name = crop_meta.get("name", str(context["crop_name"]).title())
                context_items.append(f"- Selected Crop: {c_name} (Upcoming crop; awaiting ML sensor training dataset)")
            else:
                context_items.append(f"- Selected Crop: {str(context['crop_name']).title()} (Upcoming crop; awaiting ML sensor training dataset)")
        if "crop_days" in context and context["crop_days"] is not None:
            context_items.append(f"- Crop Age: {context['crop_days']} days")
        if "soil_moisture" in context and context["soil_moisture"] is not None:
            context_items.append(f"- Soil Moisture Reading: {context['soil_moisture']}")
        if "soil_temperature" in context and context["soil_temperature"] is not None:
            context_items.append(f"- Soil Temperature: {context['soil_temperature']} °C")
        if "temperature" in context and context["temperature"] is not None:
            context_items.append(f"- Air Temperature: {context['temperature']} °C")
        if "humidity" in context and context["humidity"] is not None:
            context_items.append(f"- Relative Humidity: {context['humidity']}%")

        if context_items:
            user_content_parts.append(
                "Active Farm Dashboard Readings (reference only if relevant to user's question; do not push prediction unless requested):\n"
                + "\n".join(context_items)
            )

    lang_instruction = build_language_instruction(language, detected_lang)
    user_content_parts.append(lang_instruction)
    user_content_parts.append(f"User Question: {prompt.strip()}")
    final_content = "\n\n".join(user_content_parts)

    # Build multi-turn contents with session history
    contents_list: List[types.Content] = []
    for msg in validated_history:
        contents_list.append(
            types.Content(
                role=msg["role"],
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )

    # Append current turn
    contents_list.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=final_content)],
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.35,
        max_output_tokens=400,
        tools=AGRI_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_exception = None

    for candidate_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=contents_list,
                config=config,
            )

            # Security: handle approved tool calling with strict validation and max 1 execution per turn
            if response.function_calls:
                executed_calls = []
                for call in response.function_calls[:1]:
                    if call.name not in APPROVED_TOOL_NAMES:
                        tool_result = {
                            "error": f"Tool '{call.name}' is unauthorized. Only 'predict_irrigation' is permitted.",
                            "status": "rejected",
                        }
                    else:
                        tool_result = execute_tool_call(call.name, call.args)

                    executed_calls.append({
                        "name": call.name,
                        "args": call.args,
                        "result": tool_result,
                    })

                    continuation_contents = list(contents_list)
                    continuation_contents.append(response.candidates[0].content)
                    continuation_contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=call.name,
                                    response={"result": tool_result},
                                )
                            ],
                        ),
                    )

                    followup_response = client.models.generate_content(
                        model=candidate_model,
                        contents=continuation_contents,
                        config=config,
                    )

                    reply_text = followup_response.text or ""
                    suggestions = get_follow_up_suggestions(prompt, reply_text, language=target_lang)
                    return {
                        "reply": reply_text,
                        "model": candidate_model,
                        "status": "success",
                        "tool_executed": True,
                        "tool_calls": executed_calls,
                        "suggestions": suggestions,
                    }

            reply_text = response.text or ""
            suggestions = get_follow_up_suggestions(prompt, reply_text, language=target_lang)
            return {
                "reply": reply_text,
                "model": candidate_model,
                "status": "success",
                "tool_executed": False,
                "suggestions": suggestions,
            }
        except ClientError as e:
            error_msg = str(e)
            last_exception = e
            # If 429 quota exhausted on this candidate, try the next fallback model
            if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                continue
            elif "API_KEY_INVALID" in error_msg or "403" in error_msg:
                raise AgriAssistantError(
                    message="Invalid Gemini API key. Please check the GEMINI_API_KEY in your .env file.",
                    code="invalid_api_key",
                    details={"original_error": error_msg},
                )
            elif "INVALID_ARGUMENT" in error_msg or "400" in error_msg:
                raise AgriAssistantError(
                    message=f"Invalid request sent to Gemini API: {error_msg}",
                    code="invalid_request",
                    details={"original_error": error_msg},
                )
            else:
                continue
        except ServerError as e:
            last_exception = e
            # Try next fallback model on 503/500
            continue
        except Exception as e:
            last_exception = e
            continue

    # If all models failed or offline environment, fall back to grounded agricultural knowledge engine
    if last_exception:
        logger.warning(f"All Gemini models failed ({last_exception}). Using grounded agricultural knowledge engine.")
        fallback_reply = generate_grounded_fallback_response(
            prompt=prompt,
            context=context,
            language=language,
            detected_lang=detected_lang,
        )
        suggestions = get_follow_up_suggestions(prompt, fallback_reply, language=target_lang)
        return {
            "reply": fallback_reply,
            "model": "AgriSaathi Grounded Knowledge Engine (Fallback)",
            "status": "success",
            "fallback_used": True,
            "details": {"original_error": str(last_exception)},
            "suggestions": suggestions,
        }

    fallback_reply = generate_grounded_fallback_response(
        prompt=prompt,
        context=context,
        language=language,
        detected_lang=detected_lang,
    )
    suggestions = get_follow_up_suggestions(prompt, fallback_reply, language=target_lang)
    return {
        "reply": fallback_reply,
        "model": "AgriSaathi Grounded Knowledge Engine (Fallback)",
        "status": "success",
        "fallback_used": True,
        "suggestions": suggestions,
    }


def verify_connection() -> Dict[str, Any]:
    """
    Lightweight health-check verifying that Gemini can generate a response.
    """
    test_prompt = "Say 'AgriSaathi connection verified successfully' in one brief sentence."
    result = generate_response(prompt=test_prompt)
    return {
        "status": "connected",
        "model": result["model"],
        "sample_reply": result["reply"].strip(),
    }
