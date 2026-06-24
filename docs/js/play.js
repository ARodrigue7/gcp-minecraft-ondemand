        // State
        let customServers = [];
        let favorites = [];
        let selectedServerId = null;
        let statuses = {}; // Keyed by server ID: { status, ip }

        // DOM elements
        const serverList = document.getElementById("server-list");
        const searchInput = document.getElementById("search-input");
        const detailsPanel = document.getElementById("details-panel");
        const addBtn = document.getElementById("add-btn");
        const refreshBtn = document.getElementById("refresh-btn");
        const globalToast = document.getElementById("global-toast");

        // Modals
        const addModal = document.getElementById("add-modal");
        const closeAddBtn = document.getElementById("close-add-btn");
        const addForm = document.getElementById("add-form");
        const editModal = document.getElementById("edit-modal");
        const closeEditBtn = document.getElementById("close-edit-btn");
        const editForm = document.getElementById("edit-form");

        // Load config from local storage
        try {
            const storedFavs = localStorage.getItem("mcod_favorites");
            if (storedFavs) favorites = JSON.parse(storedFavs);
            
            const storedCustom = localStorage.getItem("mcod_custom_servers");
            if (storedCustom) customServers = JSON.parse(storedCustom);
        } catch (e) {
            console.error("Local storage error:", e);
        }

        // Generate ID for custom servers
        function generateId() {
            return 'custom_' + Math.random().toString(36).substr(2, 9);
        }

        // Get merged list of servers
        function getMasterList() {
            const list = [];
            
            // 1. Primary GCP Server (from config.js)
            if (window.serverConfig && window.serverConfig.statusUrl) {
                list.push({
                    id: "primary",
                    name: "Primary On-Demand Server",
                    domain: window.serverConfig.domainName,
                    statusUrl: window.serverConfig.statusUrl,
                    isPrivate: true,
                    isPrimary: true,
                    description: "Main scale-to-zero Minecraft server"
                });
            }

            // 2. Custom Local Servers
            customServers.forEach(srv => {
                list.push({
                    id: srv.id,
                    name: srv.name,
                    domain: srv.domain,
                    statusUrl: srv.statusUrl || "",
                    isPrivate: srv.statusUrl ? true : false,
                    isCustom: true,
                    description: srv.description || "Local Custom Server"
                });
            });

            return list;
        }

        // Setup base event listeners
        function setupEventListeners() {
            // Search
            searchInput.addEventListener("input", renderServers);

            // Refresh
            refreshBtn.addEventListener("click", refreshAll);

            // Add Modal
            addBtn.addEventListener("click", () => {
                addForm.reset();
                addModal.classList.remove("hidden");
            });
            closeAddBtn.addEventListener("click", () => addModal.classList.add("hidden"));
            addModal.addEventListener("click", (e) => {
                if (e.target === addModal) addModal.classList.add("hidden");
            });

            // Edit Modal
            closeEditBtn.addEventListener("click", () => editModal.classList.add("hidden"));
            editModal.addEventListener("click", (e) => {
                if (e.target === editModal) editModal.classList.add("hidden");
            });

            // Add Form Submit
            addForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const newServer = {
                    id: generateId(),
                    name: document.getElementById("add-name-input").value.trim(),
                    domain: document.getElementById("add-domain-input").value.trim(),
                    description: document.getElementById("add-desc-input").value.trim(),
                    statusUrl: document.getElementById("add-api-input").value.trim(),
                    isCustom: true
                };

                customServers.push(newServer);
                localStorage.setItem("mcod_custom_servers", JSON.stringify(customServers));
                addModal.classList.add("hidden");
                showToast(`✅ Server "${newServer.name}" added successfully.`, "success");
                refreshAll();
            });

            // Edit Form Submit
            editForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const id = document.getElementById("edit-id-input").value;
                const idx = customServers.findIndex(s => s.id === id);
                if (idx > -1) {
                    customServers[idx] = {
                        ...customServers[idx],
                        name: document.getElementById("edit-name-input").value.trim(),
                        domain: document.getElementById("edit-domain-input").value.trim(),
                        description: document.getElementById("edit-desc-input").value.trim(),
                        statusUrl: document.getElementById("edit-api-input").value.trim()
                    };
                    localStorage.setItem("mcod_custom_servers", JSON.stringify(customServers));
                    editModal.classList.add("hidden");
                    showToast(`✅ Server "${customServers[idx].name}" updated.`, "success");
                    refreshAll();
                }
            });
        }

        function renderServers() {
            const query = searchInput.value.toLowerCase().trim();
            let list = getMasterList();

            if (query) {
                list = list.filter(srv => 
                    srv.name.toLowerCase().includes(query) || 
                    srv.domain.toLowerCase().includes(query) || 
                    srv.description.toLowerCase().includes(query)
                );
            }

            // Sort: Favorites first, then primary
            list.sort((a, b) => {
                const aFav = favorites.includes(a.id) || a.id === "primary";
                const bFav = favorites.includes(b.id) || b.id === "primary";
                
                if (aFav && !bFav) return -1;
                if (!aFav && bFav) return 1;
                
                if (a.id === "primary" && b.id !== "primary") return -1;
                if (a.id !== "primary" && b.id === "primary") return 1;
                
                return a.name.localeCompare(b.name);
            });

            serverList.innerHTML = "";

            if (list.length === 0) {
                serverList.innerHTML = `
                    <div class="empty-state" style="padding: 2rem 1rem;">
                        No servers found.
                    </div>
                `;
                return;
            }

            list.forEach(server => {
                const isSelected = selectedServerId === server.id;
                const isFav = favorites.includes(server.id) || server.id === "primary";
                const state = statuses[server.id] || { status: "checking" };

                let statusClass = "status-offline";
                let motdText = server.description;

                if (state.status === "checking") {
                    statusClass = "status-starting";
                    motdText = "Checking status...";
                } else if (state.status === "RUNNING") {
                    statusClass = "status-online";
                    motdText = "Online - Click to view connection info";
                } else if (state.status === "TERMINATED") {
                    statusClass = "status-offline";
                    motdText = "Offline - Click to start server";
                } else if (["PROVISIONING", "STAGING", "STARTING"].includes(state.status)) {
                    statusClass = "status-starting";
                    motdText = "Starting server instance...";
                } else {
                    if (!server.statusUrl) {
                        statusClass = "status-online";
                        motdText = server.description;
                    }
                }

                const starredClass = isFav ? "star-btn starred" : "star-btn";
                
                let badgesHtml = "";
                if (server.id === "primary") {
                    badgesHtml += `<span class="badge-tag primary">Primary</span> `;
                }
                if (server.isPrivate) {
                    badgesHtml += `<span class="badge-tag private">Private</span> `;
                } else {
                    badgesHtml += `<span class="badge-tag public">Public</span> `;
                }

                const li = document.createElement("div");
                li.className = `server-row-item ${isSelected ? "selected" : ""}`;
                
                li.addEventListener("click", (e) => {
                    if (!e.target.classList.contains("star-btn")) {
                        selectServer(server.id);
                    }
                });
                li.addEventListener("dblclick", (e) => {
                    if (!e.target.classList.contains("star-btn")) {
                        triggerJoinById(server.id);
                    }
                });

                li.innerHTML = `
                    <button type="button" class="${starredClass}" onclick="event.stopPropagation(); toggleStar('${server.id}')" title="Toggle Favorite">★</button>
                    <div class="row-details">
                        <div class="row-name-group">
                            <span class="row-name">${server.name}</span>
                            ${badgesHtml}
                        </div>
                        <div class="row-motd">${motdText}</div>
                        <div class="row-domain">${server.domain}</div>
                    </div>
                    <div class="row-status">
                        <div class="${statusClass}">
                            <span class="pulse-dot-mini"></span>
                        </div>
                    </div>
                `;
                serverList.appendChild(li);
            });
        }

        window.selectServer = function(id) {
            selectedServerId = id;
            renderServers();
            
            const list = getMasterList();
            const server = list.find(s => s.id === id);
            if (!server) return;

            renderSelectedServerDetails(server);
        };

        window.triggerJoinById = function(id) {
            const list = getMasterList();
            const server = list.find(s => s.id === id);
            if (server) triggerJoin(server);
        };

        function renderSelectedServerDetails(server) {
            const state = statuses[server.id] || { status: "checking" };
            
            let badgeClass = "badge loading";
            let badgeText = "Checking...";
            if (state.status === "RUNNING") {
                badgeClass = "badge online";
                badgeText = "Online";
            } else if (state.status === "TERMINATED") {
                badgeClass = "badge offline";
                badgeText = "Offline";
            } else if (["PROVISIONING", "STAGING", "STARTING"].includes(state.status)) {
                badgeClass = "badge starting";
                badgeText = "Starting...";
            } else if (state.status === "unknown" && !server.statusUrl) {
                badgeClass = "badge online";
                badgeText = "Online";
            }

            let whitelistFormHtml = "";
            if (server.isPrivate) {
                if (server.id === "primary") {
                    whitelistFormHtml = `
                        <div class="whitelist-section">
                            <h4 class="section-title">Request Whitelist Access</h4>
                            <p class="section-desc">Submit your Minecraft username. The admin will get a notification on Discord to whitelist you.</p>
                            <form id="whitelist-form" class="whitelist-form">
                                <div class="form-field" style="margin-bottom: 1rem;">
                                    <label for="mc-username" class="field-label" style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary); font-weight: 600;">Minecraft Username <span class="required" aria-hidden="true" style="color: #ef4444;">*</span></label>
                                    <input type="text" id="mc-username" placeholder="e.g. Steve" required aria-required="true" aria-describedby="username-hint" autocomplete="off" style="width: 100%; background: rgba(9, 26, 16, 0.6); border: 3px solid var(--wood-border); border-radius: 12px; color: var(--text-primary); padding: 0.75rem 1rem; font-size: 0.95rem; outline: none;">
                                    <p id="username-hint" class="field-hint" style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.4rem; opacity: 0.8;">Enter your exact in-game name (3-16 characters).</p>
                                </div>
                                <button type="submit" id="submit-btn" class="btn btn-secondary btn-block" style="padding: 0.75rem; width: 100%;">Submit Whitelist Request</button>
                            </form>
                            <div id="form-message" class="form-message hidden" role="alert" aria-live="polite" style="margin-top: 1rem; padding: 0.75rem; border-radius: 10px; font-size: 0.85rem;"></div>
                        </div>
                    `;
                } else {
                    whitelistFormHtml = `
                        <div class="whitelist-section" style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.5;">
                            🛡️ This server is private. To request whitelisting, please contact the server administrator directly.
                        </div>
                    `;
                }
            } else {
                whitelistFormHtml = `
                    <div class="whitelist-section" style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.5;">
                        🌳 This server is public! Anyone can join immediately. No whitelisting required.
                    </div>
                `;
            }

            let joinBtnText = "🎮 Join Server";
            let passcodeBoxHtml = "";
            let joinBtnDisabled = "";
            if (server.statusUrl && state.status === "TERMINATED") {
                joinBtnText = "⚡ Wake Up Server";
                passcodeBoxHtml = `
                    <div class="form-field" style="margin-bottom: 1rem;">
                        <label for="server-passcode" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary); display: block; margin-bottom: 0.5rem;">Server Passcode</label>
                        <input type="password" id="server-passcode" placeholder="Enter passcode to wake up..." style="width: 100%; background: rgba(9, 26, 16, 0.6); border: 3px solid var(--wood-border); border-radius: 12px; color: var(--text-primary); padding: 0.75rem 1rem; font-size: 0.95rem; outline: none;">
                    </div>
                `;
            } else if (state.status === "STARTING" || state.status === "PROVISIONING" || state.status === "STAGING") {
                joinBtnText = "⏳ Booting up...";
                joinBtnDisabled = "disabled";
            }

            let customActionsHtml = "";
            if (server.isCustom) {
                customActionsHtml = `
                    <div class="directory-buttons" style="margin-top: 1rem; border-top: 2px dashed rgba(255, 255, 255, 0.08); padding-top: 1rem;">
                        <button type="button" id="edit-btn" class="btn btn-primary" style="flex: 1;">✏️ Edit Details</button>
                        <button type="button" id="delete-btn" class="btn btn-primary" style="flex: 1; background: linear-gradient(to bottom, #f87171, #ef4444); border-color: #b91c1c; border-bottom-color: #991b1b;">🗑️ Delete</button>
                    </div>
                `;
            }

            detailsPanel.innerHTML = `
                <div class="details-wrapper">
                    <div>
                        <h3 class="panel-title" style="margin-bottom: 0.5rem; text-shadow: 2px 2px 0px var(--wood-border);">${server.name}</h3>
                        <p style="font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 1.25rem;">${server.description}</p>
                    </div>
                    
                    <div class="status-panel" style="margin-bottom: 0; padding: 1.5rem; background: rgba(9, 26, 16, 0.45); border: 2px solid var(--forest-border); border-radius: 20px;">
                        <div class="status-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px dashed rgba(255,255,255,0.08); padding-bottom: 0.75rem; margin-bottom: 1rem;">
                            <span class="status-label" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Server Status</span>
                            <div class="badge-status-wrap">
                                <div class="${badgeClass}">
                                    <span class="pulse-dot"></span>
                                    <span>${badgeText}</span>
                                </div>
                            </div>
                        </div>

                        <div class="connection-box">
                            <div class="connection-label">Server Address</div>
                            <div class="connection-input-group">
                                <input type="text" id="server-ip" value="${server.domain}" readonly>
                                <button id="copy-btn" class="btn btn-primary" title="Copy Address">
                                    <span id="copy-icon">📋</span>
                                    <span id="copy-text">Copy</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    ${passcodeBoxHtml}

                    <button type="button" id="main-join-btn" class="btn btn-secondary" style="width: 100%; font-size: 1.1rem; padding: 1rem;" ${joinBtnDisabled}>
                        ${joinBtnText}
                    </button>

                    ${whitelistFormHtml}
                    ${customActionsHtml}
                </div>
            `;

            setupDetailsListeners(server);
        }

        function setupDetailsListeners(server) {
            const copyBtn = document.getElementById("copy-btn");
            const copyText = document.getElementById("copy-text");
            const copyIcon = document.getElementById("copy-icon");
            const serverIpInput = document.getElementById("server-ip");
            const mainJoinBtn = document.getElementById("main-join-btn");
            const whitelistForm = document.getElementById("whitelist-form");

            copyBtn.addEventListener("click", () => {
                serverIpInput.select();
                serverIpInput.setSelectionRange(0, 99999);
                navigator.clipboard.writeText(serverIpInput.value)
                    .then(() => {
                        copyText.textContent = "Copied!";
                        copyIcon.textContent = "✅";
                        copyBtn.classList.add("copied");
                        setTimeout(() => {
                            copyText.textContent = "Copy";
                            copyIcon.textContent = "📋";
                            copyBtn.classList.remove("copied");
                        }, 2000);
                    });
            });

            mainJoinBtn.addEventListener("click", () => {
                const passcodeEl = document.getElementById("server-passcode");
                const passcode = passcodeEl ? passcodeEl.value.trim() : "";
                triggerJoin(server, passcode);
            });

            if (whitelistForm) {
                const mcUsernameInput = document.getElementById("mc-username");
                const submitBtn = document.getElementById("submit-btn");
                const formMessage = document.getElementById("form-message");

                whitelistForm.addEventListener("submit", async (e) => {
                    e.preventDefault();
                    const username = mcUsernameInput.value.trim();
                    if (!username) return;

                    const usernameRegex = /^[a-zA-Z0-9_]{3,16}$/;
                    if (!usernameRegex.test(username)) {
                        showFormMessage(formMessage, "Invalid username! 3-16 alphanumeric characters and underscores.", "error");
                        return;
                    }

                    submitBtn.disabled = true;
                    submitBtn.textContent = "Sending Request...";
                    formMessage.classList.add("hidden");

                    try {
                        const res = await fetch(server.statusUrl, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ action: "whitelist", username })
                        });

                        const data = await res.json();
                        if (res.ok && data.success) {
                            const displayMsg = data.message || `Success! Whitelist request for <strong>${username}</strong> sent.`;
                            showFormMessage(formMessage, displayMsg, "success");
                            mcUsernameInput.value = "";
                        } else {
                            throw new Error(data.error || "Failed to submit whitelist request.");
                        }
                    } catch (err) {
                        console.error(err);
                        showFormMessage(formMessage, err.message || "An unexpected error occurred.", "error");
                    } finally {
                        submitBtn.disabled = false;
                        submitBtn.textContent = "Submit Whitelist Request";
                    }
                });
            }

            // Edit Custom Server
            const editBtn = document.getElementById("edit-btn");
            if (editBtn) {
                editBtn.addEventListener("click", () => {
                    document.getElementById("edit-id-input").value = server.id;
                    document.getElementById("edit-name-input").value = server.name;
                    document.getElementById("edit-domain-input").value = server.domain;
                    document.getElementById("edit-desc-input").value = server.description || "";
                    document.getElementById("edit-api-input").value = server.statusUrl || "";
                    document.getElementById("edit-modal").classList.remove("hidden");
                });
            }

            // Delete Custom Server (Inline two-step)
            const deleteBtn = document.getElementById("delete-btn");
            if (deleteBtn) {
                let deleteTimeout;
                deleteBtn.addEventListener("click", () => {
                    if (!deleteBtn.classList.contains("confirming")) {
                        deleteBtn.classList.add("confirming");
                        deleteBtn.innerHTML = "⚠️ Confirm Delete";
                        deleteBtn.style.background = "#991b1b";
                        
                        deleteTimeout = setTimeout(() => {
                            deleteBtn.classList.remove("confirming");
                            deleteBtn.innerHTML = "🗑️ Delete";
                            deleteBtn.style.background = "linear-gradient(to bottom, #f87171, #ef4444)";
                        }, 4000);
                    } else {
                        clearTimeout(deleteTimeout);
                        customServers = customServers.filter(s => s.id !== server.id);
                        localStorage.setItem("mcod_custom_servers", JSON.stringify(customServers));
                        showToast(`🗑️ Server "${server.name}" has been deleted.`, "success");
                        refreshAll();
                    }
                });
            }
        }

        function showFormMessage(element, text, type) {
            element.innerHTML = text;
            element.className = `form-message ${type}`;
            element.classList.remove("hidden");
        }

        window.toggleStar = function(id) {
            if (id === "primary") return;

            const idx = favorites.indexOf(id);
            if (idx > -1) {
                favorites.splice(idx, 1);
            } else {
                favorites.push(id);
            }
            
            localStorage.setItem("mcod_favorites", JSON.stringify(favorites));
            renderServers();
            
            // Re-select currently selected server to maintain state
            const list = getMasterList();
            const current = list.find(s => s.id === selectedServerId);
            if (current) selectServer(current.id);
        };

        async function fetchStatus(server) {
            if (!server.statusUrl) {
                statuses[server.id] = { status: "unknown" };
                renderServers();
                return;
            }

            try {
                const res = await fetch(server.statusUrl);
                if (res.ok) {
                    const data = await res.json();
                    statuses[server.id] = { status: data.status, ip: data.ip };
                } else {
                    statuses[server.id] = { status: "TERMINATED" };
                }
            } catch (e) {
                console.error("Status fetch failed for " + server.name, e);
                statuses[server.id] = { status: "TERMINATED" };
            }

            renderServers();

            // If selected, refresh the detail view dynamically too!
            if (selectedServerId === server.id) {
                renderSelectedServerDetails(server);
            }
        }

        function refreshAll() {
            selectedServerId = null;
            detailsPanel.innerHTML = `
                <div class="empty-state">
                    <div style="font-size: 3rem; margin-bottom: 1.5rem; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));">🎮</div>
                    <p style="font-size: 1.05rem; line-height: 1.6; max-width: 280px; margin: 0 auto;">Select a server from the directory list to view connection details, check status, or request whitelist access.</p>
                </div>
            `;
            statuses = {};
            renderServers();

            const list = getMasterList();
            list.forEach(srv => {
                if (srv.statusUrl) {
                    fetchStatus(srv);
                }
            });
        }

        async function triggerJoin(server, passcode = "") {
            const state = statuses[server.id] || {};

            if (server.statusUrl && state.status === "TERMINATED") {
                showToast("⚡ Waking up server on GCP... Please wait ~30 seconds for the VM to boot.", "starting");
                statuses[server.id] = { status: "STARTING" };
                renderServers();
                renderSelectedServerDetails(server);

                try {
                    const res = await fetch(server.statusUrl, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ action: "start", passcode: passcode })
                    });
                    
                    const data = await res.json();
                    
                    if (!res.ok || !data.success) {
                        statuses[server.id] = { status: "TERMINATED" };
                        renderServers();
                        renderSelectedServerDetails(server);
                        showToast(`❌ Wake up failed: ${data.error || "Access Denied."}`, "error");
                        return;
                    }

                    let attempts = 0;
                    const interval = setInterval(async () => {
                        attempts++;
                        try {
                            const pollRes = await fetch(server.statusUrl);
                            if (pollRes.ok) {
                                const pollData = await pollRes.json();
                                statuses[server.id] = { status: pollData.status, ip: pollData.ip };
                                renderServers();

                                if (selectedServerId === server.id) {
                                    renderSelectedServerDetails(server);
                                }

                                if (pollData.status === "RUNNING") {
                                    clearInterval(interval);
                                    showToast("🟢 Server is now ONLINE! Address copied to clipboard.", "success");
                                    copyToClipboard(server.domain);
                                }
                            }
                        } catch (e) {
                            console.error(e);
                        }

                        if (attempts > 15) {
                            clearInterval(interval);
                        }
                    }, 5000);

                } catch (e) {
                    console.error(e);
                    statuses[server.id] = { status: "TERMINATED" };
                    renderServers();
                    renderSelectedServerDetails(server);
                    showToast("❌ Failed to wake up server. Please contact admin.", "error");
                }
            } else {
                copyToClipboard(server.domain);
                showToast("📋 Server Address copied! Paste it in Minecraft multiplayer.", "success");
            }
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text)
                .catch(err => {
                    console.error("Could not copy: ", err);
                });
        }

        function showToast(message, type) {
            globalToast.textContent = message;
            globalToast.className = `dir-alert-toast ${type}`;
            globalToast.classList.remove("hidden");
            
            setTimeout(() => {
                globalToast.classList.add("hidden");
            }, 5000);
        }

        // Initialize!
        setupEventListeners();
        refreshAll();

