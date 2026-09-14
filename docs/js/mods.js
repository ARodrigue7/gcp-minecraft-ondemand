// Custom Mods & Plugins Manager Controller
(function() {
    let activeFolder = "mods";
    let isVanilla = false;

    document.addEventListener("DOMContentLoaded", () => {
        initModsUI();
        
        // Load mods when tab is clicked
        const modsTabBtn = document.querySelector('[data-tab="mods-tab"]');
        if (modsTabBtn) {
            modsTabBtn.addEventListener("click", () => {
                refreshModsView();
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

    async function refreshModsView() {
        const apiEndpoint = window.APP_CONFIG?.API_URL;
        if (!apiEndpoint) return;

        try {
            // Check server config to determine if we are mods, plugins, or vanilla
            const cfgRes = await fetch(`${apiEndpoint}?action=admin_get_config`, {
                headers: getAuthHeaders()
            });
            if (cfgRes.ok) {
                const cfg = await cfgRes.json();
                const sType = (cfg.type || "paper").toLowerCase();
                
                const titleEl = document.getElementById("mods-tab-title");
                const descEl = document.getElementById("mods-tab-desc");
                const vanillaNotice = document.getElementById("mods-vanilla-notice");
                const managerContent = document.getElementById("mods-manager-content");

                if (sType === "vanilla") {
                    isVanilla = true;
                    if (vanillaNotice) vanillaNotice.classList.remove("hidden");
                    if (managerContent) managerContent.classList.add("hidden");
                    return;
                }

                isVanilla = false;
                if (vanillaNotice) vanillaNotice.classList.add("hidden");
                if (managerContent) managerContent.classList.remove("hidden");

                if (sType === "paper") {
                    activeFolder = "plugins";
                    if (titleEl) titleEl.textContent = "Plugins Manager";
                    if (descEl) descEl.textContent = "Manage Spigot/Paper plugins (.jar). Stored in GCS and synced to /plugins at boot.";
                } else {
                    activeFolder = "mods";
                    if (titleEl) titleEl.textContent = "Custom Mods Manager";
                    if (descEl) descEl.textContent = "Manage Fabric/Forge mod jars (.jar). Stored in GCS and synced to /mods at boot.";
                }
            }

            await loadModsList();
        } catch (err) {
            console.error("Failed to refresh mods view:", err);
        }
    }

    async function loadModsList() {
        if (isVanilla) return;
        const apiEndpoint = window.APP_CONFIG?.API_URL;
        const tbody = document.getElementById("mods-table-body");
        if (!tbody || !apiEndpoint) return;

        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-xs font-mono text-on-surface-variant">Loading files...</td></tr>';

        try {
            const res = await fetch(`${apiEndpoint}?action=admin_mods_list&folder=${activeFolder}`, {
                headers: getAuthHeaders()
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            renderModsTable(data.mods || []);
        } catch (err) {
            console.error("Failed to load mods list:", err);
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-xs font-mono text-error">Failed to load: ${err.message}</td></tr>`;
        }
    }

    function renderModsTable(mods) {
        const tbody = document.getElementById("mods-table-body");
        const countBadge = document.getElementById("mods-count-badge");
        if (!tbody) return;

        if (countBadge) countBadge.textContent = `${mods.length} File${mods.length === 1 ? '' : 's'}`;

        if (mods.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-xs font-mono text-on-surface-variant">No ${activeFolder} installed yet. Drag and drop .jar files above to upload.</td></tr>`;
            return;
        }

        tbody.innerHTML = mods.map(m => {
            const sizeStr = m.size > 1048576 
                ? (m.size / 1048576).toFixed(2) + " MB" 
                : (m.size / 1024).toFixed(1) + " KB";
            
            const isEnabled = m.enabled;
            const displayName = isEnabled ? m.filename : m.filename.replace(/\.disabled$/, "");

            return `
                <tr class="border-b border-white/5 hover:bg-surface-container-high/30 transition-colors">
                    <td class="p-3 font-mono text-xs text-white">
                        <div class="flex items-center gap-2">
                            <span class="material-symbols-outlined text-sm ${isEnabled ? 'text-primary' : 'text-on-surface-variant'}">extension</span>
                            <span class="${isEnabled ? '' : 'line-through text-on-surface-variant'}">${displayName}</span>
                            ${!isEnabled ? '<span class="text-[9px] font-mono px-1 py-0.2 rounded-xs bg-surface-container-highest text-on-surface-variant">DISABLED</span>' : ''}
                        </div>
                    </td>
                    <td class="p-3 font-mono text-xs text-on-surface-variant">${sizeStr}</td>
                    <td class="p-3">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${isEnabled ? 'bg-primary/20 text-primary' : 'bg-surface-container-highest text-on-surface-variant'}">
                            ${isEnabled ? 'Active' : 'Disabled'}
                        </span>
                    </td>
                    <td class="p-3 text-right space-x-2">
                        <button type="button" class="px-2.5 py-1 text-[11px] font-mono uppercase rounded-xs border border-white/10 hover:bg-white/5 transition-colors mod-toggle-btn" data-filename="${m.filename}">
                            ${isEnabled ? 'Disable' : 'Enable'}
                        </button>
                        <button type="button" class="px-2.5 py-1 text-[11px] font-mono uppercase rounded-xs text-red-400 hover:bg-red-500/10 border border-red-500/20 transition-colors mod-delete-btn" data-filename="${m.filename}">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        // Bind toggle buttons
        tbody.querySelectorAll(".mod-toggle-btn").forEach(btn => {
            btn.addEventListener("click", () => handleToggleMod(btn.getAttribute("data-filename")));
        });

        // Bind delete buttons
        tbody.querySelectorAll(".mod-delete-btn").forEach(btn => {
            btn.addEventListener("click", () => handleDeleteMod(btn.getAttribute("data-filename")));
        });
    }

    async function handleToggleMod(filename) {
        const apiEndpoint = window.APP_CONFIG?.API_URL;
        if (!apiEndpoint) return;

        try {
            const res = await fetch(`${apiEndpoint}?action=admin_mods_toggle`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ filename, folder: activeFolder })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
            
            if (window.showToast) window.showToast(`Mod ${data.enabled ? 'enabled' : 'disabled'}. Applies on next start.`, "info");
            await loadModsList();
        } catch (err) {
            console.error("Failed to toggle mod:", err);
            if (window.showToast) window.showToast(err.message || "Toggle failed", "error");
        }
    }

    async function handleDeleteMod(filename) {
        if (!confirm(`Are you sure you want to delete ${filename}?`)) return;

        const apiEndpoint = window.APP_CONFIG?.API_URL;
        if (!apiEndpoint) return;

        try {
            const res = await fetch(`${apiEndpoint}?action=admin_mods_delete`, {
                method: "POST",
                headers: getAuthHeaders(),
                body: JSON.stringify({ filename, folder: activeFolder })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
            
            if (window.showToast) window.showToast(`Deleted ${filename}`, "success");
            await loadModsList();
        } catch (err) {
            console.error("Failed to delete mod:", err);
            if (window.showToast) window.showToast(err.message || "Delete failed", "error");
        }
    }

    function initModsUI() {
        const dropZone = document.getElementById("mods-drop-zone");
        const fileInput = document.getElementById("mods-file-input");

        if (dropZone && fileInput) {
            dropZone.addEventListener("click", () => fileInput.click());

            dropZone.addEventListener("dragover", (e) => {
                e.preventDefault();
                dropZone.classList.add("border-primary", "bg-primary/5");
            });

            dropZone.addEventListener("dragleave", () => {
                dropZone.classList.remove("border-primary", "bg-primary/5");
            });

            dropZone.addEventListener("drop", (e) => {
                e.preventDefault();
                dropZone.classList.remove("border-primary", "bg-primary/5");
                if (e.dataTransfer?.files?.length) {
                    uploadFiles(e.dataTransfer.files);
                }
            });

            fileInput.addEventListener("change", () => {
                if (fileInput.files?.length) {
                    uploadFiles(fileInput.files);
                    fileInput.value = "";
                }
            });
        }
    }

    async function uploadFiles(fileList) {
        const apiEndpoint = window.APP_CONFIG?.API_URL;
        const statusEl = document.getElementById("mods-upload-status");
        if (!apiEndpoint) return;

        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            if (!file.name.endsWith(".jar") && !file.name.endsWith(".zip")) {
                if (window.showToast) window.showToast(`Skipping ${file.name}: only .jar or .zip supported`, "warning");
                continue;
            }

            try {
                if (statusEl) {
                    statusEl.classList.remove("hidden");
                    statusEl.textContent = `Uploading ${file.name} (${i + 1}/${fileList.length})...`;
                }

                // 1. Request GCS Resumable Session URI
                const sessionRes = await fetch(`${apiEndpoint}?action=admin_mods_upload_session`, {
                    method: "POST",
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ filename: file.name, folder: activeFolder })
                });

                const sessionData = await sessionRes.json();
                if (!sessionRes.ok) throw new Error(sessionData.error || `HTTP ${sessionRes.status}`);

                // 2. Direct PUT to GCS resumable session URI
                const uploadRes = await fetch(sessionData.upload_url, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/java-archive"
                    },
                    body: file
                });

                if (!uploadRes.ok) throw new Error(`Upload failed with GCS HTTP ${uploadRes.status}`);

                if (window.showToast) window.showToast(`Uploaded ${file.name} successfully`, "success");
            } catch (err) {
                console.error("Upload error:", err);
                if (window.showToast) window.showToast(`Failed to upload ${file.name}: ${err.message}`, "error");
            }
        }

        if (statusEl) {
            statusEl.textContent = "Upload complete.";
            setTimeout(() => statusEl.classList.add("hidden"), 3000);
        }

        await loadModsList();
    }
})();
