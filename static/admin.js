/**
 * Super Admin Dashboard Client-Side Engine.
 * Handles:
 * - Authentication & Session Validation
 * - Executive Overview & KPIs
 * - Farmer Account Management (search, filter, inspect, edit, suspend/activate, reset password)
 * - Administrative Impersonation Mode
 * - Global Farm Management
 * - Global Irrigation Schedule Monitoring
 * - Live Weather Overview Across Farms
 * - AI & System Health Diagnostics
 * - Security Audit Trail Inspection
 */

(function () {
    "use strict";

    // Application State
    let currentAdmin = null;
    let currentTab = "overview";
    let allFarmers = [];
    let allFarms = [];
    let allSchedules = [];
    let allWeather = [];
    let allAuditLogs = [];

    // DOM Elements Cache
    const el = {
        topAdminUsername: document.getElementById("topAdminUsername"),
        btnAdminLogout: document.getElementById("btnAdminLogout"),
        navItems: document.querySelectorAll(".admin-nav-item"),
        tabViews: document.querySelectorAll(".admin-tab-view"),

        // Badges
        navFarmerCount: document.getElementById("navFarmerCount"),
        navFarmCount: document.getElementById("navFarmCount"),
        navScheduleCount: document.getElementById("navScheduleCount"),

        // Overview KPIs
        btnRefreshKPIs: document.getElementById("btnRefreshKPIs"),
        kpiTotalFarmers: document.getElementById("kpiTotalFarmers"),
        kpiActiveFarmers: document.getElementById("kpiActiveFarmers"),
        kpiSuspendedFarmers: document.getElementById("kpiSuspendedFarmers"),
        kpiTotalFarms: document.getElementById("kpiTotalFarms"),
        kpiTotalLand: document.getElementById("kpiTotalLand"),
        kpiTotalSections: document.getElementById("kpiTotalSections"),
        kpiCultivatedSections: document.getElementById("kpiCultivatedSections"),
        kpiEmptySections: document.getElementById("kpiEmptySections"),
        kpiActiveCrops: document.getElementById("kpiActiveCrops"),
        kpiTotalWater: document.getElementById("kpiTotalWater"),
        kpiTotalSchedules: document.getElementById("kpiTotalSchedules"),
        kpiUpcomingSessions: document.getElementById("kpiUpcomingSessions"),
        kpiCompletedSessions: document.getElementById("kpiCompletedSessions"),
        kpiSkippedSessions: document.getElementById("kpiSkippedSessions"),
        overviewAuditEventsList: document.getElementById("overviewAuditEventsList"),
        overviewGeminiStatus: document.getElementById("overviewGeminiStatus"),
        overviewGeminiBadge: document.getElementById("overviewGeminiBadge"),

        // Farmers Tab
        btnRefreshFarmers: document.getElementById("btnRefreshFarmers"),
        farmerSearchInput: document.getElementById("farmerSearchInput"),
        farmerStateFilter: document.getElementById("farmerStateFilter"),
        farmerStatusFilter: document.getElementById("farmerStatusFilter"),
        farmersTableBody: document.getElementById("farmersTableBody"),
        farmersEmptyNotice: document.getElementById("farmersEmptyNotice"),

        // Farms Tab
        btnRefreshFarms: document.getElementById("btnRefreshFarms"),
        farmSearchInput: document.getElementById("farmSearchInput"),
        farmsTableBody: document.getElementById("farmsTableBody"),

        // Schedules Tab
        btnRefreshSchedules: document.getElementById("btnRefreshSchedules"),
        schedStatusFilter: document.getElementById("schedStatusFilter"),
        schedCropFilter: document.getElementById("schedCropFilter"),
        schedulesTableBody: document.getElementById("schedulesTableBody"),

        // Weather Tab
        btnRefreshWeatherStations: document.getElementById("btnRefreshWeatherStations"),
        weatherStationsTableBody: document.getElementById("weatherStationsTableBody"),

        // AI Diagnostics Tab
        btnRefreshAIStatus: document.getElementById("btnRefreshAIStatus"),
        geminiDiagBody: document.getElementById("geminiDiagBody"),
        modelDiagBody: document.getElementById("modelDiagBody"),
        weatherDiagBody: document.getElementById("weatherDiagBody"),

        // Audit Logs Tab
        btnRefreshAuditLogs: document.getElementById("btnRefreshAuditLogs"),
        auditActionFilter: document.getElementById("auditActionFilter"),
        auditLogsTableBody: document.getElementById("auditLogsTableBody"),

        // Inspect Modal
        farmerInspectModal: document.getElementById("farmerInspectModal"),
        inspectModalTitle: document.getElementById("inspectModalTitle"),
        inspectModalFarmerId: document.getElementById("inspectModalFarmerId"),
        inspectModalBody: document.getElementById("inspectModalBody"),
        inspectModalCloseBtn: document.getElementById("inspectModalCloseBtn"),
        inspectModalDoneBtn: document.getElementById("inspectModalDoneBtn"),
        inspectModalBackdrop: document.getElementById("inspectModalBackdrop"),

        // Edit Modal
        editFarmerModal: document.getElementById("editFarmerModal"),
        editFarmerForm: document.getElementById("editFarmerForm"),
        editFarmerId: document.getElementById("editFarmerId"),
        editFarmerName: document.getElementById("editFarmerName"),
        editFarmerPhone: document.getElementById("editFarmerPhone"),
        editFarmerEmail: document.getElementById("editFarmerEmail"),
        editFarmerState: document.getElementById("editFarmerState"),
        editFarmerDistrict: document.getElementById("editFarmerDistrict"),
        editFarmerVillage: document.getElementById("editFarmerVillage"),
        editFarmerFeedback: document.getElementById("editFarmerFeedback"),
        editFarmerCloseBtn: document.getElementById("editFarmerModalCloseBtn"),
        editFarmerCancelBtn: document.getElementById("editFarmerCancelBtn"),
        editFarmerBackdrop: document.getElementById("editFarmerModalBackdrop"),

        // Reset Password Modal
        resetPasswordModal: document.getElementById("resetPasswordModal"),
        resetPasswordForm: document.getElementById("resetPasswordForm"),
        resetFarmerId: document.getElementById("resetFarmerId"),
        resetFarmerNameLabel: document.getElementById("resetFarmerNameLabel"),
        adminNewFarmerPassword: document.getElementById("adminNewFarmerPassword"),
        resetPasswordFeedback: document.getElementById("resetPasswordFeedback"),
        resetPasswordCloseBtn: document.getElementById("resetPasswordCloseBtn"),
        resetPasswordCancelBtn: document.getElementById("resetPasswordCancelBtn"),
        resetPasswordBackdrop: document.getElementById("resetPasswordBackdrop"),

        // Impersonation Modal
        impersonationModal: document.getElementById("impersonationModal"),
        impersonationForm: document.getElementById("impersonationForm"),
        impersonateFarmerId: document.getElementById("impersonateFarmerId"),
        impersonateTargetName: document.getElementById("impersonateTargetName"),
        impersonationReason: document.getElementById("impersonationReason"),
        impersonationFeedback: document.getElementById("impersonationFeedback"),
        impersonationCloseBtn: document.getElementById("impersonationCloseBtn"),
        impersonationCancelBtn: document.getElementById("impersonationCancelBtn"),
        impersonationBackdrop: document.getElementById("impersonationBackdrop"),
    };

    // Helper: Debounce
    function debounce(fn, delay = 300) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        if (!str && str !== 0) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Helper: Format Date/Time
    function formatDateTime(isoString) {
        if (!isoString) return "--";
        try {
            const d = new Date(isoString);
            return d.toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            });
        } catch (e) {
            return isoString;
        }
    }

    // Tab Navigation
    function switchTab(tabName) {
        if (tabName === "farmers") tabName = "overview";
        currentTab = tabName;
        el.navItems.forEach(item => {
            const itemTab = item.getAttribute("data-tab");
            if (itemTab === tabName || (tabName === "overview" && itemTab === "farmers")) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });

        el.tabViews.forEach(view => {
            if (view.id === `view-${tabName}`) {
                view.classList.add("active");
            } else {
                view.classList.remove("active");
            }
        });

        // Trigger on-demand loads
        if (tabName === "overview") {
            loadKPIs();
            loadFarmers();
        }
        else if (tabName === "farms") loadFarms();
        else if (tabName === "schedules") loadSchedules();
        else if (tabName === "weather") loadWeather();
        else if (tabName === "ai-system") loadAIStatus();
        else if (tabName === "audit-logs") loadAuditLogs();
    }

    // ========================================================
    // Authentication & Initialization
    // ========================================================
    async function checkAdminAuth() {
        try {
            const res = await fetch("/api/admin/me");
            if (!res.ok) {
                window.location.href = "/admin/login";
                return;
            }
            const data = await res.json();
            if (!data.authenticated || !data.admin) {
                window.location.href = "/admin/login";
                return;
            }
            currentAdmin = data.admin;
            if (el.topAdminUsername) {
                el.topAdminUsername.textContent = currentAdmin.username || "Super Admin";
            }
            // Load dashboard
            loadKPIs();
            loadFarmers();
            loadAIStatus();
        } catch (err) {
            console.error("Auth check failed:", err);
            window.location.href = "/admin/login";
        }
    }

    // Logout
    if (el.btnAdminLogout) {
        el.btnAdminLogout.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to end your Super Admin session?")) return;
            try {
                await fetch("/api/admin/auth/logout", { method: "POST" });
            } finally {
                window.location.href = "/admin/login";
            }
        });
    }

    // Navigation Click Listeners
    el.navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tab = item.getAttribute("data-tab");
            if (tab) switchTab(tab);
        });
    });

    document.querySelectorAll("[data-goto]").forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-goto");
            if (target) switchTab(target);
        });
    });

    // ========================================================
    // Executive Overview & KPIs
    // ========================================================
    async function loadKPIs() {
        try {
            const res = await fetch("/api/admin/kpis");
            if (!res.ok) return;
            const data = await res.json();

            if (el.kpiTotalFarmers) el.kpiTotalFarmers.textContent = data.total_farmers || 0;
            if (el.kpiActiveFarmers) el.kpiActiveFarmers.textContent = `${data.active_farmers || 0} Active`;
            if (el.kpiSuspendedFarmers) el.kpiSuspendedFarmers.textContent = `${data.suspended_farmers || 0} Suspended`;
            if (el.kpiTotalFarms) el.kpiTotalFarms.textContent = data.total_farms || 0;
            if (el.kpiTotalLand) el.kpiTotalLand.textContent = `${data.total_land_acres || 0} Acres`;
            if (el.kpiTotalSections) el.kpiTotalSections.textContent = data.total_sections || 0;
            if (el.kpiCultivatedSections) el.kpiCultivatedSections.textContent = `${data.cultivated_sections || 0} Cultivated`;
            if (el.kpiEmptySections) el.kpiEmptySections.textContent = `${data.empty_sections || 0} Empty`;
            if (el.kpiActiveCrops) el.kpiActiveCrops.textContent = data.active_crops_count || 0;
            if (el.kpiTotalWater) el.kpiTotalWater.textContent = `${(data.total_water_liters || 0).toLocaleString()} L`;
            if (el.kpiTotalSchedules) el.kpiTotalSchedules.textContent = data.total_schedules || 0;
            if (el.kpiUpcomingSessions) el.kpiUpcomingSessions.textContent = `${data.upcoming_sessions || 0} Upcoming`;
            if (el.kpiCompletedSessions) el.kpiCompletedSessions.textContent = `${data.completed_sessions || 0} Done`;
            if (el.kpiSkippedSessions) el.kpiSkippedSessions.textContent = `${data.skipped_sessions || 0} Skipped`;

            // Update badge counts in sidebar
            if (el.navFarmerCount) el.navFarmerCount.textContent = data.total_farmers || 0;
            if (el.navFarmCount) el.navFarmCount.textContent = data.total_farms || 0;
            if (el.navScheduleCount) el.navScheduleCount.textContent = data.total_schedules || 0;

            // Load audit trail preview for overview
            loadOverviewAuditEvents();
        } catch (err) {
            console.error("Failed to load KPIs:", err);
        }
    }

    async function loadOverviewAuditEvents() {
        if (!el.overviewAuditEventsList) return;
        try {
            const res = await fetch("/api/admin/audit-logs?limit=5");
            if (!res.ok) return;
            const logs = await res.json();
            if (!logs || logs.length === 0) {
                el.overviewAuditEventsList.innerHTML = `<div class="event-empty">No recent administrative events recorded.</div>`;
                return;
            }
            el.overviewAuditEventsList.innerHTML = logs.map(l => `
                <div class="event-row">
                    <span class="event-time">${escapeHtml(formatDateTime(l.created_at))}</span>
                    <span class="action-tag tag-${escapeHtml(l.action)}">${escapeHtml(l.action)}</span>
                    <span class="event-desc">${escapeHtml(l.details || l.target_type)}</span>
                </div>
            `).join("");
        } catch (e) {
            console.error("Overview audit logs preview error:", e);
        }
    }

    if (el.btnRefreshKPIs) el.btnRefreshKPIs.addEventListener("click", loadKPIs);

    // ========================================================
    // Farmer Account Management
    // ========================================================
    async function loadFarmers() {
        try {
            const sq = el.farmerSearchInput ? el.farmerSearchInput.value.trim() : "";
            const st = el.farmerStateFilter ? el.farmerStateFilter.value : "all";
            const stat = el.farmerStatusFilter ? el.farmerStatusFilter.value : "all";

            const params = new URLSearchParams();
            if (sq) params.set("search", sq);
            if (st && st !== "all") params.set("state", st);
            if (stat && stat !== "all") params.set("status", stat);

            const res = await fetch(`/api/admin/farmers?${params.toString()}`);
            if (!res.ok) return;
            allFarmers = await res.json();
            renderFarmersTable(allFarmers);
            populateStateFilter(allFarmers);
        } catch (err) {
            console.error("Failed to load farmers:", err);
        }
    }

    function populateStateFilter(farmers) {
        if (!el.farmerStateFilter || el.farmerStateFilter.options.length > 1) return;
        const states = Array.from(new Set(farmers.map(f => f.state).filter(Boolean))).sort();
        states.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s;
            opt.textContent = s;
            el.farmerStateFilter.appendChild(opt);
        });
    }

    function renderFarmersTable(farmers) {
        if (!el.farmersTableBody) return;
        el.farmersTableBody.innerHTML = "";

        if (!farmers || farmers.length === 0) {
            if (el.farmersEmptyNotice) {
                el.farmersEmptyNotice.innerHTML = `
                    <div class="empty-state-wrap" style="padding: 32px 16px; text-align: center;">
                        <span style="font-size: 32px; display: block; margin-bottom: 8px;">👨‍🌾</span>
                        <h3 style="margin: 0 0 6px 0; font-size: 16px; color: #1e293b;">No registered farmers yet.</h3>
                        <p style="margin: 0; font-size: 13px; color: #64748b;">Farmers who create accounts via the Create Account / Register page will be displayed here automatically.</p>
                    </div>
                `;
                el.farmersEmptyNotice.style.display = "block";
            }
            return;
        }
        if (el.farmersEmptyNotice) el.farmersEmptyNotice.style.display = "none";

        farmers.forEach(f => {
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            const isSuspended = (f.status || "Active").toLowerCase() === "suspended";
            const statusBadge = isSuspended
                ? `<span class="badge badge-suspended">Suspended</span>`
                : `<span class="badge badge-active">Active</span>`;

            tr.innerHTML = `
                <td><code>${escapeHtml(f.id)}</code></td>
                <td>
                    <div class="farmer-cell">
                        <span class="farmer-avatar-sm">👨‍🌾</span>
                        <div>
                            <strong>${escapeHtml(f.name || "--")}</strong>
                        </div>
                    </div>
                </td>
                <td><code>${escapeHtml(f.username || "--")}</code></td>
                <td>${escapeHtml(f.email || "--")}</td>
                <td>${escapeHtml(f.phone || "--")}</td>
                <td>${escapeHtml(formatDateTime(f.created_at))}</td>
                <td>${statusBadge}</td>
                <td>${escapeHtml(formatDateTime(f.last_login_at))}</td>
                <td class="text-right">
                    <div class="action-btn-group">
                        <button type="button" class="btn-table-action btn-inspect" data-id="${f.id}" title="View Details">
                            👁️ Details
                        </button>
                        <button type="button" class="btn-table-action btn-edit" data-id="${f.id}" title="Edit Farmer Profile">
                            ✏️ Edit
                        </button>
                        <button type="button" class="btn-table-action btn-delete" data-id="${f.id}" data-name="${escapeHtml(f.name)}" title="Delete Farmer Account">
                            🗑️ Delete
                        </button>
                        <button type="button" class="btn-table-action ${isSuspended ? 'btn-activate' : 'btn-suspend'}" data-id="${f.id}" data-status="${f.status || 'Active'}" title="${isSuspended ? 'Reactivate Account' : 'Suspend Account'}">
                            ${isSuspended ? '✅' : '🚫'}
                        </button>
                        <button type="button" class="btn-table-action btn-reset-pwd" data-id="${f.id}" data-name="${escapeHtml(f.name)}" title="Reset Password">
                            🔑
                        </button>
                    </div>
                </td>
            `;

            // Clicking row (except on action buttons) opens details
            tr.addEventListener("click", (e) => {
                if (e.target.closest("button") || e.target.closest("a")) return;
                openInspectModal(f.id);
            });

            // Action button listeners with stopPropagation
            const btnInspect = tr.querySelector(".btn-inspect");
            if (btnInspect) {
                btnInspect.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openInspectModal(f.id);
                });
            }
            const btnEdit = tr.querySelector(".btn-edit");
            if (btnEdit) {
                btnEdit.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openEditModal(f);
                });
            }
            const btnDelete = tr.querySelector(".btn-delete");
            if (btnDelete) {
                btnDelete.addEventListener("click", (e) => {
                    e.stopPropagation();
                    deleteFarmer(f.id, f.name, f.username);
                });
            }
            const btnToggle = tr.querySelector(isSuspended ? ".btn-activate" : ".btn-suspend");
            if (btnToggle) {
                btnToggle.addEventListener("click", (e) => {
                    e.stopPropagation();
                    toggleFarmerStatus(f.id, f.status || "Active", f.name);
                });
            }
            const btnReset = tr.querySelector(".btn-reset-pwd");
            if (btnReset) {
                btnReset.addEventListener("click", (e) => {
                    e.stopPropagation();
                    openResetPasswordModal(f.id, f.name);
                });
            }

            el.farmersTableBody.appendChild(tr);
        });
    }

    async function deleteFarmer(farmerId, farmerName, farmerUsername) {
        const confirmMsg = `Are you sure you want to permanently delete farmer '${farmerName || farmerId}' (@${farmerUsername || ''})?\n\nThis will remove all their farms, land sections, and irrigation schedules permanently. This action cannot be undone.`;
        if (!confirm(confirmMsg)) return;

        try {
            const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" }
            });
            const data = await res.json();
            if (res.ok && data.success) {
                loadKPIs();
                loadFarmers();
            } else {
                alert(`Failed to delete farmer: ${data.error || 'Server error'}`);
            }
        } catch (err) {
            console.error("Delete farmer error:", err);
            alert("Error deleting farmer account.");
        }
    }

    if (el.farmerSearchInput) el.farmerSearchInput.addEventListener("input", debounce(loadFarmers, 300));
    if (el.farmerStateFilter) el.farmerStateFilter.addEventListener("change", loadFarmers);
    if (el.farmerStatusFilter) el.farmerStatusFilter.addEventListener("change", loadFarmers);
    if (el.btnRefreshFarmers) el.btnRefreshFarmers.addEventListener("click", loadFarmers);

    // ========================================================
    // Modal 1: Farmer Account Inspection
    // ========================================================
    async function openInspectModal(farmerId) {
        if (!el.farmerInspectModal || !el.inspectModalBody) return;
        el.inspectModalFarmerId.textContent = `Farmer ID: ${farmerId}`;
        el.inspectModalBody.innerHTML = `<div class="p-4 text-center">Loading exhaustive diagnostic records for farmer...</div>`;
        el.farmerInspectModal.style.display = "flex";

        try {
            const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}`);
            if (!res.ok) {
                el.inspectModalBody.innerHTML = `<div class="alert-box-warning">Unable to fetch farmer details.</div>`;
                return;
            }
            const data = await res.json();
            const f = data.farmer;
            const farms = data.farms || [];
            const sections = data.sections || [];
            const schedules = data.schedules || [];
            const auditTrail = data.audit_trail || [];

            el.inspectModalTitle.textContent = `${f.name} · Diagnostic Overview`;

            let sectionsRows = sections.map(s => `
                <tr>
                    <td><strong>${escapeHtml(s.name)}</strong></td>
                    <td>${s.area_acres} Ac</td>
                    <td>${s.is_empty ? '<span class="badge badge-empty">Empty Land</span>' : `<strong>${escapeHtml(s.crop || "--")}</strong> (${escapeHtml(s.crop_variety || "Standard")})`}</td>
                    <td>${s.sowing_date || "--"}</td>
                    <td>${s.soil_type || "--"}</td>
                    <td><strong>${s.soil_moisture !== null ? s.soil_moisture + '%' : '--'}</strong></td>
                </tr>
            `).join("");

            let schedulesRows = schedules.slice(0, 10).map(sc => `
                <tr>
                    <td>${escapeHtml(sc.irrigation_date)}</td>
                    <td>${escapeHtml(sc.recommended_time || "06:00 AM")}</td>
                    <td>${escapeHtml(sc.crop || "--")}</td>
                    <td><strong>${sc.water_quantity_liters} L</strong></td>
                    <td><span class="status-pill pill-${(sc.status || '').toLowerCase()}">${escapeHtml(sc.status)}</span></td>
                    <td style="font-size: 11px;">${escapeHtml(sc.ai_rationale || "--")}</td>
                </tr>
            `).join("");

            let auditRows = auditTrail.map(a => `
                <div class="event-row">
                    <span class="event-time">${escapeHtml(formatDateTime(a.created_at))}</span>
                    <strong class="action-tag">${escapeHtml(a.action)}</strong>
                    <span class="event-desc">${escapeHtml(a.details)}</span>
                </div>
            `).join("");

            el.inspectModalBody.innerHTML = `
                <div class="inspect-grid">
                    <div class="inspect-card">
                        <h4>📋 Registered Account Information</h4>
                        <table class="inspect-table">
                            <tr><th>Farmer ID</th><td><code>${escapeHtml(f.id)}</code></td></tr>
                            <tr><th>Farmer Name</th><td><strong>${escapeHtml(f.name || "--")}</strong></td></tr>
                            <tr><th>Username</th><td><code>${escapeHtml(f.username || "--")}</code></td></tr>
                            <tr><th>Email</th><td>${escapeHtml(f.email || "--")}</td></tr>
                            <tr><th>Mobile Number</th><td>${escapeHtml(f.phone || "--")}</td></tr>
                            <tr><th>Registration Date</th><td>${escapeHtml(formatDateTime(f.created_at))}</td></tr>
                            <tr><th>Account Status</th><td><strong>${escapeHtml(f.status || "Active")}</strong> ${f.suspend_reason ? `(${escapeHtml(f.suspend_reason)})` : ""}</td></tr>
                            <tr><th>Last Login</th><td>${escapeHtml(formatDateTime(f.last_login_at))}</td></tr>
                        </table>
                    </div>

                    <div class="inspect-card">
                        <h4>🏡 Farmer Profile & Agricultural Holdings</h4>
                        <table class="inspect-table">
                            <tr><th>Location</th><td>${escapeHtml(f.village || "")}${f.district ? `, ${escapeHtml(f.district)}` : ""}, ${escapeHtml(f.state || "--")}</td></tr>
                            <tr><th>Total Farms</th><td>${farms.length}</td></tr>
                            <tr><th>Primary Farm</th><td>${escapeHtml(farms[0]?.name || "Primary Farm")}</td></tr>
                            <tr><th>Total Land Area</th><td><strong>${farms[0]?.total_area_acres || 0} ${farms[0]?.unit || "Acres"}</strong></td></tr>
                            <tr><th>GPS Coordinates</th><td><code>${farms[0]?.latitude || 0}, ${farms[0]?.longitude || 0}</code></td></tr>
                            <tr><th>Land Sections</th><td>${sections.length} configured (${sections.filter(s => !s.is_empty).length} cultivated, ${sections.filter(s => s.is_empty).length} empty)</td></tr>
                        </table>
                    </div>
                </div>

                <div class="inspect-section-block">
                    <h4>🌾 Section Breakdown</h4>
                    <table class="admin-table admin-table-compact">
                        <thead>
                            <tr>
                                <th>Section Name</th>
                                <th>Area</th>
                                <th>Crop Status</th>
                                <th>Sowing Date</th>
                                <th>Soil Type</th>
                                <th>Soil Moisture</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sectionsRows || '<tr><td colspan="6" class="text-center">No sections configured.</td></tr>'}
                        </tbody>
                    </table>
                </div>

                <div class="inspect-section-block">
                    <h4>💧 Irrigation Schedules (Recent 10)</h4>
                    <table class="admin-table admin-table-compact">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Crop</th>
                                <th>Water</th>
                                <th>Status</th>
                                <th>AI Rationale</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${schedulesRows || '<tr><td colspan="6" class="text-center">No irrigation schedules recorded.</td></tr>'}
                        </tbody>
                    </table>
                </div>

                <div class="inspect-section-block">
                    <h4>📜 Security & Administrative Audit Trail</h4>
                    <div class="compact-event-list">
                        ${auditRows || '<div class="event-empty">No admin actions recorded for this farmer.</div>'}
                    </div>
                </div>
            `;
        } catch (err) {
            console.error("Inspect error:", err);
            el.inspectModalBody.innerHTML = `<div class="alert-box-warning">Error loading farmer details.</div>`;
        }
    }

    function closeInspectModal() {
        if (el.farmerInspectModal) el.farmerInspectModal.style.display = "none";
    }
    if (el.inspectModalCloseBtn) el.inspectModalCloseBtn.addEventListener("click", closeInspectModal);
    if (el.inspectModalDoneBtn) el.inspectModalDoneBtn.addEventListener("click", closeInspectModal);
    if (el.inspectModalBackdrop) el.inspectModalBackdrop.addEventListener("click", closeInspectModal);

    // ========================================================
    // Modal 2: Edit Farmer Profile
    // ========================================================
    function openEditModal(f) {
        if (!el.editFarmerModal) return;
        el.editFarmerId.value = f.id;
        el.editFarmerName.value = f.name || "";
        el.editFarmerPhone.value = f.phone || "";
        el.editFarmerEmail.value = f.email || "";
        el.editFarmerState.value = f.state || "";
        el.editFarmerDistrict.value = f.district || "";
        el.editFarmerVillage.value = f.village || "";
        el.editFarmerFeedback.style.display = "none";
        el.editFarmerModal.style.display = "flex";
    }

    function closeEditModal() {
        if (el.editFarmerModal) el.editFarmerModal.style.display = "none";
    }
    if (el.editFarmerCloseBtn) el.editFarmerCloseBtn.addEventListener("click", closeEditModal);
    if (el.editFarmerCancelBtn) el.editFarmerCancelBtn.addEventListener("click", closeEditModal);
    if (el.editFarmerBackdrop) el.editFarmerBackdrop.addEventListener("click", closeEditModal);

    if (el.editFarmerForm) {
        el.editFarmerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const farmerId = el.editFarmerId.value;
            const payload = {
                name: el.editFarmerName.value.trim(),
                phone: el.editFarmerPhone.value.trim(),
                email: el.editFarmerEmail.value.trim() || null,
                state: el.editFarmerState.value.trim(),
                district: el.editFarmerDistrict.value.trim(),
                village: el.editFarmerVillage.value.trim(),
            };

            el.editFarmerFeedback.style.display = "block";
            el.editFarmerFeedback.className = "form-feedback feedback-info";
            el.editFarmerFeedback.textContent = "Updating farmer profile...";

            try {
                const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    el.editFarmerFeedback.className = "form-feedback feedback-success";
                    el.editFarmerFeedback.textContent = "Farmer profile updated successfully!";
                    setTimeout(() => {
                        closeEditModal();
                        loadFarmers();
                        loadKPIs();
                    }, 500);
                } else {
                    el.editFarmerFeedback.className = "form-feedback feedback-error";
                    el.editFarmerFeedback.textContent = data.error || "Update failed.";
                }
            } catch (err) {
                el.editFarmerFeedback.className = "form-feedback feedback-error";
                el.editFarmerFeedback.textContent = "Network error. Please try again.";
            }
        });
    }

    // ========================================================
    // Modal 3: Reset Farmer Password
    // ========================================================
    function openResetPasswordModal(farmerId, farmerName) {
        if (!el.resetPasswordModal) return;
        el.resetFarmerId.value = farmerId;
        el.resetFarmerNameLabel.textContent = `Setting new master/temporary password for farmer ${farmerName} (${farmerId}).`;
        el.adminNewFarmerPassword.value = "";
        el.resetPasswordFeedback.style.display = "none";
        el.resetPasswordModal.style.display = "flex";
    }

    function closeResetPasswordModal() {
        if (el.resetPasswordModal) el.resetPasswordModal.style.display = "none";
    }
    if (el.resetPasswordCloseBtn) el.resetPasswordCloseBtn.addEventListener("click", closeResetPasswordModal);
    if (el.resetPasswordCancelBtn) el.resetPasswordCancelBtn.addEventListener("click", closeResetPasswordModal);
    if (el.resetPasswordBackdrop) el.resetPasswordBackdrop.addEventListener("click", closeResetPasswordModal);

    if (el.resetPasswordForm) {
        el.resetPasswordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const farmerId = el.resetFarmerId.value;
            const newPassword = el.adminNewFarmerPassword.value.trim();

            if (!newPassword || newPassword.length < 6) {
                el.resetPasswordFeedback.style.display = "block";
                el.resetPasswordFeedback.className = "form-feedback feedback-error";
                el.resetPasswordFeedback.textContent = "Password must be at least 6 characters.";
                return;
            }

            el.resetPasswordFeedback.style.display = "block";
            el.resetPasswordFeedback.className = "form-feedback feedback-info";
            el.resetPasswordFeedback.textContent = "Hashing and securely updating password...";

            try {
                const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}/reset-password`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ password: newPassword }),
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    el.resetPasswordFeedback.className = "form-feedback feedback-success";
                    el.resetPasswordFeedback.textContent = "Password securely updated! The farmer can now log in with the new password.";
                    setTimeout(() => {
                        closeResetPasswordModal();
                    }, 800);
                } else {
                    el.resetPasswordFeedback.className = "form-feedback feedback-error";
                    el.resetPasswordFeedback.textContent = data.error || "Reset failed.";
                }
            } catch (err) {
                el.resetPasswordFeedback.className = "form-feedback feedback-error";
                el.resetPasswordFeedback.textContent = "Network error. Please try again.";
            }
        });
    }

    // ========================================================
    // Farmer Suspension & Activation
    // ========================================================
    async function toggleFarmerStatus(farmerId, currentStatus, farmerName) {
        const isCurrentlyActive = (currentStatus || "Active").toLowerCase() === "active";
        const newStatus = isCurrentlyActive ? "Suspended" : "Active";
        let reason = "";

        if (isCurrentlyActive) {
            reason = prompt(`Please enter reason for suspending farmer account '${farmerName}':`, "Administrative policy compliance");
            if (reason === null) return; // User cancelled
        } else {
            if (!confirm(`Are you sure you want to reactivate farmer account '${farmerName}'?`)) return;
        }

        try {
            const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}/status`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: newStatus, reason: reason }),
            });
            const data = await res.json();
            if (res.ok && data.success) {
                loadFarmers();
                loadKPIs();
            } else {
                alert(`Status update failed: ${data.error || "Unknown error"}`);
            }
        } catch (err) {
            alert("Network error updating farmer status.");
        }
    }

    // ========================================================
    // Modal 4: Administrative Impersonation
    // ========================================================
    function openImpersonationModal(farmerId, farmerName) {
        if (!el.impersonationModal) return;
        el.impersonateFarmerId.value = farmerId;
        el.impersonateTargetName.textContent = `${farmerName} (${farmerId})`;
        el.impersonationReason.value = "Diagnostic verification & irrigation schedule inspection";
        el.impersonationFeedback.style.display = "none";
        el.impersonationModal.style.display = "flex";
    }

    function closeImpersonationModal() {
        if (el.impersonationModal) el.impersonationModal.style.display = "none";
    }
    if (el.impersonationCloseBtn) el.impersonationCloseBtn.addEventListener("click", closeImpersonationModal);
    if (el.impersonationCancelBtn) el.impersonationCancelBtn.addEventListener("click", closeImpersonationModal);
    if (el.impersonationBackdrop) el.impersonationBackdrop.addEventListener("click", closeImpersonationModal);

    if (el.impersonationForm) {
        el.impersonationForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const farmerId = el.impersonateFarmerId.value;
            const reason = el.impersonationReason.value.trim();

            el.impersonationFeedback.style.display = "block";
            el.impersonationFeedback.className = "form-feedback feedback-info";
            el.impersonationFeedback.textContent = "Logging inspection session & initiating farmer dashboard...";

            try {
                const res = await fetch(`/api/admin/farmers/${encodeURIComponent(farmerId)}/impersonate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reason: reason }),
                });
                const data = await res.json();
                if (res.ok && data.status === "success") {
                    el.impersonationFeedback.className = "form-feedback feedback-success";
                    el.impersonationFeedback.textContent = "Inspection session authorized! Opening farmer dashboard...";
                    setTimeout(() => {
                        window.location.href = data.redirect || "/";
                    }, 500);
                } else {
                    el.impersonationFeedback.className = "form-feedback feedback-error";
                    el.impersonationFeedback.textContent = data.error || "Impersonation authorization failed.";
                }
            } catch (err) {
                el.impersonationFeedback.className = "form-feedback feedback-error";
                el.impersonationFeedback.textContent = "Network error. Please try again.";
            }
        });
    }

    // ========================================================
    // Global Farm Management
    // ========================================================
    async function loadFarms() {
        try {
            const sq = el.farmSearchInput ? el.farmSearchInput.value.trim().toLowerCase() : "";
            const res = await fetch("/api/admin/farms");
            if (!res.ok) return;
            allFarms = await res.json();

            let filtered = allFarms;
            if (sq) {
                filtered = allFarms.filter(fm => {
                    const str = `${fm.name} ${fm.farmer_name} ${fm.village} ${fm.district} ${fm.state}`.toLowerCase();
                    return str.includes(sq);
                });
            }
            renderFarmsTable(filtered);
        } catch (err) {
            console.error("Failed to load farms:", err);
        }
    }

    function renderFarmsTable(farms) {
        if (!el.farmsTableBody) return;
        el.farmsTableBody.innerHTML = "";

        if (!farms || farms.length === 0) {
            el.farmsTableBody.innerHTML = `<tr><td colspan="9" class="text-center">No agricultural holdings found.</td></tr>`;
            return;
        }

        farms.forEach(fm => {
            const tr = document.createElement("tr");
            const cropsChips = (fm.sections || [])
                .map(s => `<span class="crop-chip ${s.is_empty ? 'chip-empty' : ''}">${escapeHtml(s.crop || s.name)} (${s.area_acres} Ac)</span>`)
                .join(" ");

            tr.innerHTML = `
                <td><strong>${escapeHtml(fm.name || "Primary Farm")}</strong><br><small class="text-muted"><code>${escapeHtml(fm.id)}</code></small></td>
                <td>
                    <strong>${escapeHtml(fm.farmer_name || "--")}</strong><br>
                    <small class="text-muted">📞 ${escapeHtml(fm.farmer_phone || "")}</small>
                </td>
                <td>${escapeHtml(fm.village || "")}, ${escapeHtml(fm.district || "")}, <strong>${escapeHtml(fm.state)}</strong></td>
                <td><code>${(fm.latitude || 0).toFixed(4)}, ${(fm.longitude || 0).toFixed(4)}</code></td>
                <td><strong>${fm.total_area_acres} ${escapeHtml(fm.unit || "Acres")}</strong></td>
                <td><span class="text-allocated">${fm.allocated_land} Ac</span></td>
                <td><span class="text-available">${fm.available_land} Ac</span></td>
                <td>${fm.sections_count || 0}</td>
                <td>${cropsChips || "<span class='text-muted'>None</span>"}</td>
            `;
            el.farmsTableBody.appendChild(tr);
        });
    }

    if (el.farmSearchInput) el.farmSearchInput.addEventListener("input", debounce(loadFarms, 300));
    if (el.btnRefreshFarms) el.btnRefreshFarms.addEventListener("click", loadFarms);

    // ========================================================
    // Global Irrigation Schedule Monitoring
    // ========================================================
    async function loadSchedules() {
        try {
            const status = el.schedStatusFilter ? el.schedStatusFilter.value : "all";
            const crop = el.schedCropFilter ? el.schedCropFilter.value : "all";

            const params = new URLSearchParams();
            if (status && status !== "all") params.set("status", status);
            if (crop && crop !== "all") params.set("crop", crop);

            const res = await fetch(`/api/admin/schedules?${params.toString()}`);
            if (!res.ok) return;
            allSchedules = await res.json();
            renderSchedulesTable(allSchedules);
        } catch (err) {
            console.error("Failed to load schedules:", err);
        }
    }

    function renderSchedulesTable(schedules) {
        if (!el.schedulesTableBody) return;
        el.schedulesTableBody.innerHTML = "";

        if (!schedules || schedules.length === 0) {
            el.schedulesTableBody.innerHTML = `<tr><td colspan="9" class="text-center">No irrigation schedules found matching filters.</td></tr>`;
            return;
        }

        schedules.forEach(sc => {
            const tr = document.createElement("tr");
            const st = (sc.status || "Upcoming").toLowerCase();
            const badgeClass = st === "completed" ? "pill-completed" : (st === "skipped" ? "pill-skipped" : "pill-upcoming");

            tr.innerHTML = `
                <td>
                    <strong>${escapeHtml(sc.farmer_name || "--")}</strong><br>
                    <small class="text-muted"><code>${escapeHtml(sc.farmer_id)}</code></small>
                </td>
                <td>${escapeHtml(sc.farmer_village || "")}, ${escapeHtml(sc.farmer_state || "")}</td>
                <td>
                    <strong>${escapeHtml(sc.farm_name || "Farm")}</strong><br>
                    <small class="text-muted">${escapeHtml(sc.section_name || "--")}</small>
                </td>
                <td><strong>${escapeHtml(sc.crop || "--")}</strong> (${sc.area_acres || 0} Ac)</td>
                <td><strong>${escapeHtml(sc.irrigation_date)}</strong></td>
                <td>${escapeHtml(sc.recommended_time || "06:00 AM")}</td>
                <td><strong>${sc.water_quantity_liters} L</strong></td>
                <td><span class="status-pill ${badgeClass}">${escapeHtml(sc.status)}</span></td>
                <td style="font-size: 11px; max-width: 250px;">${escapeHtml(sc.ai_rationale || "--")}</td>
            `;
            el.schedulesTableBody.appendChild(tr);
        });
    }

    if (el.schedStatusFilter) el.schedStatusFilter.addEventListener("change", loadSchedules);
    if (el.schedCropFilter) el.schedCropFilter.addEventListener("change", loadSchedules);
    if (el.btnRefreshSchedules) el.btnRefreshSchedules.addEventListener("click", loadSchedules);

    // ========================================================
    // Live Weather Monitoring Across Farms
    // ========================================================
    async function loadWeather() {
        try {
            const res = await fetch("/api/admin/weather");
            if (!res.ok) return;
            allWeather = await res.json();
            renderWeatherTable(allWeather);
        } catch (err) {
            console.error("Failed to load weather:", err);
        }
    }

    function renderWeatherTable(stations) {
        if (!el.weatherStationsTableBody) return;
        el.weatherStationsTableBody.innerHTML = "";

        if (!stations || stations.length === 0) {
            el.weatherStationsTableBody.innerHTML = `<tr><td colspan="9" class="text-center">No weather records found.</td></tr>`;
            return;
        }

        stations.forEach(ws => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <strong>${escapeHtml(ws.village)}</strong><br>
                    <small class="text-muted">${escapeHtml(ws.district)}, ${escapeHtml(ws.state)}</small>
                </td>
                <td><code>${(ws.latitude || 0).toFixed(4)}, ${(ws.longitude || 0).toFixed(4)}</code></td>
                <td>${ws.farmers_count} Farmers (${ws.farms_count} Farms)</td>
                <td><strong>${ws.current_temp !== null ? ws.current_temp + ' °C' : '--'}</strong></td>
                <td>${ws.current_humidity !== null ? ws.current_humidity + ' %' : '--'}</td>
                <td><span class="weather-cond-badge">🌤️ ${escapeHtml(ws.current_weather || "Sync Pending")}</span></td>
                <td>${ws.current_rainfall !== null ? ws.current_rainfall + ' mm' : '0.0 mm'}</td>
                <td><strong>${ws.forecast_rainfall_24h !== null ? ws.forecast_rainfall_24h + ' mm' : '0.0 mm'}</strong></td>
                <td>
                    <span class="badge ${ws.cache_age_minutes < 15 ? 'badge-active' : 'badge-cached'}">${escapeHtml(ws.status)}</span><br>
                    <small class="text-muted">${ws.cache_age_minutes}m ago · Open-Meteo</small>
                </td>
            `;
            el.weatherStationsTableBody.appendChild(tr);
        });
    }

    if (el.btnRefreshWeatherStations) el.btnRefreshWeatherStations.addEventListener("click", loadWeather);

    // ========================================================
    // AI System Monitoring & Health Diagnostics
    // ========================================================
    async function loadAIStatus() {
        try {
            const res = await fetch("/api/admin/ai-system");
            if (!res.ok) return;
            const data = await res.json();

            // Overview badges
            if (el.overviewGeminiStatus) {
                el.overviewGeminiStatus.textContent = data.gemini_api.configured
                    ? "Online · Connected to Gemini 1.5 / 2.5 Flash"
                    : "Grounded Agri Engine Active (API Key Not Set)";
            }
            if (el.overviewGeminiBadge) {
                el.overviewGeminiBadge.className = data.gemini_api.configured ? "status-badge badge-green" : "status-badge badge-amber";
                el.overviewGeminiBadge.textContent = data.gemini_api.configured ? "Online" : "Fallback";
            }

            // Gemini diagnostics card
            if (el.geminiDiagBody) {
                el.geminiDiagBody.innerHTML = `
                    <div class="diag-item">
                        <span class="diag-key">API Status:</span>
                        <strong class="${data.gemini_api.configured ? 'text-success' : 'text-warning'}">${escapeHtml(data.gemini_api.status)}</strong>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Target Models:</span>
                        <span><code>gemini-1.5-flash</code> / <code>gemini-2.5-flash</code></span>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Multilingual Support:</span>
                        <span>English, हिन्दी, తెలుగు, ਪੰਜਾਬੀ (Automatic Language Detection)</span>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Chatbot Memory:</span>
                        <span>Context-Aware Session Injection (Farmer Name, Location, Crops, Schedules)</span>
                    </div>
                `;
            }

            // ML Model diagnostics card
            if (el.modelDiagBody) {
                el.modelDiagBody.innerHTML = `
                    <div class="diag-item">
                        <span class="diag-key">Model Name:</span>
                        <strong>${escapeHtml(data.ml_model.name)}</strong>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Decision Hierarchy:</span>
                        <span><strong>Rule-over-ML (Single Source of Truth)</strong></span>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Dataset & Samples:</span>
                        <span>16,240 Indian Agro-Climatic Samples across 36 States & UTs</span>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Accuracy Metric:</span>
                        <strong class="text-success">${escapeHtml(data.ml_model.accuracy)}</strong>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Total Predictions:</span>
                        <strong>${data.predictions_count} Scheduled Recommendations</strong>
                    </div>
                `;
            }

            // Open-Meteo Diagnostics card
            if (el.weatherDiagBody) {
                el.weatherDiagBody.innerHTML = `
                    <div class="diag-item">
                        <span class="diag-key">Provider:</span>
                        <strong>${escapeHtml(data.weather_api.provider)}</strong>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Caching Engine:</span>
                        <span>15-Minute SQLite Caching with GPS Coordinate Rounding</span>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Cached Locations:</span>
                        <strong>${data.weather_api.total_cached_locations} Stations Active</strong>
                    </div>
                    <div class="diag-item">
                        <span class="diag-key">Server Timestamp:</span>
                        <span><code>${escapeHtml(formatDateTime(data.server_time))}</code></span>
                    </div>
                `;
            }
        } catch (err) {
            console.error("AI diagnostics error:", err);
        }
    }

    if (el.btnRefreshAIStatus) el.btnRefreshAIStatus.addEventListener("click", loadAIStatus);

    // ========================================================
    // Security & Administrative Audit Logs
    // ========================================================
    async function loadAuditLogs() {
        try {
            const action = el.auditActionFilter ? el.auditActionFilter.value : "all";
            const params = new URLSearchParams();
            if (action && action !== "all") params.set("action", action);
            params.set("limit", "100");

            const res = await fetch(`/api/admin/audit-logs?${params.toString()}`);
            if (!res.ok) return;
            allAuditLogs = await res.json();
            renderAuditLogsTable(allAuditLogs);
        } catch (err) {
            console.error("Failed to load audit logs:", err);
        }
    }

    function renderAuditLogsTable(logs) {
        if (!el.auditLogsTableBody) return;
        el.auditLogsTableBody.innerHTML = "";

        if (!logs || logs.length === 0) {
            el.auditLogsTableBody.innerHTML = `<tr><td colspan="7" class="text-center">No security audit logs recorded.</td></tr>`;
            return;
        }

        logs.forEach(l => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><code>${escapeHtml(formatDateTime(l.created_at))}</code></td>
                <td><strong>${escapeHtml(l.admin_username)}</strong></td>
                <td><span class="action-tag tag-${escapeHtml(l.action)}">${escapeHtml(l.action)}</span></td>
                <td>${escapeHtml(l.target_type || "--")}</td>
                <td><code>${escapeHtml(l.target_id || "--")}</code></td>
                <td style="max-width: 320px;">${escapeHtml(l.details || "--")}</td>
                <td><code>${escapeHtml(l.ip_address || "127.0.0.1")}</code></td>
            `;
            el.auditLogsTableBody.appendChild(tr);
        });
    }

    if (el.auditActionFilter) el.auditActionFilter.addEventListener("change", loadAuditLogs);
    if (el.btnRefreshAuditLogs) el.btnRefreshAuditLogs.addEventListener("click", loadAuditLogs);

    // Initialize application on page load
    document.addEventListener("DOMContentLoaded", () => {
        checkAdminAuth();
    });

})();
