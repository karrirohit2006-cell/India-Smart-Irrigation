"""
Tests for Complete Multilingual Voice-Controlled Smart Irrigation Planner.
Validates all 22 scheduled Indian languages + English (23 languages total):
1. Assamese (as), 2. Bengali (bn), 3. Bodo (brx), 4. Dogri (doi), 5. Gujarati (gu),
6. Hindi (hi), 7. Kannada (kn), 8. Kashmiri (ks), 9. Konkani (kok), 10. Maithili (mai),
11. Malayalam (ml), 12. Manipuri (mni), 13. Marathi (mr), 14. Nepali (ne), 15. Odia (or),
16. Punjabi (pa), 17. Sanskrit (sa), 18. Santali (sat), 19. Sindhi (sd), 20. Tamil (ta),
21. Telugu (te), 22. Urdu (ur), 23. English (en).

Covers:
- Translation resource completeness (all 69 keys non-empty for all 23 languages)
- Language Registry and Capabilities Matrix (transparent Tier 1 vs Tier 2)
- Exhaustive 7 core voice commands across all 23 languages (161 actions)
- TTS endpoint audio generation for all 23 languages
- Direction verification (LTR vs RTL for Urdu, Kashmiri, Sindhi)
- Security: Sensitive credential sanitization before speech generation
"""

import os
import json
import pytest
from pathlib import Path

from app import app
from src.languages_registry import (
    LANGUAGES_REGISTRY,
    list_all_languages,
    get_language_capabilities_matrix,
    get_language,
    register_new_language,
    LanguageDefinition,
)
from src.translation_manager import (
    get_translations,
    get_all_translations,
    get_text,
    TRANSLATIONS_DIR,
)
from src.voice_triggers import (
    COMMANDS_23_LANGUAGES,
    DASHBOARD_TRIGGERS,
    FARM_SUMMARY_TRIGGERS,
    SELECT_SECTION_TRIGGERS,
    CHECK_IRRIGATION_TRIGGERS,
    UPCOMING_SCHEDULE_TRIGGERS,
    EXPLAIN_PREDICTION_TRIGGERS,
    HISTORY_TRIGGERS,
)
from src.voice_command_engine import process_voice_command
from src.voice_providers import sanitize_speech_text, get_tts_audio
from src.farm_manager import (
    register_farmer,
    get_farmer_farms,
    get_farm_sections,
    create_section,
    update_farmer_onboarding,
)


ALL_23_LANG_CODES = [
    "as", "bn", "brx", "doi", "gu", "hi", "kn", "ks", "kok",
    "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat",
    "sd", "ta", "te", "ur", "en"
]

STANDARD_69_KEYS = [
    "welcomeHeader", "tagline", "subtext", "languageLabel", "welcomeFarmer",
    "signInToManage", "btnLoginFaceLock", "btnFaceLockSub", "orSignInWithPassword",
    "usernameLabel", "usernamePlaceholder", "passwordLabel", "passwordPlaceholder",
    "confirmPasswordLabel", "confirmPasswordPlaceholder", "btnSignIn", "btnCreateAccount",
    "newFarmerPrompt", "createAccountLink", "alreadyAccountPrompt", "loginLink",
    "superAdminPortal", "activeFarmBadge", "syncLiveWeather", "landTotalLabel",
    "landCultivatedLabel", "landAvailableLabel", "landSectionsLabel", "btnAddSection",
    "btnEditSection", "btnDeleteSection", "emptySectionText", "sectionAreaLabel",
    "cropLabel", "soilTempLabel", "moistureLabel", "formTitle", "stateLabel",
    "predict", "resultTitle", "resultPlaceholder", "irrigate", "noIrrigate",
    "probability", "upcomingScheduleTitle", "calendarTitle", "monitor", "settings",
    "logout", "voiceWelcomeSpeech", "voiceGuideBtn", "voiceGuideTitle", "voiceMicBtn",
    "voiceListening", "voiceRecognized", "voiceActionDone", "disclaimer",
    "onboardingStep1", "onboardingStep2", "onboardingStep3", "onboardingStep4",
    "nextStep", "prevStep", "saveOnboarding", "pageGuideLogin", "pageGuideDashboard",
    "pageGuideOnboard", "pageGuidePlanner"
]


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def seeded_farmer():
    """Create a verified test farmer with a farm and sections for voice actions."""
    username = f"voice_all_test_{os.urandom(4).hex()}"
    farmer = register_farmer(username, "pass12345", name="Multilingual Test Farmer")
    fid = farmer["id"]

    # Complete onboarding with state and farm details so ML predictions succeed
    update_farmer_onboarding(
        farmer_id=fid,
        name="Multilingual Test Farmer",
        state="Punjab",
        district="Ludhiana",
        total_land=5.0,
    )

    farms = get_farmer_farms(fid)
    farm_id = farms[0]["id"]

    # Ensure two sections exist
    sec1 = create_section(farm_id, fid, "Section 01", 0.50, is_empty=False, crop="Rice")
    sec2 = create_section(farm_id, fid, "Section 02", 0.50, is_empty=False, crop="Wheat")

    return {
        "farmer_id": fid,
        "farm_id": farm_id,
        "sec1_id": sec1["id"],
        "sec2_id": sec2["id"],
    }


# ==============================================================================
# 1. Translation Resource Completeness across all 23 Languages
# ==============================================================================
def test_all_23_json_files_exist_and_complete():
    """Verify that each of the 23 language translation files has all standard keys non-empty."""
    for code in ALL_23_LANG_CODES:
        file_path = TRANSLATIONS_DIR / f"{code}.json"
        assert file_path.exists(), f"Translation file missing: {file_path}"

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict), f"{code}.json must contain a JSON object."
        for key in STANDARD_69_KEYS:
            assert key in data, f"Key '{key}' missing from {code}.json"
            val = str(data[key]).strip()
            assert len(val) > 0, f"Key '{key}' in {code}.json is empty."


def test_translation_manager_loading():
    """Verify translation manager cached disk-loading and fallback."""
    for code in ALL_23_LANG_CODES:
        translations = get_translations(code)
        assert translations is not None
        assert "welcomeHeader" in translations

    # Test unknown language falls back to English
    fallback = get_translations("xyz_non_existent")
    assert fallback is not None
    assert fallback["welcomeHeader"] == "Welcome to Smart Irrigation Planner"


# ==============================================================================
# 2. Language Registry and Transparent Capabilities Matrix
# ==============================================================================
def test_language_registry_and_capabilities():
    """Verify language definitions, script family, and honest capability separation."""
    languages = list_all_languages()
    assert len(languages) >= 23

    matrix = get_language_capabilities_matrix()
    assert len(matrix) >= 23

    # RTL verification: Urdu, Kashmiri, Sindhi must be RTL
    assert matrix["ur"]["direction"] == "rtl"
    assert matrix["ks"]["direction"] == "rtl"
    assert matrix["sd"]["direction"] == "rtl"

    # LTR verification
    assert matrix["en"]["direction"] == "ltr"
    assert matrix["hi"]["direction"] == "ltr"
    assert matrix["te"]["direction"] == "ltr"

    # Honest STT/TTS capability separation (Section 8 requirement)
    tier1_langs = ["en", "hi", "te", "pa", "ta", "bn", "mr", "gu", "kn", "ml", "or", "as", "ur", "ne", "sa"]
    for c in tier1_langs:
        assert matrix[c]["stt_supported"] is True, f"{c} should have STT supported"
        assert matrix[c]["tts_supported"] is True, f"{c} should have TTS supported"

    tier2_langs = ["kok", "mai", "doi", "brx", "ks", "sd", "mni", "sat"]
    for c in tier2_langs:
        assert matrix[c]["stt_supported"] is False, f"{c} STT must be honestly reported as False"
        assert matrix[c]["tts_supported"] is False, f"{c} TTS must be honestly reported as False"
        assert (
            "not natively supported" in matrix[c]["provider_notes"].lower()
            or "synthesized" in matrix[c]["provider_notes"].lower()
            or "waveform" in matrix[c]["provider_notes"].lower()
            or "chime" in matrix[c]["provider_notes"].lower()
            or "tone" in matrix[c]["provider_notes"].lower()
        )


def test_extensibility_register_new_language():
    """Verify system architecture allows adding new languages dynamically."""
    new_lang = LanguageDefinition(
        code="fr",
        name="French",
        native_name="Français",
        bcp47="fr-FR",
        direction="ltr",
        script_family="Latin",
        stt_supported=True,
        tts_supported=True,
        provider_notes="WebSpeech + Google TTS",
    )
    register_new_language(new_lang)

    fetched = get_language("fr")
    assert fetched is not None
    assert fetched.name == "French"
    assert fetched.native_name == "Français"


# ==============================================================================
# 3. Exhaustive 7-Command Coverage across ALL 23 Languages (161 Actions)
# ==============================================================================
@pytest.mark.parametrize("lang_code", ALL_23_LANG_CODES)
def test_all_7_voice_commands_per_language(lang_code, seeded_farmer):
    """
    Exhaustively test each of the 7 required voice actions in all 23 languages:
    1. Open dashboard
    2. Show my farm details
    3. Select my first section
    4. Check irrigation
    5. Show tomorrow's schedule
    6. Explain my prediction
    7. Open irrigation history
    """
    fid = seeded_farmer["farmer_id"]
    ctx = {
        "farm_id": seeded_farmer["farm_id"],
        "active_section_id": seeded_farmer["sec1_id"],
        "active_section_name": "Section 01",
    }

    cmd_dict = COMMANDS_23_LANGUAGES[lang_code]

    # 1. Open Dashboard
    d_cmd = cmd_dict["dashboard"]
    res_d = process_voice_command(fid, d_cmd, language=lang_code, context=ctx)
    assert res_d["status"] == "success", f"Dashboard failed for {lang_code}: {res_d}"
    assert res_d["action"] == "navigate_to_page"
    assert res_d["action_payload"]["target"] == "dashboard"
    assert len(res_d["spoken_response"]) > 0

    # 2. Show Farm Details
    f_cmd = cmd_dict["farm_details"]
    res_f = process_voice_command(fid, f_cmd, language=lang_code, context=ctx)
    assert res_f["status"] == "success", f"Farm summary failed for {lang_code}: {res_f}"
    assert res_f["action"] == "get_farm_summary"
    assert len(res_f["spoken_response"]) > 0

    # 3. Select First Section
    s_cmd = cmd_dict["select_first"]
    res_s = process_voice_command(fid, s_cmd, language=lang_code, context=ctx)
    assert res_s["status"] == "success", f"Select section failed for {lang_code}: {res_s}"
    assert res_s["action"] == "select_section"
    assert len(res_s["spoken_response"]) > 0

    # 4. Check Irrigation
    c_cmd = cmd_dict["check_irrigation"]
    res_c = process_voice_command(fid, c_cmd, language=lang_code, context=ctx)
    assert res_c["status"] == "success", f"Check irrigation failed for {lang_code}: {res_c}"
    assert res_c["action"] == "run_irrigation_prediction"
    assert res_c["action_payload"]["decision"] in ("IRRIGATE", "DO NOT IRRIGATE")
    assert len(res_c["spoken_response"]) > 0

    # 5. Show Tomorrow's / Upcoming Schedule
    u_cmd = cmd_dict["upcoming"]
    res_u = process_voice_command(fid, u_cmd, language=lang_code, context=ctx)
    assert res_u["status"] == "success", f"Upcoming schedule failed for {lang_code}: {res_u}"
    assert res_u["action"] == "get_upcoming_schedule"
    assert len(res_u["spoken_response"]) > 0

    # 6. Explain Prediction
    e_cmd = cmd_dict["explain"]
    res_e = process_voice_command(fid, e_cmd, language=lang_code, context=ctx)
    assert res_e["status"] == "success", f"Explain prediction failed for {lang_code}: {res_e}"
    assert res_e["action"] == "explain_prediction"
    assert len(res_e["spoken_response"]) > 0

    # 7. Open Irrigation History
    h_cmd = cmd_dict["history"]
    res_h = process_voice_command(fid, h_cmd, language=lang_code, context=ctx)
    assert res_h["status"] == "success", f"History failed for {lang_code}: {res_h}"
    assert res_h["action"] == "navigate_to_page"
    assert res_h["action_payload"]["target"] == "irrigation_history"
    assert len(res_h["spoken_response"]) > 0


# ==============================================================================
# 4. Flask API Endpoints Integration Tests
# ==============================================================================
def test_api_languages_endpoints(client):
    """Verify /api/languages and /api/languages/capabilities REST endpoints."""
    res = client.get("/api/languages")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert len(data["languages"]) >= 23

    res_cap = client.get("/api/languages/capabilities")
    assert res_cap.status_code == 200
    cap_data = res_cap.get_json()
    assert cap_data["status"] == "success"
    assert "te" in cap_data["capabilities"]
    assert "ur" in cap_data["capabilities"]
    assert cap_data["capabilities"]["ur"]["direction"] == "rtl"


def test_api_translations_endpoint(client):
    """Verify /api/translations/<lang> serves proper JSON translation dictionaries."""
    for code in ["te", "hi", "ur", "pa", "en", "ta", "kn"]:
        res = client.get(f"/api/translations/{code}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["language"] == code
        assert "welcomeHeader" in data["translations"]


def test_api_voice_tts_endpoint_all_23_languages(client):
    """Verify TTS endpoint returns valid audio bytes for all 23 languages without error."""
    sample_texts = {
        "en": "Irrigation scheduled for tomorrow.",
        "te": "రేపటికి సాగునీరు షెడ్యూల్ చేయబడింది.",
        "hi": "कल के लिए सिंचाई निर्धारित की गई है।",
        "pa": "ਕੱਲ੍ਹ ਲਈ ਸਿੰਚਾਈ ਤੈਅ ਕੀਤੀ ਗਈ ਹੈ।",
        "ta": "நாளைக்கான பாசனம் திட்டமிடப்பட்டுள்ளது.",
        "bn": "আগামীকালের জন্য সেচ নির্ধারিত হয়েছে।",
        "mr": "उद्यासाठी सिंचन नियोजित केले आहे.",
        "gu": "આવતીકાલ માટે સિંચાઈનું આયોજન કરવામાં આવ્યું છે.",
        "kn": "ನಾಳೆಗೆ ನೀರಾವರಿ ನಿಗದಿಪಡಿಸಲಾಗಿದೆ.",
        "ml": "നാളത്തേക്ക് ജലസേചനം നിശ്ചയിച്ചിട്ടുണ്ട്.",
        "or": "ଆସନ୍ତାକାଲି ପାଇଁ ଜଳସେଚନ ନିର୍ଦ୍ଧାରିତ ହୋଇଛି.",
        "as": "কাইলৈৰ বাবে জলসিঞ্চন নিৰ্ধাৰণ কৰা হৈছে।",
        "ur": "کل کے لیے آبپاشی کا شیڈول طے کیا گیا ہے۔",
        "sa": "श्वः कृते सेचनं निर्धारितम् अस्ति।",
        "ne": "भोलिको लागि सिँचाइ तालिका बनाइएको छ।",
        "kok": "फाल्या खातीर शिंपणेची येवजण केल्या.",
        "mai": "काल्हिक लेल सिंचाई निर्धारित कएल गेल अछि.",
        "doi": "कल्ल आस्तै सिंचाई तय कीती गेई ऐ.",
        "brx": "गाबोननि थाखाय दै होनाय थि खालामबाय.",
        "ks": "پگاہس خٲطرٕ آبپاشی ہنٛد شیڈول.",
        "sd": "سڀاڻي لاءِ آبپاشي جو شيڊول مقرر ڪيو ويو آهي.",
        "mni": "হয়েংগীদমক ঈথৈ ফিবম সেমখ্রে.",
        "sat": "ᱜᱟᱯᱟ ᱞᱟᱹᱜᱤᱫ ᱫᱟᱜ ᱫᱩᱞ ᱴᱷᱟᱹᱣᱠᱟᱹ ᱟᱠᱟᱱᱟ."
    }

    for code in ALL_23_LANG_CODES:
        text = sample_texts.get(code, "Irrigation test")
        res = client.get(f"/api/voice/tts?text={text}&lang={code}")
        assert res.status_code == 200
        assert res.mimetype in ("audio/mpeg", "audio/wav")
        assert len(res.data) > 0, f"Empty audio for {code}"


def test_api_voice_command_returns_language_capability(client):
    """Verify /api/voice/command response attaches language capability metadata."""
    res = client.post("/api/voice/command", json={
        "message": "Open dashboard",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "language_capability" in data
    assert data["language_capability"]["code"] == "en"
    assert data["language_capability"]["stt_supported"] is True


# ==============================================================================
# 5. Security & Credential Sanitization
# ==============================================================================
def test_sensitive_credential_sanitization():
    """Verify passwords, OTPs, passkeys, and tokens are scrubbed from speech synthesis."""
    dirty_text = "Your password is Secret12345! and OTP is 987654. Passkey credentialId a1b2c3d4."
    clean_text = sanitize_speech_text(dirty_text)

    assert "Secret12345!" not in clean_text
    assert "987654" not in clean_text
    assert "a1b2c3d4" not in clean_text
    assert "[CONFIDENTIAL]" in clean_text
