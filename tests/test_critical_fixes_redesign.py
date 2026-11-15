"""
Unit and Integration Tests for Critical Fixes and Redesign:
1. Compact Login Page Redesign.
2. Pre-rendered 23-Language Selector (English + 22 Scheduled Indian Languages).
3. Circular Audio Controls (Listen, Pause, Mute).
4. Multilingual Voice Guide & Telugu Audio Fallback (/api/voice/tts).
5. AI Voice Assistant Network Error Fallback.
6. Structured 5-Section Farmer Dashboard (Removal of oversized hero banner).
"""

import re
import pytest
from app import app
from src.farm_manager import init_farm_db, register_farmer, get_farmer_by_id


@pytest.fixture
def client():
    app.config["TESTING"] = True
    init_farm_db()
    with app.test_client() as client:
        yield client


# ========================================================
# 1. Login Page Redesign & Compact Top-Right Language Bar
# ========================================================
def test_login_page_compact_redesign():
    with open("templates/login.html", "r", encoding="utf-8") as f:
        html = f.read()

    # Heading preserved
    assert "Welcome to Smart Irrigation Planner" in html
    assert "Welcome, Farmer" in html
    assert "Sign in to manage your farm" in html

    # Main focus is the login form
    assert 'id="formFarmerLogin"' in html
    assert 'id="loginUsername"' in html
    assert 'id="loginPassword"' in html
    assert 'id="btnLoginSubmit"' in html or 'id="btnSignIn"' in html

    # Circular audio controls in login header
    assert 'id="btnAudioListen"' in html
    assert 'id="btnAudioPause"' in html
    assert 'id="btnAudioMute"' in html

    # Compact language selector at top-right with globe icon
    assert "🌐" in html
    assert 'id="languageSelect"' in html

    # No oversized panels or permanent language lists
    assert "class=\"auth-top-controls\"" in html or "class=\"top-nav-controls\"" in html or "class=\"lang-selector-compact\"" in html


# ========================================================
# 2. Pre-rendered 23-Language Selector
# ========================================================
def test_all_23_languages_prerendered_in_templates():
    expected_codes = [
        "en", "hi", "te", "pa", "ta", "bn", "mr", "gu",
        "kn", "ml", "or", "as", "ur", "sa", "ne", "kok",
        "mai", "doi", "brx", "ks", "sd", "mni", "sat"
    ]

    for template in ["templates/login.html", "templates/index.html", "templates/register.html", "templates/onboarding.html"]:
        with open(template, "r", encoding="utf-8") as f:
            content = f.read()

        for code in expected_codes:
            assert f'value="{code}"' in content, f"Language option '{code}' missing from {template}"


# ========================================================
# 3. Compact Circular Audio Controls (Listen, Pause, Mute)
# ========================================================
def test_circular_audio_controls_and_controller_methods():
    for template in ["templates/login.html", "templates/index.html", "templates/register.html", "templates/onboarding.html"]:
        with open(template, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'id="btnAudioListen"' in content, f"Listen button missing from {template}"
        assert 'id="btnAudioPause"' in content, f"Pause button missing from {template}"
        assert 'id="btnAudioMute"' in content, f"Mute button missing from {template}"

    # Verify voice_controller.js implements AgriVoiceAudioPlayer with play, pause, resume, mute
    with open("static/voice_controller.js", "r", encoding="utf-8") as f:
        voice_js = f.read()

    assert "class AgriVoiceAudioPlayer" in voice_js
    assert "play(" in voice_js
    assert "pause(" in voice_js
    assert "resume(" in voice_js
    assert "mute(" in voice_js
    assert "window.AgriVoiceAudio" in voice_js
    assert "btnAudioListen" in voice_js
    assert "btnAudioPause" in voice_js
    assert "btnAudioMute" in voice_js

    # Verify style.css defines .btn-circular-audio
    with open("static/style.css", "r", encoding="utf-8") as f:
        css = f.read()

    assert ".btn-circular-audio" in css
    assert "border-radius: 50%" in css
    assert ".active-audio" in css
    assert ".paused-audio" in css
    assert ".muted-audio" in css


# ========================================================
# 4. Multilingual Voice Guide & Telugu Audio Fallback (/api/voice/tts)
# ========================================================
def test_multilingual_tts_endpoint_all_10_target_languages(client):
    dash_guides = {
        'en': 'Welcome to your Farm Dashboard. Section 1 shows your land summary. Section 2 shows live weather conditions. Section 3 lists your land sections. Section 4 lets you check irrigation and see schedules.',
        'hi': 'फार्म डैशबोर्ड में आपका स्वागत है। खंड 1 में भूमि सारांश देखें। खंड 2 में लाइव मौसम देखें। खंड 3 में खेत के हिस्से देखें। खंड 4 में सिंचाई की जांच करें और कार्यक्रम देखें।',
        'te': 'వ్యవసాయ డాష్‌బోర్డ్‌కి స్వాగతం. విభాగం 1 లో భూమి వివరాలు ఉంటాయి. విభాగం 2 లో వాతావరణం ఉంటుంది. విభాగం 3 లో భూమి విభాగాలు ఉంటాయి. విభాగం 4 లో సాగునీటి అవసరాన్ని తనిఖీ చేయండి.',
        'pa': 'ਫਾਰਮ ਡੈਸ਼ਬੋਰਡ ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ। ਸੈਕਸ਼ਨ 1 ਵਿੱਚ ਜ਼ਮੀਨ ਦਾ ਸੰਖੇਪ ਹੈ। ਸੈਕਸ਼ਨ 2 ਵਿੱਚ ਲਾਈਵ ਮੌਸਮ ਹੈ। ਸੈਕਸ਼ਨ 3 ਵਿੱਚ ਜ਼ਮੀਨ ਦੇ ਹਿੱਸੇ ਹਨ। ਸੈਕਸ਼ਨ 4 ਵਿੱਚ ਸਿੰਚਾਈ ਦੀ ਜਾਂਚ ਕਰੋ।',
        'ta': 'பண்ணை டாஷ்போர்டுக்கு வரவேற்கிறோம். பிரிவு 1 நில விவரங்களையும், பிரிவு 2 நேரடி வானிலையையும், பிரிவு 3 நிலப் பிரிவுகளையும், பிரிவு 4 பாசனத் தேவைகளையும் காட்டுகிறது.',
        'kn': 'ಕೃಷಿ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಸುಸ್ವಾಗತ. ವಿಭಾಗ 1 ಜಮೀನಿನ ವಿವರ, ವಿಭಾಗ 2 ಲೈವ್ ಹವಾಮಾನ, ವಿಭಾಗ 3 ಜಮೀನಿನ ಭಾಗಗಳು, ವಿಭಾಗ 4 ನೀರಾವರಿ ಪರೀಕ್ಷಿಸಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ.',
        'ml': 'ഫാം ഡാഷ്‌ബോർഡിലേക്ക് സ്വാഗതം. വിഭാഗം 1 ഭൂമിയുടെ വിവരങ്ങളും, വിഭാഗം 2 തത്സമയ കാലാവസ്ഥയും, വിഭാഗം 3 വിഭാഗങ്ങളും, വിഭാഗം 4 നനയ്ക്കൽ പരിശോധനയും നൽകുന്നു.',
        'bn': 'খামার ড্যাশবোর্ডে স্বাগতম। বিভাগ ১ জমির বিবরণ, বিভাগ ২ লাইভ আবহাওয়া, বিভাগ ৩ জমির অংশ এবং বিভাগ ৪ সেচ পরীক্ষা প্রদর্শন করে।',
        'mr': 'फार्म डॅशबोर्डवर आपले स्वागत आहे. विभाग 1 मध्ये जमिनीचा सारांश, विभाग 2 मध्ये थेट हवामान, विभाग 3 मध्ये शेताचे तुकडे आणि विभाग 4 मध्ये सिंचन तपासणी आहे.',
        'gu': 'ફાર્મ ડેશબોર્ડમાં આપનું સ્વાગત છે. વિભાગ 1 માં જમીનની માહિતી, વિભાગ 2 માં લાઈવ હવામાન, વિભાગ 3 માં પ્લોટ અને વિભાગ 4 માં સિંચાઈ તપાસો.'
    }

    import urllib.parse
    for lang, guide_text in dash_guides.items():
        q = urllib.parse.quote(guide_text)
        res_guide = client.get(f"/api/voice/tts?lang={lang}&text={q}")
        assert res_guide.status_code == 200, f"TTS endpoint failed for {lang}"
        assert res_guide.content_type in ["audio/mpeg", "audio/wav"], f"MIME type invalid for {lang}"
        assert len(res_guide.data) > 1000, f"Audio data too small for {lang}"


# ========================================================
# 5. Fix AI Voice Assistant – Network Error Fallback
# ========================================================
def test_chat_voice_network_error_fallback():
    with open("static/chat.js", "r", encoding="utf-8") as f:
        chat_js = f.read()

    # Verify event.error === "network" does NOT throw a dead-end failure
    assert 'event.error === "network"' in chat_js
    assert "handleVoiceNetworkFallback" in chat_js
    assert "renderVoiceFallbackChips" in chat_js
    assert "Network error during speech recognition" not in chat_js


# ========================================================
# 6. Structured 5-Section Farmer Dashboard (Hero banner removed)
# ========================================================
def test_dashboard_5_sections_and_hero_banner_removal():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        index_html = f.read()

    # 1. section.hero is completely removed
    assert '<section class="hero">' not in index_html
    assert "hero-eyebrow" not in index_html
    assert "Example sensor indicators" not in index_html

    # 2. Section 1: Farm Overview (4 compact cards in one row + progress bar)
    assert 'id="sectionFarmOverview"' in index_html
    assert "overview-grid-4" in index_html
    assert 'id="landStatTotal"' in index_html
    assert 'id="landStatAllocated"' in index_html
    assert 'id="landStatAvailable"' in index_html
    assert 'id="landStatSections"' in index_html
    assert 'id="landProgressBar"' in index_html

    # 3. Section 2: Live Weather (5 compact cards of consistent height)
    assert 'id="sectionWeather"' in index_html
    assert "weather-grid-5" in index_html
    assert 'id="weatherTempDisplay"' in index_html
    assert 'id="weatherHumidityDisplay"' in index_html
    assert 'id="weatherRainDisplay"' in index_html
    assert 'id="weatherForecast24Display"' in index_html
    assert 'id="weatherSoilTempDisplay"' in index_html

    # 4. Section 3: Land Sections (Actual cards, Add button)
    assert 'id="sectionLandSections"' in index_html
    assert 'id="btnAddSectionModalBtn"' in index_html
    assert 'id="sectionsCardsGrid"' in index_html

    # 5. Section 4: Irrigation Workspace (Balanced 2-column layout)
    assert 'id="sectionIrrigationWorkspace"' in index_html
    assert 'id="irrigation-planner"' in index_html
    assert 'id="results"' in index_html

    # 6. Section 5: AI Assistant (Floating 52px button with 🤖 icon)
    assert 'id="agriChatToggle"' in index_html
    assert "🤖" in index_html
    assert 'id="agriChatWindow"' in index_html

    # Container width is 1240px
    assert "dashboard-main-container" in index_html
