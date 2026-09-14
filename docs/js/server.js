// Server Setup & Modpack Configuration Controller
(function() {
    let serverConfig = null;
    let selectedType = "paper";
    let selectedMachine = "e2-medium";
    let searchDebounceTimer = null;

    const typeDetails = {
        vanilla: { title: "Vanilla", badge: "No Mods", minRam: "2G" },
        paper: { title: "Paper", badge: "Plugins Only", minRam: "2G" },
        fabric: { title: "Fabric", badge: "Mods Loader", minRam: "4G" },
        modrinth: { title: "Modrinth Pack", badge: "Full Modpack", minRam: "6G+" },
        curseforge: { title: "CurseForge Pack", badge: "Full Modpack", minRam: "6G+" }
    };

    document.addEventListener("DOMContentLoaded", () => {
        initEventListeners();
        
        // Load config when server tab is clicked
        const serverTabBtn = document.querySelector('[data-tab="server-tab"]');
        if (serverTabBtn) {
            serverTabBtn.addEventListener("click", () => {
                loadServerConfig();
            });
        }
    });

    function getAuthHeaders() {
        const passcode = localStorage.getItem("gcp_mc_admin_passcode") || "";
        const username = localStorage.getItem("gcp_mc_admin_username") || "";
        return {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${passcode}`,
            "X-Admin-User": username
        };
    }

    async function loadServerConfig() {
        const apiEndpoint = window.APP_CONFIG?.API_URL;
        if (!apiEndpoint) return;

        try {
            const res = await fetch(`${apiEndpoint}?action=admin_get_config`, {
                headers: getAuthHeaders()
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            serverConfig = await res.json();
            renderConfig(serverConfig);
        } catch (err) {
            console.error("Failed to load server config:", err);
            if (window.showToast) window.showToast("Failed to load server settings", "error");
        }
    }

    function renderConfig(cfg) {
        selectedType = cfg.type || "paper";
        selectedMachine = cfg.machine_type || "e2-medium";

        // Update active server type card
        document.querySelectorAll(".server-type-card").forEach(card => {
            const type = card.getAttribute("data-type");
            if (type === selectedType) {
                card.classList.add("border-primary", "bg-primary/10");
                card.classList.remove("border-outline-variant/30", "bg-surface-container/40");
            } else {
                card.classList.remove("border-primary", "bg-primary/10");
                card.classList.add("border-outline-variant/30", "bg-surface-container/40");
            }
        });

        // Update active machine radio
        const machineInput = document.querySelector(`input[name="machine-size"][value="${selectedMachine}"]`);
        if (machineInput) machineInput.checked = true;

        // Toggle sub-inputs based on type
        updateInputVisibility(selectedType);

        // Populate fields
        const versionInput = document.getElementById("server-version-input");
        if (versionInput) versionInput.value = cfg.minecraft_version || "LATEST";

        const modpackInput = document.getElementById("server-modpack-input");
        if (modpackInput) modpackInput.value = cfg.modpack_id || "";

        const idleSelect = document.getElementById("server-idle-select");
        if (idleSelect) idleSelect.value = String(cfg.idle_timeout_seconds || 600);

        const stampDisplay = document.getElementById("server-world-stamp");
        if (stampDisplay) stampDisplay.textContent = cfg.world_stamp || "paper";
    }

    function updateInputVisibility(type) {
        const versionContainer = document.getElementById("server-version-container");
        const modpackContainer = document.getElementById("server-modpack-container");
        const modpackLabel = document.getElementById("server-modpack-label");
        const modrinthSearch = document.getElementById("modrinth-search-container");

        if (type === "modrinth") {
            if (versionContainer) versionContainer.classList.add("hidden");
            if (modpackContainer) modpackContainer.classList.remove("hidden");
            if (modrinthSearch) modrinthSearch.classList.remove("hidden");
            if (modpackLabel) modpackLabel.textContent = "Modrinth Modpack Slug or ID";
        } else if (type === "curseforge") {
            if (versionContainer) versionContainer.classList.add("hidden");
            if (modpackContainer) modpackContainer.classList.remove("hidden");
            if (modrinthSearch) modrinthSearch.classList.add("hidden");
            if (modpackLabel) modpackLabel.textContent = "CurseForge Modpack Page URL";
        } else {
            if (versionContainer) versionContainer.classList.remove("hidden");
            if (modpackContainer) modpackContainer.classList.add("hidden");
            if (modrinthSearch) modrinthSearch.classList.add("hidden");
        }
    }

    function initEventListeners() {
        // Server type cards
        document.querySelectorAll(".server-type-card").forEach(card => {
            card.addEventListener("click", () => {
                selectedType = card.getAttribute("data-type");
                document.querySelectorAll(".server-type-card").forEach(c => {
                    c.classList.remove("border-primary", "bg-primary/10");
                    c.classList.add("border-outline-variant/30", "bg-surface-container/40");
                });
                card.classList.add("border-primary", "bg-primary/10");
                card.classList.remove("border-outline-variant/30", "bg-surface-container/40");
                updateInputVisibility(selectedType);
            });
        });

        // Machine size radios
        document.querySelectorAll('input[name="machine-size"]').forEach(radio => {
            radio.addEventListener("change", (e) => {
                selectedMachine = e.target.value;
            });
        });

        // Modrinth live search (direct browser call)
        const searchInput = document.getElementById("modrinth-search-input");
        if (searchInput) {
            searchInput.addEventListener("input", (e) => {
                const query = e.target.value.trim();
                clearTimeout(searchDebounceTimer);
                if (!query) {
                    renderSearchResults([]);
                    return;
                }
                searchDebounceTimer = setTimeout(() => searchModrinth(query), 300);
            });
        }

        // Save button
        const saveBtn = document.getElementById("server-save-btn");
        if (saveBtn) {
            saveBtn.addEventListener("click", handleSaveConfig);
        }

        // Restart now button
        const restartNowBtn = document.getElementById("server-restart-now-btn");
        if (restartNowBtn) {
            restartNowBtn.addEventListener("click", handleRestartNow);
        }
    }

    async function searchModrinth(query) {
        const resultsContainer = document.getElementById("modrinth-search-results");
        if (resultsContainer) resultsContainer.innerHTML = '<div class="p-2 text-xs text-on-surface-variant">Searching Modrinth...</div>';

        try {
            const url = `https://api.modrinth.com/v2/search?query=${encodeURIComponent(query)}&facets=[["project_type:modpack"]]&limit=5`;
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Modrinth API error: ${res.status}`);
            const data = await res.json();
            renderSearchResults(data.hits || []);
        } catch (err) {
            console.error("Modrinth search error:", err);
            if (resultsContainer) resultsContainer.innerHTML = '<div class="p-2 text-xs text-error">Search failed</div>';
        }
    }

    function renderSearchResults(hits) {
        const resultsContainer = document.getElementById("modrinth-search-results");
        if (!resultsContainer) return;

        if (hits.length === 0) {
            resultsContainer.innerHTML = "";
            return;
        }

        resultsContainer.innerHTML = hits.map(hit => `
            <div class="p-2.5 flex items-center justify-between border-b border-white/5 hover:bg-surface-container-high/40 transition-colors cursor-pointer modpack-result-item" data-slug="${hit.slug}">
                <div class="flex items-center gap-2.5 overflow-hidden">
                    ${hit.icon_url ? `<img src="${hit.icon_url}" class="w-7 h-7 rounded-sm object-cover" alt="" />` : '<span class="material-symbols-outlined text-primary text-base">extension</span>'}
                    <div class="truncate">
                        <div class="text-xs font-bold text-white truncate">${hit.title}</div>
                        <div class="text-[10px] text-on-surface-variant truncate">${hit.description}</div>
                    </div>
                </div>
                <button type="button" class="px-2.5 py-1 text-[10px] uppercase font-bold border border-primary text-primary hover:bg-primary/10 rounded-xs shrink-0 ml-2">Select</button>
            </div>
        `).join("");

        resultsContainer.querySelectorAll(".modpack-result-item").forEach(item => {
            item.addEventListener("click", () => {
                const slug = item.getAttribute("data-slug");
                const modpackInput = document.getElementById("server-modpack-input");
                if (modpackInput) modpackInput.value = slug;
                resultsContainer.innerHTML = "";
            });
        });
    }

    async function handleSaveConfig() {
        const saveBtn = document.getElementById("server-save-btn");
        const statusNotice = document.getElementById("server-save-notice");
        const restartNowBtn = document.getElementById("server-restart-now-btn");
        const versionInput = document.getElementById("server-version-input");
        const modpackInput = document.getElementById("server-modpack-input");
        const idleSelect = document.getElementById("server-idle-select");
        const freshCheckbox = document.getElementById("server-fresh-world-checkbox");

        const payload = {
            type: selectedType,
            machine_type: selectedMachine,
            minecraft_version: versionInput ? versionInput.value.trim() : "LATEST",
            modpack_id: modpackInput ? modpackInput.value.trim() : "",
            idle_timeout_seconds: idleSelect ? parseInt(idleSelect.value, 10) : 600,
            world_stamp: (freshCheckbox && freshCheckbox.checked) ? selectedType : (serverConfig?.world_stamp || selectedType)
        };

        if (saveBtn) saveBtn.disabled = true;

        try {
            const apiEndpoint = window.APP_CONFIG?.API_URL;
            const res = await fetch(`${apiEndpoint}?action=admin_save_config`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

            serverConfig = data.config;
            if (window.showToast) window.showToast("Settings saved successfully", "success");

            if (statusNotice) {
                statusNotice.classList.remove("hidden");
                statusNotice.textContent = "Saved — applies next time the server starts.";
            }

            // Check if server is running to prompt restart
            const vmStatus = document.getElementById("info-status")?.textContent?.trim() || "";
            if (vmStatus === "RUNNING" && restartNowBtn) {
                restartNowBtn.classList.remove("hidden");
            }
        } catch (err) {
            console.error("Save config error:", err);
            if (window.showToast) window.showToast(err.message || "Failed to save settings", "error");
        } finally {
            if (saveBtn) saveBtn.disabled = false;
        }
    }

    async function handleRestartNow() {
        const restartBtn = document.getElementById("server-restart-now-btn");
        if (restartBtn) restartBtn.disabled = true;

        try {
            const apiEndpoint = window.APP_CONFIG?.API_URL;
            const res = await fetch(`${apiEndpoint}?action=admin_power`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ command: "restart" })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);

            if (window.showToast) window.showToast("Server restart triggered. Applying new settings...", "info");
            restartBtn.classList.add("hidden");
        } catch (err) {
            console.error("Restart error:", err);
            if (window.showToast) window.showToast("Failed to trigger restart", "error");
        } finally {
            if (restartBtn) restartBtn.disabled = false;
        }
    }
})();
