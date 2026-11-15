/**
 * Smart Irrigation Planner - Complete Voice-Controlled Website Integration
 * Connects speech recognition and AI action dispatcher with real website components:
 * navigation, forms, dropdowns, buttons, land section management, irrigation planner,
 * dual calendars, weather synchronization, and audio verbal confirmations.
 *
 * Supports English + 22 Scheduled Indian Languages (Telugu, Hindi, Punjabi, Tamil,
 * Kannada, Malayalam, Bengali, Marathi, Gujarati, etc.).
 */

class AgriVoiceWebsiteController {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.statusBanner = null;
        this.pendingAction = null;
        this.lastResponse = null;
        this.currentTranscript = "";
        this.speakerEnabled = true;
        try {
            this.speakerEnabled = (localStorage.getItem("va_speaker_enabled") !== "false");
        } catch (e) {
            this.speakerEnabled = true;
        }

        this.initRecognition();
        this.initVisualFeedback();
        this.initSpeakerToggle();
        this.initNavMic();
        this.bindVoiceDeckControls();
    }

    initSpeakerToggle() {
        try {
            const saved = localStorage.getItem("va_speaker_enabled");
            this.speakerEnabled = (saved !== "false");
        } catch (e) {
            this.speakerEnabled = true;
        }

        const btn = document.getElementById("btnVoiceSpeakerToggle");
        if (btn && !btn._speakerBound) {
            btn._speakerBound = true;
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.speakerEnabled = !this.speakerEnabled;
                try {
                    localStorage.setItem("va_speaker_enabled", this.speakerEnabled.toString());
                } catch (err) {}

                if (!this.speakerEnabled && window.AgriVoiceAudio) {
                    window.AgriVoiceAudio.stopCurrent();
                }

                this.updateSpeakerUI();
                this.updateFeedback(
                    this.speakerEnabled ? "success" : "info",
                    this.speakerEnabled ? "🔊 Voice Assistant Speaker ON" : "🔇 Voice Assistant Speaker Muted (Silent Mode)"
                );
            });
        }
        this.updateSpeakerUI();
    }

    updateSpeakerUI() {
        const btn = document.getElementById("btnVoiceSpeakerToggle");
        const icon = document.getElementById("vaSpeakerIcon");
        const badge = document.getElementById("vaSpeakerBadge");
        if (!btn) return;

        if (this.speakerEnabled) {
            btn.classList.add("speaker-on");
            btn.classList.remove("speaker-off");
            btn.setAttribute("aria-label", "Mute Voice Assistant Speaker Speech");
            btn.title = "Speaker Speech is ON (Click to Mute)";
            if (icon) icon.textContent = "🔊";
            if (badge) {
                badge.textContent = "ON";
                badge.className = "va-speaker-badge va-badge-on";
            }
        } else {
            btn.classList.remove("speaker-on");
            btn.classList.add("speaker-off");
            btn.setAttribute("aria-label", "Enable Voice Assistant Speaker Speech");
            btn.title = "Speaker Speech is OFF (Click to Unmute)";
            if (icon) icon.textContent = "🔇";
            if (badge) {
                badge.textContent = "OFF";
                badge.className = "va-speaker-badge va-badge-off";
            }
        }
    }

    initNavMic() {
        const btn = document.getElementById("btnVoiceNavMic");
        if (btn && !btn._voiceBound) {
            btn._voiceBound = true;
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (this.isListening) {
                    // Click 2 (RECORDING OFF): Stops recording immediately, sends command, executes action
                    this.stopListening(true);
                } else {
                    // Click 1 (RECORDING ON): Starts listening immediately with visual indicator
                    this.startListening();
                }
            });
        }
    }

    initRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
            this.recognition = new SpeechRec();
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.maxAlternatives = 1;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUIState("listening");
                this.updateFeedback("listening", "🎙️ Recording... Speak your command (Click Voice button again to execute)");
            };

            this.recognition.onresult = (event) => {
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
                if (recognized) {
                    this.currentTranscript = recognized;
                    const transcriptInput = document.getElementById("vaTranscriptInput");
                    if (transcriptInput) transcriptInput.value = recognized;
                    this.updateFeedback("listening", `🎙️ Recording: "${recognized}" (Click Voice again to run)`);
                }
            };

            this.recognition.onerror = (event) => {
                console.warn("Speech recognition error:", event.error);
                if (event.error === "no-speech") {
                    // Farmer may be pausing between sentences; keep listening
                    return;
                }
                this.isListening = false;
                this.updateUIState("idle");

                if (event.error === "not-allowed") {
                    this.updateFeedback("error", "⚠️ Microphone permission denied. Please allow microphone access.");
                } else if (event.error === "network") {
                    this.updateFeedback("info", "🎙️ Voice Ready — click Voice again when ready.");
                } else {
                    this.updateFeedback("error", `⚠️ Voice recognition: ${event.error}`);
                }
            };

            this.recognition.onend = () => {
                if (this.isListening) {
                    // Continuous speech: keep listening until the farmer presses Click 2
                    try {
                        this.recognition.start();
                    } catch (err) {
                        this.isListening = false;
                        this.updateUIState("idle");
                    }
                } else {
                    this.updateUIState("idle");
                }
            };
        } else {
            console.log("Web Speech API not supported. Falling back to text-based voice command execution.");
        }
    }

    initVisualFeedback() {
        let banner = document.getElementById("voiceFeedbackBanner");
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "voiceFeedbackBanner";
            banner.className = "voice-feedback-banner";
            banner.style.cssText = `
                position: fixed;
                bottom: 24px;
                left: 50%;
                transform: translateX(-50%) translateY(100px);
                background: #0f172a;
                color: #ffffff;
                padding: 12px 22px;
                border-radius: 999px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.3);
                font-size: 14px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
                z-index: 10001;
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
                border: 1.5px solid #22c55e;
                pointer-events: none;
                opacity: 0;
            `;
            document.body.appendChild(banner);
        }
        this.statusBanner = banner;
    }

    updateFeedback(type, message) {
        if (!this.statusBanner) return;
        this.statusBanner.textContent = message;
        this.statusBanner.style.opacity = "1";
        this.statusBanner.style.transform = "translateX(-50%) translateY(0)";

        if (type === "error") {
            this.statusBanner.style.borderColor = "#ef4444";
        } else if (type === "success") {
            this.statusBanner.style.borderColor = "#22c55e";
        } else {
            this.statusBanner.style.borderColor = "#38bdf8";
        }

        if (type !== "listening") {
            setTimeout(() => this.hideFeedback(), 3000);
        }
    }

    hideFeedback() {
        if (!this.statusBanner) return;
        this.statusBanner.style.opacity = "0";
        this.statusBanner.style.transform = "translateX(-50%) translateY(100px)";
    }

    updateUIState(state) {
        const isRec = (state === "listening");
        const navMicBtn = document.getElementById("btnVoiceNavMic");
        const recordingDot = document.getElementById("vaRecordingDot");
        const statusPill = document.getElementById("vaNavStatusPill");
        const statusDot = document.getElementById("vaNavStatusDot");
        const statusText = document.getElementById("vaNavStatusText");

        if (navMicBtn) {
            navMicBtn.classList.toggle("mic-listening", isRec);
            navMicBtn.classList.toggle("mic-idle", !isRec);
            navMicBtn.setAttribute("aria-pressed", isRec ? "true" : "false");
            navMicBtn.title = isRec ? "Recording... (Click to stop and execute command)" : "Voice Control (Click once to record, click again to stop and execute)";
            const textSpan = navMicBtn.querySelector(".btn-ctrl-text");
            if (textSpan) textSpan.remove();
        }

        if (recordingDot) {
            recordingDot.style.display = isRec ? "inline-block" : "none";
        }

        if (statusPill) {
            if (isRec) {
                statusPill.style.display = "inline-flex";
                statusPill.textContent = "Listening...";
                statusPill.style.color = "#ef4444";
            } else if (state === "processing") {
                statusPill.style.display = "inline-flex";
                statusPill.textContent = "Processing...";
                statusPill.style.color = "#38bdf8";
            } else {
                statusPill.style.display = "none";
                statusPill.textContent = "Ready";
            }
        }

        if (statusDot) {
            statusDot.className = "va-nav-status-dot";
            if (state === "listening") statusDot.classList.add("dot-listening");
            else if (state === "processing") statusDot.classList.add("dot-processing");
            else statusDot.classList.add("dot-ready");
        }

        if (statusText) {
            if (state === "listening") statusText.textContent = "Listening...";
            else if (state === "processing") statusText.textContent = "Processing...";
            else statusText.textContent = "Voice: Ready";
        }

        const micBtns = document.querySelectorAll("#vaMicBtn, .btn-voice-mic, #btnVoiceMicHero, #btnVoiceMicOnboard");
        const stopBtns = document.querySelectorAll("#vaStopBtn");
        const recordPills = document.querySelectorAll("#vaRecordingPill");

        micBtns.forEach(btn => {
            btn.classList.toggle("recording-active", isRec);
            btn.setAttribute("aria-pressed", isRec);
        });

        stopBtns.forEach(btn => {
            btn.disabled = !isRec;
        });

        recordPills.forEach(pill => {
            pill.style.display = isRec ? "inline-flex" : "none";
        });
    }

    startListening() {
        if (!this.recognition) {
            this.updateFeedback("info", "Microphone voice recognition requires browser Speech API.");
            return;
        }

        if (this.isListening) {
            this.stopListening(true);
            return;
        }

        this.currentTranscript = "";

        // Stop any current audio speech playback before listening
        if (window.AgriVoiceAudio) {
            window.AgriVoiceAudio.stopCurrent();
        }

        const langMeta = (typeof SUPPORTED_LANGUAGES !== "undefined")
            ? SUPPORTED_LANGUAGES.find(l => l.code === (window.AgriI18n ? window.AgriI18n.currentLang : "en"))
            : null;

        if (langMeta && langMeta.stt_supported === false) {
            this.updateFeedback(
                "info",
                `ℹ️ Browser speech recognition is not natively supported for ${langMeta.nativeName} (${langMeta.name}). Please type your command in ${langMeta.nativeName} script below or speak in Hindi/English.`
            );
            const transcriptInput = document.getElementById("vaTranscriptInput") || document.getElementById("agriChatInput");
            if (transcriptInput) transcriptInput.focus();
            return;
        }

        this.recognition.lang = langMeta ? langMeta.bcp47 : "en-IN";

        try {
            this.isListening = true;
            this.recognition.start();
            this.updateUIState("listening");
        } catch (err) {
            console.warn("Recognition start error:", err);
        }
    }

    stopListening(execute = true) {
        this.isListening = false;
        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (err) {}
        }
        this.updateUIState("idle");

        if (execute && this.currentTranscript && this.currentTranscript.trim()) {
            const cmd = this.currentTranscript.trim();
            this.currentTranscript = "";
            this.executeCommand(cmd);
        }
    }

    processVoiceCommand(rawText) {
        return this.executeCommand(rawText);
    }

    async executeCommand(rawText) {
        if (!rawText || !rawText.trim()) return;
        const text = rawText.trim();
        const activeLang = window.AgriI18n ? window.AgriI18n.currentLang : "en";

        // Determine current page context
        const isDashboard = !!document.getElementById("landManagementModule");
        const isOnboard = !!document.getElementById("paneStep1");
        const pageContext = isDashboard ? "dashboard" : (isOnboard ? "onboarding" : "login");

        const context = {
            page: pageContext,
            active_section_id: window.activeSectionId || null,
            farm_id: window.currentFarm ? window.currentFarm.id : null,
            pending_action: this.pendingAction || null
        };

        this.updateFeedback("info", `⚡ Understanding command: "${text}"...`);
        this.updateUIState("processing");

        try {
            const res = await fetch("/api/voice/command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    language: activeLang,
                    context: context
                })
            });

            const data = await res.json();
            if (!res.ok || data.status === "error") {
                this.updateFeedback("error", `⚠️ ${data.error || "Could not process command"}`);
                return;
            }

            this.lastResponse = data;

            // 1. Handle Confirmation Required (Destructive actions)
            if (data.requires_confirmation) {
                this.pendingAction = {
                    action: data.action,
                    payload: data.action_payload
                };
                this.showConfirmationBox(data.confirmation_prompt || data.spoken_response);
                if (this.speakerEnabled && data.spoken_response && window.AgriVoiceAudio) {
                    window.AgriVoiceAudio.play(data.spoken_response, data.language || activeLang);
                }
                return;
            }

            // 2. Clear pending action if confirmed or normal action
            this.pendingAction = null;
            this.hideConfirmationBox();

            // 3. Dispatch and execute the corresponding website action
            if (data.action && data.action !== "general_query" && data.action !== "ask_clarification") {
                await this.dispatchWebsiteAction(data.action, data.action_payload || {});
            }

            // 4. Update subtle 3-second UI feedback toast (no large screen blocking panel)
            const feedbackText = data.display_text || data.spoken_response || "Command executed successfully.";
            this.showActionFeedback(`✓ ${feedbackText}`);
            this.updateFeedback("success", `✅ ${feedbackText}`);

            // 5. Assistant confirms verbally in farmer's selected language when speaker is enabled
            if (this.speakerEnabled && data.spoken_response && window.AgriVoiceAudio) {
                window.AgriVoiceAudio.play(data.spoken_response, data.language || activeLang);
            }

        } catch (err) {
            console.error("Voice command execution error:", err);
            this.updateFeedback("error", "⚠️ Network error executing voice command.");
        } finally {
            this.updateUIState("idle");
        }
    }

    async dispatchWebsiteAction(action, payload) {
        console.log("Dispatching Website Action:", action, payload);

        switch (action) {
            case "navigate_to_page":
                this.handleNavigationAction(payload);
                break;

            case "select_crop":
                this.handleSelectCrop(payload);
                break;

            case "select_section":
                let targetSecId = payload.section_id;
                if (!targetSecId && typeof payload.ordinal_index === "number" && window.farmSections && window.farmSections.length > payload.ordinal_index) {
                    targetSecId = window.farmSections[payload.ordinal_index].id;
                }
                if (targetSecId && window.selectSection) {
                    window.selectSection(targetSecId);
                    const secCard = document.querySelector(`.section-card[data-section-id="${targetSecId}"]`) || document.querySelector(`.section-card[data-id="${targetSecId}"]`);
                    if (secCard) {
                        secCard.scrollIntoView({ behavior: "smooth", block: "center" });
                        secCard.classList.add("voice-action-highlight");
                        setTimeout(() => secCard.classList.remove("voice-action-highlight"), 2500);
                    }
                }
                break;

            case "select_farm":
                const farmOverviewSec = document.getElementById("sectionFarmOverview");
                if (farmOverviewSec) {
                    farmOverviewSec.scrollIntoView({ behavior: "smooth", block: "start" });
                    farmOverviewSec.classList.add("voice-action-highlight");
                    setTimeout(() => farmOverviewSec.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "scroll_page":
                if (payload.direction === "top") {
                    window.scrollTo({ top: 0, behavior: "smooth" });
                } else if (payload.direction === "down") {
                    window.scrollBy({ top: 500, behavior: "smooth" });
                } else if (payload.direction === "up") {
                    window.scrollBy({ top: -500, behavior: "smooth" });
                }
                break;

            case "save_section":
                const saveSecBtn = document.getElementById("btnSaveSection") || document.querySelector("#sectionModal button[type='submit']") || document.querySelector("#formSectionManage button[type='submit']");
                if (saveSecBtn) {
                    saveSecBtn.click();
                } else {
                    const finishBtn = document.getElementById("btnCompleteOnboarding") || document.getElementById("btnOnboardSave");
                    if (finishBtn) finishBtn.click();
                }
                break;

            case "add_land_section":
                if (typeof openAddSectionModal === "function") {
                    openAddSectionModal();
                    const nameInput = document.getElementById("modalSectionName");
                    const areaInput = document.getElementById("modalSectionArea");
                    const cropSelect = document.getElementById("modalCropSelect");

                    if (nameInput && payload.name) nameInput.value = payload.name;
                    if (areaInput && payload.area_acres) areaInput.value = payload.area_acres;
                    if (cropSelect && payload.crop) cropSelect.value = payload.crop;
                }
                break;

            case "edit_land_section":
                if (payload.section_id && typeof openEditSectionModal === "function") {
                    openEditSectionModal(payload.section_id);
                    const areaInput = document.getElementById("modalSectionArea");
                    const cropSelect = document.getElementById("modalCropSelect");
                    if (areaInput && payload.area_acres) areaInput.value = payload.area_acres;
                    if (cropSelect && payload.crop) cropSelect.value = payload.crop;
                }
                break;

            case "remove_land_section":
                if (payload.section_id && window.currentFarm && typeof loadFarmSections === "function") {
                    await loadFarmSections(window.currentFarm.id);
                }
                break;

            case "calculate_irrigation":
            case "run_irrigation_prediction":
                if (payload.section_id && window.selectSection) {
                    window.selectSection(payload.section_id);
                }
                const plannerSec = document.getElementById("irrigation-planner") || document.getElementById("irrigationForm");
                if (plannerSec) plannerSec.scrollIntoView({ behavior: "smooth", block: "start" });
                if (window.triggerPrediction) {
                    window.triggerPrediction();
                } else {
                    const btn = document.getElementById("predictButton");
                    if (btn && !btn.disabled) btn.click();
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
                this.handleOnboardingField(payload);
                break;

            case "complete_onboarding":
                const finishBtn = document.getElementById("btnCompleteOnboarding") || document.getElementById("btnOnboardSave");
                if (finishBtn) finishBtn.click();
                break;

            default:
                console.log("Unhandled action:", action);
        }
    }

    handleSelectCrop(payload) {
        const stateSelect = document.getElementById("state_select");
        const cropSelect = document.getElementById("crop_type");
        if (!cropSelect) return;

        // Ensure state is selected so crop dropdown is populated
        if (stateSelect && !stateSelect.value && window.currentFarmer && window.currentFarmer.state) {
            stateSelect.value = window.currentFarmer.state;
            stateSelect.dispatchEvent(new Event("change"));
        }

        const applyCrop = () => {
            if (payload.crop) {
                const target = payload.crop.toLowerCase();
                const matched = Array.from(cropSelect.options).find(opt => 
                    opt.value.toLowerCase() === target || 
                    opt.text.toLowerCase().includes(target) ||
                    target.includes(opt.value.toLowerCase())
                );
                if (matched) {
                    cropSelect.value = matched.value;
                    cropSelect.dispatchEvent(new Event("change"));
                }
            } else if (payload.crop_index !== undefined || payload.crop_number !== undefined) {
                const idx = (payload.crop_index !== undefined) ? payload.crop_index : (payload.crop_number - 1);
                const valid = Array.from(cropSelect.options).filter(opt => opt.value && !opt.disabled);
                if (valid[idx]) {
                    cropSelect.value = valid[idx].value;
                    cropSelect.dispatchEvent(new Event("change"));
                }
            }

            const plannerEl = document.getElementById("irrigation-planner") || cropSelect;
            plannerEl.scrollIntoView({ behavior: "smooth", block: "center" });
            cropSelect.classList.add("voice-action-highlight");
            setTimeout(() => cropSelect.classList.remove("voice-action-highlight"), 2500);
        };

        if (cropSelect.disabled) {
            setTimeout(applyCrop, 200);
        } else {
            applyCrop();
        }
    }

    handleNavigationAction(payload) {
        const target = payload.target;
        switch (target) {
            case "dashboard":
                // Close any open modals
                document.querySelectorAll(".modal, .modal-backdrop, [id$='Modal']").forEach(m => {
                    if (m.style) m.style.display = "none";
                });
                if (window.location.pathname.includes("/dashboard") || window.location.pathname === "/") {
                    window.scrollTo({ top: 0, behavior: "smooth" });
                } else {
                    window.location.href = "/dashboard";
                }
                break;

            case "crop_details":
                const elCrop = document.getElementById("crop_type") || document.getElementById("cropGrowthStageFieldWrap") || document.getElementById("irrigation-planner");
                if (elCrop) {
                    elCrop.scrollIntoView({ behavior: "smooth", block: "center" });
                    elCrop.classList.add("voice-action-highlight");
                    setTimeout(() => elCrop.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "soil_details":
                const elSoil = document.getElementById("soil_moisture") || document.getElementById("soil_temperature") || document.getElementById("irrigation-planner");
                if (elSoil) {
                    elSoil.scrollIntoView({ behavior: "smooth", block: "center" });
                    elSoil.classList.add("voice-action-highlight");
                    setTimeout(() => elSoil.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "settings":
                const dropBtn = document.getElementById("farmerAccountBtn");
                const dropMenu = document.getElementById("farmerDropdownMenu");
                if (dropMenu) dropMenu.style.display = (dropMenu.style.display === "block" ? "none" : "block");
                if (dropBtn) {
                    dropBtn.scrollIntoView({ behavior: "smooth", block: "center" });
                    dropBtn.classList.add("voice-action-highlight");
                    setTimeout(() => dropBtn.classList.remove("voice-action-highlight"), 2500);
                }
                break;

            case "irrigation_schedule":
                const elSched = document.getElementById("smartSchedulerCard") || document.getElementById("noIrrigationCard") || document.getElementById("irrigation-planner");
                if (elSched) {
                    elSched.scrollIntoView({ behavior: "smooth", block: "center" });
                    elSched.classList.add("voice-action-highlight");
                    setTimeout(() => elSched.classList.remove("voice-action-highlight"), 2500);
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
                const chatWin = document.getElementById("agriChatWindow");
                if (chatWin) {
                    chatWin.classList.add("agri-open");
                    chatWin.removeAttribute("hidden");
                }
                break;

            case "go_back":
                const openModal = document.querySelector(".modal[style*='block'], .modal-backdrop[style*='block'], #sectionModal[style*='block'], #globalCalendarModal[style*='block'], #predictionHistoryModal[style*='block']");
                if (openModal) {
                    openModal.style.display = "none";
                    const closeBtn = openModal.querySelector(".btn-close, .modal-close");
                    if (closeBtn) closeBtn.click();
                } else {
                    window.history.back();
                }
                break;

            case "home":
                window.location.href = "/";
                break;

            case "logout":
                window.location.href = "/logout";
                break;
        }
    }

    handleOnboardingField(payload) {
        const field = payload.field;
        const val = payload.value;

        if (field === "state") {
            const stateSelect = document.getElementById("obState") || document.getElementById("state_select");
            if (stateSelect) {
                stateSelect.value = val;
                stateSelect.dispatchEvent(new Event("change"));
            }
        } else if (field === "district") {
            const distInput = document.getElementById("obDistrict");
            if (distInput) {
                distInput.value = val;
                distInput.dispatchEvent(new Event("input"));
            }
        } else if (field === "total_land") {
            const landInput = document.getElementById("obTotalLand") || document.getElementById("section_area_acres");
            if (landInput) {
                landInput.value = parseFloat(val).toFixed(2);
                landInput.dispatchEvent(new Event("input"));
                landInput.dispatchEvent(new Event("change"));
            }
        } else if (field === "farmer_name") {
            const nameInput = document.getElementById("obFarmerName") || document.getElementById("onboardFarmerName");
            if (nameInput) {
                nameInput.value = val;
                nameInput.dispatchEvent(new Event("input"));
            }
        } else if (field === "step") {
            if (val === "next") {
                const nextBtn = document.getElementById("btnOnboardNext");
                if (nextBtn) nextBtn.click();
            } else if (val === "prev") {
                const prevBtn = document.querySelector(".btn-prev");
                if (prevBtn) prevBtn.click();
            }
        }
    }

    showConfirmationBox(promptText) {
        const box = document.getElementById("vaConfirmBox");
        const promptEl = document.getElementById("vaConfirmPrompt");
        if (box && promptEl) {
            promptEl.textContent = promptText;
            box.style.display = "block";
            return;
        }

        let floatBox = document.getElementById("vaFloatingConfirm");
        if (!floatBox) {
            floatBox = document.createElement("div");
            floatBox.id = "vaFloatingConfirm";
            floatBox.className = "va-floating-confirm";
            floatBox.innerHTML = `
                <div class="va-floating-confirm-content">
                    <p id="vaFloatingConfirmPrompt" class="va-confirm-prompt" style="margin:0 0 8px 0; font-size:13px; font-weight:700; color:#92400e;"></p>
                    <div class="va-confirm-btn-row" style="display:flex; gap:8px;">
                        <button type="button" id="vaFloatingBtnYes" class="va-confirm-yes" style="background:#16a34a; color:#fff; border:none; padding:6px 14px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">✓ Confirm</button>
                        <button type="button" id="vaFloatingBtnNo" class="va-confirm-no" style="background:#dc2626; color:#fff; border:none; padding:6px 14px; border-radius:6px; font-size:12px; font-weight:700; cursor:pointer;">✕ Cancel</button>
                    </div>
                </div>
            `;
            document.body.appendChild(floatBox);

            floatBox.querySelector("#vaFloatingBtnYes").addEventListener("click", () => {
                this.executeCommand("confirm");
                this.hideConfirmationBox();
            });
            floatBox.querySelector("#vaFloatingBtnNo").addEventListener("click", () => {
                this.executeCommand("cancel");
                this.hideConfirmationBox();
            });
        }
        const promptF = floatBox.querySelector("#vaFloatingConfirmPrompt");
        if (promptF) promptF.textContent = promptText;
        floatBox.style.display = "block";
    }

    hideConfirmationBox() {
        const box = document.getElementById("vaConfirmBox");
        if (box) box.style.display = "none";
        const floatBox = document.getElementById("vaFloatingConfirm");
        if (floatBox) floatBox.style.display = "none";
    }

    showActionFeedback(msg) {
        const fb = document.getElementById("vaActionFeedback");
        if (fb) {
            fb.textContent = msg;
            fb.style.display = "block";
            setTimeout(() => {
                if (fb) fb.style.display = "none";
            }, 5000);
        }
    }

    bindVoiceDeckControls() {
        // Run button for editable transcript
        const runBtn = document.getElementById("vaExecuteBtn");
        if (runBtn) {
            runBtn.addEventListener("click", () => {
                const input = document.getElementById("vaTranscriptInput");
                if (input && input.value.trim()) {
                    this.executeCommand(input.value.trim());
                }
            });
        }

        const input = document.getElementById("vaTranscriptInput");
        if (input) {
            input.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    if (input.value.trim()) this.executeCommand(input.value.trim());
                }
            });
        }

        // Voice mic button
        const micBtn = document.getElementById("vaMicBtn");
        if (micBtn) {
            micBtn.addEventListener("click", () => this.startListening());
        }

        // Voice stop button
        const stopBtn = document.getElementById("vaStopBtn");
        if (stopBtn) {
            stopBtn.addEventListener("click", () => this.stopListening());
        }

        // Audio controls (Listen, Pause, Mute)
        const listenBtn = document.getElementById("vaListenBtn");
        if (listenBtn) {
            listenBtn.addEventListener("click", () => {
                if (window.AgriVoiceAudio) {
                    if (this.lastResponse && this.lastResponse.spoken_response) {
                        window.AgriVoiceAudio.play(this.lastResponse.spoken_response);
                    } else {
                        window.AgriVoiceAudio.play();
                    }
                }
            });
        }

        const pauseBtn = document.getElementById("vaPauseBtn");
        if (pauseBtn) {
            pauseBtn.addEventListener("click", () => {
                if (window.AgriVoiceAudio) window.AgriVoiceAudio.pause();
            });
        }

        const muteBtn = document.getElementById("vaMuteBtn");
        if (muteBtn) {
            muteBtn.addEventListener("click", () => {
                if (window.AgriVoiceAudio) window.AgriVoiceAudio.mute();
            });
        }

        // Confirmation Yes / No buttons
        const btnYes = document.getElementById("vaBtnConfirmYes");
        if (btnYes) {
            btnYes.addEventListener("click", () => {
                this.executeCommand("confirm");
            });
        }

        const btnNo = document.getElementById("vaBtnConfirmNo");
        if (btnNo) {
            btnNo.addEventListener("click", () => {
                this.executeCommand("cancel");
            });
        }
    }
}

/**
 * AgriVoiceAudioPlayer: Audio Manager with Listen, Pause, and Mute Controls.
 * Handles native SpeechSynthesis when supported and falls back automatically
 * to backend streaming TTS audio (/api/voice/tts) for Telugu, Hindi, Punjabi, etc.
 */
class AgriVoiceAudioPlayer {
    constructor() {
        this.audioEl = new Audio();
        this.synth = window.speechSynthesis;
        this.state = 'idle'; // 'idle', 'playing', 'paused', 'muted'
        this.currentMode = null; // 'synth' or 'audio'
        this.activeText = "";
        this.activeLang = "en";
        this.onEndCallback = null;

        this.audioEl.addEventListener('ended', () => {
            this.handlePlaybackEnded();
        });
        this.audioEl.addEventListener('error', (e) => {
            console.warn("AgriVoiceAudio audioEl error:", e);
            this.handlePlaybackEnded();
        });
    }

    handlePlaybackEnded() {
        this.state = 'idle';
        this.currentMode = null;
        this.updateButtons();
        if (this.onEndCallback) {
            const cb = this.onEndCallback;
            this.onEndCallback = null;
            try { cb(); } catch (err) {}
        }
    }

    hasNativeVoice(langCode) {
        if (!('speechSynthesis' in window)) return false;
        if (['te', 'kn', 'ml', 'or', 'as', 'ur', 'sa'].includes(langCode)) return false;
        const voices = window.speechSynthesis.getVoices();
        if (!voices || voices.length === 0) return false;
        const meta = typeof SUPPORTED_LANGUAGES !== "undefined"
            ? SUPPORTED_LANGUAGES.find(l => l.code === langCode)
            : null;
        const targetTag = (meta ? meta.bcp47 : langCode).toLowerCase();
        const shortTag = targetTag.split('-')[0];
        return voices.some(v => {
            const vl = (v.lang || "").toLowerCase();
            return vl === targetTag || vl.startsWith(shortTag);
        });
    }

    play(text = null, langCode = null, onEnd = null) {
        const lang = langCode || (window.AgriI18n ? window.AgriI18n.currentLang : 'en');
        const guideText = text || (window.AgriI18n ? window.AgriI18n.getPageInstructions() : "Welcome to Smart Irrigation Planner.");
        this.activeText = guideText;
        this.activeLang = lang;
        if (onEnd) this.onEndCallback = onEnd;

        if (this.state === 'paused') {
            return this.resume();
        }

        this.stopCurrent();

        if (this.hasNativeVoice(lang)) {
            try {
                this.currentMode = 'synth';
                const utterance = new SpeechSynthesisUtterance(guideText);
                const meta = typeof SUPPORTED_LANGUAGES !== "undefined"
                    ? SUPPORTED_LANGUAGES.find(l => l.code === lang)
                    : null;
                utterance.lang = meta ? meta.bcp47 : `${lang}-IN`;
                utterance.rate = 0.95;
                utterance.pitch = 1.0;

                const voices = window.speechSynthesis.getVoices();
                const matched = voices.find(v => {
                    const vl = (v.lang || "").toLowerCase();
                    return vl === utterance.lang.toLowerCase() || vl.startsWith(lang.toLowerCase());
                });
                if (matched) utterance.voice = matched;

                utterance.onend = () => this.handlePlaybackEnded();
                utterance.onerror = (e) => {
                    console.warn("SpeechSynthesis error, streaming backend TTS audio:", e);
                    this.playBackendAudio(guideText, lang);
                };

                this.state = 'playing';
                this.updateButtons();
                window.speechSynthesis.speak(utterance);
                return;
            } catch (err) {
                console.warn("Native speech synthesis attempt failed:", err);
            }
        }

        this.playBackendAudio(guideText, lang);
    }

    playBackendAudio(text, lang) {
        this.currentMode = 'audio';
        this.state = 'playing';
        this.updateButtons();
        const ttsUrl = `/api/voice/tts?lang=${encodeURIComponent(lang)}&text=${encodeURIComponent(text)}`;
        this.audioEl.src = ttsUrl;
        this.audioEl.play().catch(err => {
            console.warn("Backend TTS play error:", err);
            this.handlePlaybackEnded();
        });
    }

    pause() {
        if (this.state !== 'playing') return;
        if (this.currentMode === 'synth' && 'speechSynthesis' in window) {
            window.speechSynthesis.pause();
        } else if (this.currentMode === 'audio' && this.audioEl) {
            this.audioEl.pause();
        }
        this.state = 'paused';
        this.updateButtons();
    }

    resume() {
        if (this.state !== 'paused') return;
        if (this.currentMode === 'synth' && 'speechSynthesis' in window) {
            window.speechSynthesis.resume();
        } else if (this.currentMode === 'audio' && this.audioEl) {
            this.audioEl.play().catch(err => console.warn("Audio resume error:", err));
        }
        this.state = 'playing';
        this.updateButtons();
    }

    stop() {
        this.stopCurrent();
        this.state = 'idle';
        this.updateButtons();
    }

    mute() {
        this.stop();
    }

    stopCurrent() {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        if (this.audioEl) {
            this.audioEl.pause();
            this.audioEl.currentTime = 0;
            this.audioEl.removeAttribute('src');
        }
    }

    updateButtons() {
        const listenBtns = document.querySelectorAll("#btnAudioListen, #vaListenBtn, .btn-audio-listen");
        const pauseBtns = document.querySelectorAll("#btnAudioPause, #vaPauseBtn, .btn-audio-pause");
        const muteBtns = document.querySelectorAll("#btnAudioMute, #vaMuteBtn, .btn-audio-mute");

        const isPlaying = (this.state === 'playing');
        const isPaused = (this.state === 'paused');
        const isActive = isPlaying || isPaused;

        listenBtns.forEach(btn => {
            btn.classList.toggle("active-audio", isActive);
            btn.setAttribute("aria-pressed", isActive ? "true" : "false");
            btn.title = isActive ? "Speaker OFF - Click to stop speech" : "Speaker ON - Click to read page content";
            const iconSpan = btn.querySelector(".speaker-icon") || btn.querySelector("span:not(.btn-ctrl-text)");
            const textSpan = btn.querySelector(".btn-ctrl-text");
            if (iconSpan) iconSpan.textContent = isActive ? "🔊" : "🔈";
            if (textSpan) textSpan.remove();
        });

        pauseBtns.forEach(btn => {
            btn.disabled = !isActive;
            btn.classList.toggle("paused-audio", isPaused);
            btn.setAttribute("aria-pressed", isPaused ? "true" : "false");
            btn.title = isPaused ? "Resume Speech" : "Pause Speech";
            const iconSpan = btn.querySelector(".pause-icon") || btn.querySelector("span:not(.btn-ctrl-text)");
            const textSpan = btn.querySelector(".btn-ctrl-text");
            if (iconSpan) iconSpan.textContent = isPaused ? "▶️" : "⏸️";
            if (textSpan) textSpan.remove();
        });

        muteBtns.forEach(btn => {
            btn.disabled = !isActive;
            btn.classList.toggle("muted-audio", this.state === 'muted');
        });
    }

    bindControls() {
        document.querySelectorAll("#btnAudioListen, .btn-audio-listen").forEach(btn => {
            if (btn._boundAudio) return;
            btn._boundAudio = true;
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                if (this.state === 'playing' || this.state === 'paused') {
                    // Click 2: Turn Speaker OFF and stop speech immediately
                    this.stop();
                } else {
                    // Click 1: Turn Speaker ON and start reading current page
                    this.play();
                }
            });
        });

        document.querySelectorAll("#btnAudioPause, .btn-audio-pause").forEach(btn => {
            if (btn._boundAudio) return;
            btn._boundAudio = true;
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                if (this.state === 'paused') {
                    // Click 2: Resume from paused position without restarting
                    this.resume();
                } else if (this.state === 'playing') {
                    // Click 1: Pause current speech
                    this.pause();
                }
            });
        });

        document.querySelectorAll("#btnAudioMute, .btn-audio-mute").forEach(btn => {
            if (btn._boundAudio) return;
            btn._boundAudio = true;
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                this.stop();
            });
        });
    }
}

// Global audio player and voice controller instances
const AgriVoiceController = AgriVoiceWebsiteController;
window.AgriVoiceAudio = new AgriVoiceAudioPlayer();
window.AgriVoice = new AgriVoiceWebsiteController();

document.addEventListener("DOMContentLoaded", () => {
    window.AgriVoiceAudio.bindControls();
    window.AgriVoice.bindVoiceDeckControls();
    window.AgriVoice.initSpeakerToggle();
    window.AgriVoice.initNavMic();

    // Trigger website voice commands on dedicated navigation and section buttons (strictly never chatbot elements)
    document.querySelectorAll(".btn-voice-mic, #btnVoiceMicHero, #btnVoiceMicOnboard, #btnVoiceAssistantTrigger").forEach(btn => {
        btn.addEventListener("click", () => {
            if (window.AgriVoice.isListening) {
                window.AgriVoice.stopListening(true);
            } else {
                window.AgriVoice.startListening();
            }
        });
    });

    // Sync language changes
    window.addEventListener("farmerLanguageChanged", (e) => {
        const badge = document.getElementById("vaLangBadge");
        if (badge) {
            const meta = typeof SUPPORTED_LANGUAGES !== "undefined"
                ? SUPPORTED_LANGUAGES.find(l => l.code === e.detail.language)
                : null;
            badge.textContent = `🌐 ${meta ? meta.name : e.detail.language}`;
        }
        if (window.AgriVoiceAudio && window.AgriVoiceAudio.state === 'playing') {
            window.AgriVoiceAudio.play(null, e.detail.language);
        }
    });
});
