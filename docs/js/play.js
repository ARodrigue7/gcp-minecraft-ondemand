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
                    <div class="empty-state text-on-surface-variant font-mono text-center py-6">
                        No servers found.
                    </div>
                `;
                return;
            }

            list.forEach(server => {
                const isSelected = selectedServerId === server.id;
                const isFav = favorites.includes(server.id) || server.id === "primary";
                const state = statuses[server.id] || { status: "checking" };

                let statusBadgeHtml = "";
                let motdText = server.description;

                if (state.status === "checking") {
                    statusBadgeHtml = `<span class="w-3 h-3 bg-on-surface-variant rounded-full animate-pulse"></span>`;
                    motdText = "Checking status...";
                } else if (state.status === "RUNNING") {
                    statusBadgeHtml = `<span class="w-3 h-3 bg-secondary rounded-full"></span>`;
                    motdText = "Online - Click to view connection info";
                } else if (state.status === "TERMINATED") {
                    statusBadgeHtml = `<span class="w-3 h-3 bg-error rounded-full"></span>`;
                    motdText = "Offline - Click to start server";
                } else if (["PROVISIONING", "STAGING", "STARTING"].includes(state.status)) {
                    statusBadgeHtml = `<span class="w-3 h-3 bg-primary rounded-full animate-pulse"></span>`;
                    motdText = "Starting server instance...";
                } else {
                    if (!server.statusUrl) {
                        statusBadgeHtml = `<span class="w-3 h-3 bg-secondary rounded-full"></span>`;
                        motdText = server.description;
                    } else {
                        statusBadgeHtml = `<span class="w-3 h-3 bg-error rounded-full"></span>`;
                        motdText = "Offline";
                    }
                }

                const starText = isFav ? "★" : "☆";
                const starColor = isFav ? "text-gold-accent" : "text-on-surface-variant hover:text-gold-accent";
                
                let badgesHtml = "";
                if (server.id === "primary") {
                    badgesHtml += `<span class="bg-primary text-on-primary-fixed px-2 py-0.5 text-[10px] font-bold uppercase">PRIMARY</span> `;
                }
                if (server.isPrivate) {
                    badgesHtml += `<span class="bg-grass-deep text-secondary px-2 py-0.5 text-[10px] font-bold uppercase border border-secondary">PRIVATE</span> `;
                } else {
                    badgesHtml += `<span class="bg-surface-variant text-on-surface-variant px-2 py-0.5 text-[10px] font-bold uppercase border border-on-surface-variant">PUBLIC</span> `;
                }

                const li = document.createElement("div");
                li.className = isSelected 
                    ? `bg-primary/10 border border-primary/50 p-4 rounded-sm relative group cursor-pointer transition-all hover:bg-primary/15`
                    : `bg-background/60 border border-white/10 p-4 rounded-sm hover:border-primary/40 transition-all cursor-pointer hover:bg-surface-variant/40`;
                
                li.addEventListener("click", (e) => {
                    if (!e.target.closest(".star-btn")) {
                        selectServer(server.id);
                    }
                });
                li.addEventListener("dblclick", (e) => {
                    if (!e.target.closest(".star-btn")) {
                        triggerJoinById(server.id);
                    }
                });

                li.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div class="flex gap-2 items-center">
                            <button type="button" class="star-btn font-bold text-lg focus:outline-none ${starColor}" onclick="event.stopPropagation(); toggleStar('${server.id}')" title="Toggle Favorite">
                                ${starText}
                            </button>
                            <h3 class="font-title-md ${isSelected ? 'text-white' : 'text-on-surface-variant'}">${server.name}</h3>
                        </div>
                        ${statusBadgeHtml}
                    </div>
                    <div class="flex gap-2 mt-2">
                        ${badgesHtml}
                    </div>
                    <p class="text-on-surface-variant text-label-sm mt-2 font-mono ${isSelected ? 'italic' : ''}">${server.domain}</p>
                    <p class="text-xs mt-1 font-bold ${state.status === 'RUNNING' ? 'text-secondary' : 'text-error'}">${motdText}</p>
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
            if (server) {
                const state = statuses[server.id] || {};
                if (state.status === "TERMINATED") {
                    selectServer(server.id);
                } else {
                    triggerJoin(server);
                }
            }
        };

        function renderSelectedServerDetails(server) {
            const state = statuses[server.id] || { status: "checking" };
            const isOffline = state.status === "TERMINATED";
            
            let badgeClass = "bg-error-container/20 text-error border border-error/40 rounded-full";
            let dotClass = "bg-error shadow-[0_0_6px_rgba(255,180,171,0.5)]";
            let badgeText = "OFFLINE";
            if (state.status === "RUNNING") {
                badgeClass = "bg-secondary-container/20 text-secondary border border-secondary/40 rounded-full";
                dotClass = "bg-secondary shadow-[0_0_6px_rgba(163,210,161,0.5)]";
                badgeText = "ONLINE";
            } else if (state.status === "checking") {
                badgeClass = "bg-primary-container/20 text-primary border border-primary/40 rounded-full";
                dotClass = "bg-primary animate-pulse shadow-[0_0_6px_rgba(255,190,112,0.5)]";
                badgeText = "CHECKING...";
            } else if (["PROVISIONING", "STAGING", "STARTING"].includes(state.status)) {
                badgeClass = "bg-primary-container/20 text-primary border border-primary/40 rounded-full";
                dotClass = "bg-primary animate-pulse shadow-[0_0_6px_rgba(255,190,112,0.5)]";
                badgeText = "STARTING...";
            } else if (state.status === "unknown" && !server.statusUrl) {
                badgeClass = "bg-secondary-container/20 text-secondary border border-secondary/40 rounded-full";
                dotClass = "bg-secondary shadow-[0_0_6px_rgba(163,210,161,0.5)]";
                badgeText = "ONLINE";
            }

            let whitelistFormHtml = "";
            if (server.isPrivate) {
                if (server.id === "primary") {
                    whitelistFormHtml = `
                        <div class="mt-10 pt-8 border-t border-white/10">
                            <h3 class="font-headline-lg text-sm text-white uppercase mb-2 tracking-widest">Request Whitelist</h3>
                            <p class="text-on-surface text-[11px] mb-4 opacity-80">Submit your username for manual cloud-identity verification.</p>
                            <form id="whitelist-form" class="flex flex-col sm:flex-row gap-3">
                                <div class="flex-1">
                                    <input class="input-field w-full font-label-lg text-sm rounded-sm" id="mc-username" placeholder="In-game Name..." type="text" required autocomplete="off"/>
                                </div>
                                <button type="submit" id="submit-btn" class="bg-surface-variant hover:bg-surface-bright text-on-surface px-8 py-2.5 rounded-sm border border-white/10 font-label-lg text-xs uppercase tracking-widest transition-all">
                                    <span class="font-label-lg text-xs uppercase tracking-widest">Submit</span>
                                </button>
                            </form>
                            <div id="form-message" class="hidden mt-4 p-4 text-sm font-label-lg border-2"></div>
                        </div>
                    `;
                } else {
                    whitelistFormHtml = `
                        <div class="mt-10 pt-8 border-t border-white/10 text-on-surface text-[11px] opacity-80">
                            🛡️ This server is private. To request whitelisting, please contact the server administrator directly.
                        </div>
                    `;
                }
            } else {
                whitelistFormHtml = `
                    <div class="mt-10 pt-8 border-t border-white/10 text-on-surface text-[11px] opacity-80">
                        🌳 This server is public! Anyone can join immediately. No whitelisting required.
                    </div>
                `;
            }

            let joinBtnText = "Join Server";
            let passcodeBoxHtml = "";
            let joinBtnDisabled = "";
            let mainBtnIcon = "sports_esports";
            if (server.statusUrl && state.status === "TERMINATED") {
                joinBtnText = "Wake Up Cluster";
                mainBtnIcon = "bolt";
                passcodeBoxHtml = `
                    <div class="space-y-4">
                        <div class="space-y-2">
                            <label for="server-username" class="block font-label-lg text-on-surface uppercase text-[10px] tracking-widest opacity-80">Minecraft Username</label>
                            <input class="input-field w-full font-label-lg text-sm rounded-sm" id="server-username" placeholder="e.g. Steve" type="text" autocomplete="off"/>
                        </div>
                        <div class="space-y-2">
                            <label for="server-passcode" class="block font-label-lg text-on-surface uppercase text-[10px] tracking-widest opacity-80">Access Passcode</label>
                            <input class="input-field w-full font-label-lg text-sm rounded-sm" id="server-passcode" placeholder="Enter code..." type="password" autocomplete="off"/>
                        </div>
                    </div>
                `;
            } else if (state.status === "STARTING" || state.status === "PROVISIONING" || state.status === "STAGING") {
                joinBtnText = "Booting up...";
                mainBtnIcon = "hourglass_empty";
                joinBtnDisabled = "disabled";
            }

            let customActionsHtml = "";
            if (server.isCustom) {
                customActionsHtml = `
                    <div class="flex gap-4 mt-6 border-t border-white/10 pt-4">
                        <button type="button" id="edit-btn" class="wood-button px-6 py-2.5 flex-1 flex items-center justify-center gap-2 text-white">
                            <span class="material-symbols-outlined text-sm">edit</span>
                            <span class="font-label-lg text-xs uppercase tracking-widest">Edit Details</span>
                        </button>
                        <button type="button" id="delete-btn" class="px-6 py-2.5 flex-1 flex items-center justify-center gap-2 transition-all duration-100 text-white font-label-lg uppercase bg-red-800 border border-red-950 rounded-sm hover:bg-red-700">
                            <span class="material-symbols-outlined text-base">delete</span>
                            <span class="font-label-lg text-xs uppercase tracking-widest" id="delete-btn-text">Delete</span>
                        </button>
                    </div>
                `;
            }

            // Dynamic Bento Grid Metrics based on Status
            let uptimeVal = "0.0%";
            let uptimeFillWidth = "w-0";
            let activePlayersVal = "0 / 20";
            let activePlayersFillWidth = "w-0";
            let ramVal = "0.0 GB";
            let ramFillWidth = "w-[5%]";

            if (state.status === "RUNNING") {
                uptimeVal = "99.8%";
                uptimeFillWidth = "w-[99%]";
                activePlayersVal = "Active";
                activePlayersFillWidth = "w-[50%]";
                ramVal = "3.2 GB";
                ramFillWidth = "w-[80%]";
            } else if (state.status === "STARTING" || state.status === "PROVISIONING" || state.status === "STAGING") {
                uptimeVal = "Staging...";
                uptimeFillWidth = "w-[30%] animate-pulse";
                activePlayersVal = "Booting";
                activePlayersFillWidth = "w-0";
                ramVal = "Allocating";
                ramFillWidth = "w-[20%] animate-pulse";
            }

            detailsPanel.innerHTML = `
                <div class="stone-card p-6 md:p-8 mb-4">
                    <div class="flex flex-col gap-1.5 mb-8">
                        <h1 class="font-display-lg text-headline-lg text-white uppercase tracking-tighter leading-none">${server.name}</h1>
                        <p class="text-secondary font-mono text-sm tracking-tight flex items-center gap-2">
                            <span class="w-1 h-1 bg-secondary rounded-full"></span>
                            Cluster: main-scale-zero | Cloud: GCP-US-CENTRAL1
                        </p>
                    </div>
                    
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Connection Profile -->
                        <div class="bg-surface/60 p-5 border border-white/5 rounded-sm relative">
                            <div class="flex justify-between items-center border-b border-white/10 pb-3 mb-4">
                                <span class="font-label-lg text-on-surface uppercase text-[10px] tracking-[0.2em] font-bold">CONNECTION PROFILE</span>
                                <div class="flex items-center gap-2 px-3 py-1 ${badgeClass}">
                                    <span class="w-1.5 h-1.5 ${dotClass} rounded-full"></span>
                                    <span class="font-bold text-[10px] tracking-widest">${badgeText}</span>
                                </div>
                            </div>
                            <div class="space-y-3">
                                <label class="block font-label-lg text-on-surface uppercase text-[10px] tracking-widest opacity-80">SERVER IP</label>
                                <div class="flex gap-2">
                                    <input type="text" id="server-ip" class="bg-background/90 flex-1 px-4 py-2.5 border border-grass-lush/40 rounded-sm font-mono text-gold-accent select-all overflow-hidden text-ellipsis text-xs font-bold focus:outline-none" value="${server.domain}" readonly>
                                    <button id="copy-btn" class="bg-surface-variant hover:bg-surface-bright p-2.5 flex items-center justify-center rounded-sm border border-white/10 transition-all">
                                        <span class="material-symbols-outlined text-base" id="copy-icon">content_copy</span>
                                        <span class="hidden" id="copy-text">Copy</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Inputs Section -->
                        ${passcodeBoxHtml || `<div class="flex items-center justify-center bg-surface/40 p-5 border border-dashed border-white/10 text-on-surface-variant font-mono text-center text-xs rounded-sm">No configuration inputs required while server is online.</div>`}
                    </div>
 
                    <div class="mt-8">
                        <button class="wood-button w-full py-4 flex items-center justify-center gap-3 group text-white focus:outline-none" id="main-join-btn" ${joinBtnDisabled}>
                            <span class="material-symbols-outlined text-2xl group-hover:scale-110 transition-transform ${isOffline ? 'opacity-50' : ''}">${mainBtnIcon}</span>
                            <span class="font-display-lg text-title-md uppercase tracking-[0.15em]">${joinBtnText}</span>
                        </button>
                        <p class="text-center text-on-surface text-[11px] mt-4 italic opacity-80 flex items-center justify-center gap-2">
                            <span class="material-symbols-outlined text-xs">info</span>
                            Est. wake: ~45s. GCP Instance autosleeps after 15m idle.
                        </p>
                    </div>
 
                    ${whitelistFormHtml}
                    ${customActionsHtml}
                </div>
 
                <!-- Stats Mini-Bento -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="stone-card p-4 border-t-primary/60">
                        <div class="flex items-center gap-2 text-primary mb-1">
                            <span class="material-symbols-outlined text-base">query_stats</span>
                            <span class="font-label-lg uppercase text-[10px] tracking-[0.2em] font-bold">UPTIME</span>
                        </div>
                        <div class="font-display-lg text-title-md text-white">${uptimeVal}</div>
                        <div class="experience-bar-bg mt-2.5 rounded-full">
                            <div class="experience-bar-fill ${uptimeFillWidth} bg-primary"></div>
                        </div>
                    </div>
                    <div class="stone-card p-4 border-t-secondary/60">
                        <div class="flex items-center gap-2 text-secondary mb-1">
                            <span class="material-symbols-outlined text-base">group</span>
                            <span class="font-label-lg uppercase text-[10px] tracking-[0.2em] font-bold">ACTIVE</span>
                        </div>
                        <div class="font-display-lg text-title-md text-white">${activePlayersVal}</div>
                        <div class="experience-bar-bg mt-2.5 rounded-full">
                            <div class="experience-bar-fill ${activePlayersFillWidth} bg-secondary"></div>
                        </div>
                    </div>
                    <div class="stone-card p-4 border-t-gold-accent/60">
                        <div class="flex items-center gap-2 text-gold-accent mb-1">
                            <span class="material-symbols-outlined text-base">memory</span>
                            <span class="font-label-lg uppercase text-[10px] tracking-[0.2em] font-bold">MEMORY</span>
                        </div>
                        <div class="font-display-lg text-title-md text-white">${ramVal}</div>
                        <div class="experience-bar-bg mt-2.5 rounded-full">
                            <div class="experience-bar-fill ${ramFillWidth} bg-gold-accent"></div>
                        </div>
                    </div>
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
                        copyIcon.textContent = "check";
                        setTimeout(() => {
                            copyText.textContent = "Copy";
                            copyIcon.textContent = "content_copy";
                        }, 2000);
                    });
            });

            mainJoinBtn.addEventListener("click", () => {
                const usernameEl = document.getElementById("server-username");
                const username = usernameEl ? usernameEl.value.trim() : "";
                const passcodeEl = document.getElementById("server-passcode");
                const passcode = passcodeEl ? passcodeEl.value.trim() : "";
                triggerJoin(server, passcode, username);
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
                        document.getElementById("delete-btn-text").innerHTML = "Confirm Delete";
                        deleteBtn.style.background = "#5c0d12";
                        
                        deleteTimeout = setTimeout(() => {
                            deleteBtn.classList.remove("confirming");
                            document.getElementById("delete-btn-text").innerHTML = "Delete";
                            deleteBtn.style.background = "#990000";
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
            if (type === "success") {
                element.className = "mt-4 p-4 text-sm font-label-lg bg-secondary-container text-secondary border-2 border-secondary";
            } else {
                element.className = "mt-4 p-4 text-sm font-label-lg bg-error-container text-error border-2 border-error";
            }
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
                <div class="stone-card p-margin flex flex-col items-center justify-center text-center py-20">
                    <div class="w-16 h-16 bg-surface-container-high pixel-card flex items-center justify-center mb-6">
                        <span class="material-symbols-outlined text-4xl text-primary animate-pulse">sports_esports</span>
                    </div>
                    <p class="font-title-md text-on-surface max-w-sm">
                        Select a server from the directory list to view connection details, check status, or request whitelist access.
                    </p>
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

        async function triggerJoin(server, passcode = "", username = "") {
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
                        body: JSON.stringify({ action: "start", passcode: passcode, username: username })
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



        // Initialize!
        setupEventListeners();
        refreshAll();

