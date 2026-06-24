// State
        let adminPasscode = sessionStorage.getItem("mcod_admin_passcode") || "";
        let adminUsername = sessionStorage.getItem("mcod_admin_username") || "";
        let statusUrl = "";
        let serverDomain = "";
        let pollInterval = null;

        // DOM Elements
        const loginContainer = document.getElementById("login-container");
        const loginForm = document.getElementById("login-form");
        const passcodeInput = document.getElementById("admin-passcode-input");
        const usernameInput = document.getElementById("admin-username-input");
        const loginAlert = document.getElementById("login-alert");

        const adminDashboard = document.getElementById("admin-dashboard");
        const logoutBtn = document.getElementById("logout-btn");
        const tabButtons = document.querySelectorAll(".tab-btn");
        const tabContents = document.querySelectorAll(".tab-content");

        // Info Elements
        const infoProject = document.getElementById("info-project");
        const infoStatus = document.getElementById("info-status");
        const infoIp = document.getElementById("info-ip");

        // Dashboard Tab Elements
        const stateText = document.getElementById("state-text");
        const activePlayersCount = document.getElementById("active-players-count");
        const connectionAddress = document.getElementById("connection-address");
        const onlinePlayersList = document.getElementById("online-players-list");

        // Whitelist Tab Elements
        const addWhitelistForm = document.getElementById("add-whitelist-form");
        const whitelistUserInput = document.getElementById("whitelist-user-input");
        const whitelistTableBody = document.getElementById("whitelist-table-body");

        // Backups Tab Elements
        const backupsListContainer = document.getElementById("backups-list-container");
        const manualBackupBtn = document.getElementById("manual-backup-btn");

        // Logs Tab Elements
        const logsTerminal = document.getElementById("logs-terminal");
        const refreshLogsBtn = document.getElementById("refresh-logs-btn");

        // Console Tab Elements
        const consoleForm = document.getElementById("console-form");
        const consoleCommandInput = document.getElementById("console-command-input");
        const consoleOutput = document.getElementById("console-output");

        const globalToast = document.getElementById("global-toast");

        // Initialize Config
        function initConfig() {
            if (window.serverConfig && window.serverConfig.statusUrl) {
                statusUrl = window.serverConfig.statusUrl;
                serverDomain = window.serverConfig.domainName;
            } else {
                statusUrl = localStorage.getItem("mcod_status_url") || "";
                serverDomain = localStorage.getItem("mcod_domain_name") || "";
            }

            if (!statusUrl) {
                showToast("❌ Status API URL is not configured. Please use URL parameters or configuration.", "error");
            } else {
                const match = statusUrl.match(/https:\/\/[^-]+-([^.]+)\./);
                if (match && match[1]) {
                    infoProject.textContent = match[1];
                }
            }
        }

        // Initialize App
        function init() {
            initConfig();
            
            if (adminPasscode && adminUsername) {
                verifyAndShowDashboard(adminPasscode, adminUsername);
            } else {
                loginContainer.classList.remove("hidden");
            }

            tabButtons.forEach(btn => {
                btn.addEventListener("click", () => {
                    tabButtons.forEach(b => b.classList.remove("active"));
                    tabContents.forEach(c => c.classList.add("hidden"));

                    btn.classList.add("active");
                    const targetId = btn.getAttribute("data-tab");
                    document.getElementById(targetId).classList.remove("hidden");

                    if (targetId === "logs-tab") {
                        loadLogs();
                    }
                });
            });

            loginForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const username = usernameInput.value.trim();
                const passcode = passcodeInput.value.trim();
                verifyAndShowDashboard(passcode, username);
            });

            logoutBtn.addEventListener("click", () => {
                sessionStorage.removeItem("mcod_admin_passcode");
                sessionStorage.removeItem("mcod_admin_username");
                adminPasscode = "";
                adminUsername = "";
                adminDashboard.classList.add("hidden");
                loginContainer.classList.remove("hidden");
                if (pollInterval) clearInterval(pollInterval);
            });

            addWhitelistForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const username = whitelistUserInput.value.trim();
                if (!username) return;

                const usernameRegex = /^[a-zA-Z0-9_]{3,16}$/;
                if (!usernameRegex.test(username)) {
                    showToast("❌ Username must be 3-16 alphanumeric chars.", "error");
                    return;
                }

                showToast(`⏳ Adding player '${username}' to whitelist...`, "starting");
                whitelistUserInput.value = "";
                
                try {
                    const res = await fetch(`${statusUrl}?action=admin_whitelist_add`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${adminPasscode}`,
                            "X-Admin-User": adminUsername
                        },
                        body: JSON.stringify({ username })
                    });
                    
                    if (res.ok) {
                        showToast(`✓ Player '${username}' added to whitelist.`, "success");
                        loadDashboardData();
                    } else {
                        const data = await res.json();
                        throw new Error(data.error || "Failed to add player.");
                    }
                } catch (err) {
                    showToast(`❌ Failed to add player: ${err.message}`, "error");
                }
            });

            manualBackupBtn.addEventListener("click", async () => {
                manualBackupBtn.disabled = true;
                showToast("⚡ Enqueueing manual world backup sequence...", "starting");
                try {
                    const success = await sendAdminCommand("backup");
                    if (success) {
                        showToast("✓ Backup enqueued! Upload will start on the VM shortly.", "success");
                    }
                } catch (e) {
                    showToast(`❌ Backup failed: ${e.message}`, "error");
                } finally {
                    manualBackupBtn.disabled = false;
                }
            });

            // VM Power Controls
            const vmStartBtn = document.getElementById("vm-start-btn");
            const vmStopBtn = document.getElementById("vm-stop-btn");
            const vmRestartBtn = document.getElementById("vm-restart-btn");

            vmStartBtn.addEventListener("click", () => triggerVmPower("start"));
            vmStopBtn.addEventListener("click", () => {
                if (confirm("Are you sure you want to stop/terminate the Minecraft VM instance?")) {
                    triggerVmPower("stop");
                }
            });
            vmRestartBtn.addEventListener("click", () => {
                if (confirm("Are you sure you want to restart/reboot the Minecraft VM instance?")) {
                    triggerVmPower("restart");
                }
            });

            refreshLogsBtn.addEventListener("click", loadLogs);

            consoleForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                let command = consoleCommandInput.value.trim();
                if (!command) return;

                if (command.startsWith('/')) {
                    command = command.slice(1);
                }

                writeToConsole(`> ${command}`);
                consoleCommandInput.value = "";

                try {
                    const success = await sendAdminCommand(command);
                    if (success) {
                        writeToConsole(`✓ Command enqueued successfully.`);
                    }
                } catch (err) {
                    writeToConsole(`❌ Failed to enqueue command: ${err.message}`);
                }
            });
        }

        async function verifyAndShowDashboard(passcode, username) {
            loginAlert.classList.add("hidden");
            
            try {
                const res = await fetch(`${statusUrl}?action=admin_status`, {
                    headers: { 
                        "Authorization": `Bearer ${passcode}`,
                        "X-Admin-User": username
                    }
                });

                if (res.ok) {
                    adminPasscode = passcode;
                    adminUsername = username;
                    sessionStorage.setItem("mcod_admin_passcode", passcode);
                    sessionStorage.setItem("mcod_admin_username", username);
                    
                    loginContainer.classList.add("hidden");
                    adminDashboard.classList.remove("hidden");
                    
                    loadDashboardData();
                    pollInterval = setInterval(loadDashboardData, 10000);
                } else {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.error || "Invalid admin credentials.");
                }
            } catch (err) {
                console.error(err);
                loginAlert.textContent = `❌ Access Denied: ${err.message}`;
                loginAlert.classList.remove("hidden");
                sessionStorage.removeItem("mcod_admin_passcode");
                sessionStorage.removeItem("mcod_admin_username");
            }
        }

        async function loadDashboardData() {
            if (!adminPasscode || !adminUsername || !statusUrl) return;

            try {
                const res = await fetch(`${statusUrl}?action=admin_status`, {
                    headers: { 
                        "Authorization": `Bearer ${adminPasscode}`,
                        "X-Admin-User": adminUsername
                    }
                });

                if (!res.ok) {
                    if (res.status === 401) {
                        logoutBtn.click();
                        showToast("❌ Admin session expired. Please log in again.", "error");
                        return;
                    }
                    throw new Error("Failed to load status.");
                }

                const data = await res.json();
                
                infoStatus.textContent = data.status;
                infoIp.textContent = data.ip || "None";
                
                stateText.textContent = data.status;
                stateText.className = data.status === 'RUNNING' ? 'status-online' : (['STARTING', 'PROVISIONING', 'STAGING'].includes(data.status) ? 'status-starting' : 'status-offline');
                
                connectionAddress.textContent = data.ip ? `${data.ip} (or ${serverDomain})` : "Server Offline";
                
                const count = data.online_players === 'none' ? 0 : data.online_players.split(',').length;
                activePlayersCount.textContent = count;

                renderOnlinePlayers(data.online_players, data.status);
                renderWhitelist(data.whitelist);
                renderBackups(data.backups);

            } catch (e) {
                console.error(e);
            }
        }

        function renderOnlinePlayers(playersRaw, status) {
            onlinePlayersList.innerHTML = "";
            if (status !== 'RUNNING') {
                onlinePlayersList.innerHTML = `<div class="empty-state">Minecraft server VM is currently offline/stopped.</div>`;
                return;
            }

            if (playersRaw === 'none' || !playersRaw) {
                onlinePlayersList.innerHTML = `<div class="empty-state">No players currently online.</div>`;
                return;
            }

            const players = playersRaw.split(',');
            players.forEach(player => {
                const item = document.createElement("div");
                item.className = "server-row-item";
                item.style.cursor = "default";
                item.innerHTML = `
                    <div class="row-details">
                        <div class="row-name" style="font-size: 1.1rem; color: #fffbeb;">${player}</div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; background: linear-gradient(to bottom, #f59e0b, #d97706); border-color: #b45309;" onclick="triggerPlayerCmd('kick', '${player}')">🥾 Kick</button>
                        <button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; background: linear-gradient(to bottom, #ef4444, #dc2626); border-color: #991b1b;" onclick="triggerPlayerCmd('ban', '${player}')">🔨 Ban</button>
                    </div>
                `;
                onlinePlayersList.appendChild(item);
            });
        }

        function renderWhitelist(whitelist) {
            whitelistTableBody.innerHTML = "";
            if (!whitelist || whitelist.length === 0) {
                whitelistTableBody.innerHTML = `<div class="empty-state" style="padding: 2rem 1rem;">Whitelist is empty.</div>`;
                return;
            }

            whitelist.forEach(player => {
                const item = document.createElement("div");
                item.className = "server-row-item";
                item.style.cursor = "default";
                item.innerHTML = `
                    <div class="row-details">
                        <span class="row-name" style="font-weight: 600;">${player}</span>
                    </div>
                    <button class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; background: linear-gradient(to bottom, #ef4444, #dc2626); border-color: #991b1b;" onclick="removePlayerFromWhitelist('${player}')">❌ Remove</button>
                `;
                whitelistTableBody.appendChild(item);
            });
        }

        function renderBackups(backups) {
            backupsListContainer.innerHTML = "";
            if (!backups || backups.length === 0) {
                backupsListContainer.innerHTML = `<div class="empty-state" style="padding: 2rem 1rem;">No backups found in Google Cloud Storage.</div>`;
                return;
            }

            backups.forEach(b => {
                const date = new Date(b.timeCreated).toLocaleString();
                const sizeMb = (b.size / (1024 * 1024)).toFixed(2);
                
                const downloadUrl = `${statusUrl}?action=admin_download_backup&generation=${b.generation}&passcode=${adminPasscode}&username=${adminUsername}`;

                const item = document.createElement("div");
                item.className = "server-row-item";
                item.style.cursor = "default";
                item.innerHTML = `
                    <div class="row-details">
                        <div class="row-name" style="font-size: 0.9rem; font-family: monospace;">rolling_backup (Gen: ${b.generation})</div>
                        <div class="row-motd" style="font-size: 0.8rem;">Size: ${sizeMb} MB | Created: ${date}</div>
                    </div>
                    <a href="${downloadUrl}" class="btn btn-primary" style="padding: 0.4rem 0.8rem; font-size: 0.8rem; text-decoration: none;">📥 Download</a>
                `;
                backupsListContainer.appendChild(item);
            });
        }

        async function loadLogs() {
            if (!adminPasscode || !statusUrl) return;

            logsTerminal.textContent = "Fetching log entries from GCP Cloud Logging...";

            try {
                const res = await fetch(`${statusUrl}?action=admin_logs`, {
                    headers: { 
                        "Authorization": `Bearer ${adminPasscode}`,
                        "X-Admin-User": adminUsername
                    }
                });

                if (res.ok) {
                    const data = await res.json();
                    logsTerminal.textContent = "";
                    if (!data.logs || data.logs.length === 0) {
                        logsTerminal.textContent = "No logs available. Wait for container events to write.";
                        return;
                    }

                    data.logs.forEach(log => {
                        const dateStr = log.timestamp ? `[${new Date(log.timestamp).toLocaleTimeString()}] ` : "";
                        logsTerminal.textContent += `${dateStr}${log.message}\n`;
                    });

                    logsTerminal.scrollTop = logsTerminal.scrollHeight;
                } else {
                    logsTerminal.textContent = "Failed to fetch logs. (Check Cloud Function Logs)";
                }
            } catch (err) {
                logsTerminal.textContent = `Error loading logs: ${err.message}`;
            }
        }

        async function sendAdminCommand(cmd) {
            if (!adminPasscode || !statusUrl) return false;

            const res = await fetch(`${statusUrl}?action=admin_command`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${adminPasscode}`,
                    "X-Admin-User": adminUsername
                },
                body: JSON.stringify({ command: cmd })
            });

            if (res.ok) {
                return true;
            } else {
                const data = await res.json();
                throw new Error(data.error || "Failed to execute command.");
            }
        }

        async function triggerVmPower(powerAction) {
            if (!adminPasscode || !statusUrl) return;

            showToast(`⏳ Sending ${powerAction} command to VM...`, "starting");

            try {
                const res = await fetch(`${statusUrl}?action=admin_power`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${adminPasscode}`,
                        "X-Admin-User": adminUsername
                    },
                    body: JSON.stringify({ command: powerAction })
                });

                if (res.ok) {
                    showToast(`✓ VM ${powerAction} request succeeded!`, "success");
                    loadDashboardData();
                } else {
                    const data = await res.json();
                    throw new Error(data.error || "Failed to trigger power action.");
                }
            } catch (err) {
                console.error(err);
                showToast(`❌ VM power action failed: ${err.message}`, "error");
            }
        }

        window.triggerPlayerCmd = async function(action, player) {
            if (!confirm(`Are you sure you want to ${action} player '${player}'?`)) return;

            showToast(`⏳ Enqueueing ${action} command...`, "starting");
            try {
                const success = await sendAdminCommand(`${action} ${player}`);
                if (success) {
                    showToast(`✓ Player '${player}' has been queued for ${action}`, "success");
                    setTimeout(loadDashboardData, 2000);
                }
            } catch (e) {
                showToast(`❌ Command failed: ${e.message}`, "error");
            }
        }

        window.removePlayerFromWhitelist = async function(player) {
            if (!confirm(`Are you sure you want to remove player '${player}' from whitelist?`)) return;

            showToast(`⏳ Removing '${player}' from GCE whitelist...`, "starting");
            try {
                const res = await fetch(`${statusUrl}?action=admin_whitelist_remove`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${adminPasscode}`,
                        "X-Admin-User": adminUsername
                    },
                    body: JSON.stringify({ username: player })
                });

                if (res.ok) {
                    showToast(`✓ Player '${player}' removed from whitelist.`, "success");
                    loadDashboardData();
                } else {
                    const data = await res.json();
                    throw new Error(data.error || "Failed to remove player.");
                }
            } catch (e) {
                showToast(`❌ Failed to remove player: ${e.message}`, "error");
            }
        }

        function writeToConsole(message) {
            consoleOutput.textContent += `${message}\n`;
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        }

        function showToast(message, type) {
            globalToast.textContent = message;
            globalToast.className = `dir-alert-toast ${type}`;
            globalToast.classList.remove("hidden");
            
            setTimeout(() => {
                globalToast.classList.add("hidden");
            }, 5000);
        }

        init();