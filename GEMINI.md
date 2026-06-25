# 🛠️ Project Workspace: GCP Minecraft On-Demand
> **System Note:** This file serves as the persistent state, reference manual, and roadmap for our collaborative build. We will modify and append to this file as the architecture evolves.

---

## 🎯 Project Purpose
The goal of this project is to build an event-driven, cost-optimized infrastructure deployment that hosts a containerized Minecraft server on Google Cloud Platform (GCP). 

By leveraging cloud automation, the infrastructure scales to zero compute usage when no players are online and automatically wakes up on-demand when a connection or DNS resolution is initiated. This brings down operational costs to an absolute minimum (~$1.00 - $1.85 / month for ~10 hours of play), making it fully sustainable under standard $10 monthly cloud credit tiers.

This implementation acts as a cloud-native GCP equivalent to established AWS on-demand architectures, specifically targeting the logic popularized by:
* **Reference Architecture:** [doctorray117/minecraft-ondemand](https://github.com/doctorray117/minecraft-ondemand) (AWS ECS Fargate / Route 53 Lambda orchestration).

---

## 📌 Project Meta & Target Specs
* **Target Cloud Platform:** Google Cloud Platform (GCP)
* **Target Engine:** Minecraft Java Edition (Vanilla/Optimized Container)
* **Cost Profile:** Optimized to run entirely within a $10/month credit tier.
* **Repository Status:** Public GitHub-ready (`MIT License`)

---

## 🗺️ Master Roadmap & Status Tracker

### ⬜ Phase 1: Workspace & Repo Scaffolding
* [x] Initialize Git repository with proper `.gitignore` configuration.
* [x] Establish modular folder structure (`/terraform`, `/functions`, `/scripts`).
* [x] Configure local workstation authentication with the `gcloud` CLI.

### ⬜ Phase 2: Infrastructure as Code (Terraform)
* [x] Write provider configuration and backend state declarations.
* [x] Define the `google_compute_disk` resource for persistent game data storage.
* [x] Define the `google_compute_instance` block utilizing a container spec.
* [x] Configure `google_dns_managed_zone` and log-enabled `google_dns_policy`.
* [x] Create the `google_logging_project_sink` to route traffic event alerts.

### ⬜ Phase 3: Automation Logic & Scripting
* [x] Code the Cloud Function `main.py` launcher using the Google API Python client.
* [x] Inject environment variables dynamically from Terraform outputs into the Cloud Function.
* [x] Configure the container environment variables (`AUTOPAUSE=true` / systemd connection watchdog) for automatic idle shutdowns.

### ⬜ Phase 4: Integration, Testing & Security Hardening
* [x] Execute `terraform apply` in an isolated sandbox environment.
* [x] Verify end-to-end event chain (DNS Ping -> Cloud Function -> VM Startup).
* [x] Validate data persistence across clean instance lifecycles.
* [x] Establish a hard Billing Budget alert notification in the GCP console at the $9.00 threshold.

### ⬜ Phase 5: Monitoring & Administration
* [x] Implement public HTTP status endpoint Cloud Function.
* [x] Add dynamic server status badge to GitHub Pages splash site.
* [x] Embed glassmorphic whitelist request form on splash site.
* [x] Document configuration and administration in `README.md`.

### ⬜ Phase 6: Future Enhancements (Backlog)
* [ ] Integrate "Deploy to Google Cloud" button for an automated browser-to-Cloud-Shell deployment wizard.
* [x] Implement bot-abuse prevention (passcode-protected webpage wakeup button + watchdog player check using RCON player count instead of port 25565 TCP count).
* [x] Implement the admin_auth module to validate an admin passcode via a web form.
* [x] Provide an admin interface to run any docker exec mc-send-to-rcon command.
* [x] Fix RCON commands not executing correctly from the admin interface.
* [x] Enforce dual-authentication (whitelisted player AND admin password) for accessing the admin portal and waking up the server.
* [x] Remove all secrets from source code and store them in Secret Manager.
* [x] Create a remote Terraform state backend using Cloud Storage.
* [x] Create a secure whitelist management dashboard on the Player Portal page.
* [x] Create a secure admin portal to view logs, restart server, manage whitelists, etc.
* [x] Implement automatic IP address updates in DNS.
* [x] Remove the 2FA module from the main branch as it is not needed.
* [x] Make the Minecraft server run as a non-root user.
* [x] Fix project landing back button disappearing on `play.html` when a server is selected and the details card expands.
* [x] Prevent the "Join Server" button / double-click from initiating a wakeup request without prompts when the server is offline.

---

### 📋 Phase 6: Architecture Upgrade Blueprint

The blueprint and strategic notes for transitioning to a **Multi-Tenant BYOC SaaS Platform** (Premium Edition) have been extracted to a separate document.

👉 **Read the full blueprint here:** [MULTI_TENANT_SAAS.md](MULTI_TENANT_SAAS.md)

---

## 📋 Active Scratchpad & Architecture Variables
*This section stores configuration structures, log snippets, and variables as we build them out.*

### Proposed Directory Layout
```text
├── .github/workflows/
├── docs/
│   ├── index.html
│   ├── play.html
│   ├── admin.html
│   ├── images/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── config.js
│       ├── play.js
│       └── admin.js
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── functions/
│   ├── main.py
│   ├── config.py
│   ├── gcp_client.py
│   ├── admin_auth.py
│   ├── discord_auth.py
│   ├── discord_webhook.py
│   ├── whitelist_manager.py
│   ├── templates.py
│   └── requirements.txt
├── scripts/
└── README.md
```

### Critical Security Filters (.gitignore)
```plaintext
.terraform/
*.tfstate
*.tfstate.backup
*.json
*.env
```

🔄 Change Log & Active Focus
Current Iteration: Phase 6 - Stateful Whitelisting & Webhook Anti-Spam (GCP Minecraft On-Demand)

Recent Changes:
* Stateful Whitelisting: Added `pending-whitelist` metadata key to Compute Engine instance to securely check player whitelist status (Approved / Pending / Not Whitelisted) directly on the portal page, even when the VM is powered down.
* Webhook Anti-Spam: Cloud Function now blocks duplicate whitelist requests for the same player, preventing Discord webhook spam.
* IAM Permissions: Added `google_service_account_iam_member.cf_sa_user` to grant `roles/iam.serviceAccountUser` role to the Cloud Function service account, allowing it to perform metadata updates on the VM instance.
* Dynamic Frontend: Updated portal Javascript to render dynamic responses directly from the Cloud Function.
* Whitelist Race Condition Resolution: Fixed the GCE metadata update conflict (`412 Supplied fingerprint does not match current metadata fingerprint`) by implementing a unified, atomic metadata transaction function `update_whitelist_state` in the Cloud Function.
* Manual Whitelisting: Successfully whitelisted player `ArodPlayerLocal`, moving them from pending to approved list and queuing the RCON command.

Active Blockers: None!

Immediate Next Step: Prepare the Multi-Tenant BYOC SaaS transition plan (MULTI_TENANT_SAAS.md).

---

## ⚙️ EGC Integration & Active Skills
This project integrates **Everything Gemini Code (EGC)** to standardize AI-guided development workflows. The following skills are active for this workspace and must be loaded by the model:

- **`coding-standards`**:
  - Enforce clean, readable, high-cohesion code. Focus on modularity (high cohesion, low coupling), small files (<800 lines), and naming clarity.
- **`continuous-learning` / `continuous-learning-v2`**:
  - Proactively analyze session history and extract reusable patterns into local instructions. V2 manages automated session checkpoint outputs.
- **`configure-ecc`**:
  - Use EGC configurations to tune the workspace rules.
- **`strategic-compact`**:
  - Keep state representations and plan updates compact to maximize context efficiency.
- **`docker-patterns`**: 
  - Manage containerization settings for the `itzg/minecraft-server` image.
  - Enforce watchdog player count detection using RCON rather than raw port pings.
- **`python-patterns` / `python-testing`**:
  - Enforce clean Google Cloud Client Library usage in `functions/main.py`.
  - Validate Python code using explicit error handling (fail fast) and structure tests around pytest.
- **`deployment-patterns`**:
  - Keep Terraform files modular and use remote backend states safely.
  - Implement dynamic status checkers and security hardening for GCP ingress/egress.
- **`verification-loop`**:
  - Run syntax, build, and test validation scripts immediately after code modifications.
- **`gcloud`**:
  - Enforce explicit command validation (`gcloud help <command>`) before execution to avoid hallucinated flags.
  - Implement data projection, server-side filtering, and resource limits to minimize token usage.
- **`security-review`**:
  - Audit custom HTTP endpoints for signature bypasses, injection attacks, and raw output sanitization.
- **`git-workflow`**:
  - Enforce atomic commits, descriptive messages, and clean branch isolation (e.g. `feature/` prefixes).
- **`seo` & `accessibility`**:
  - Validate meta attributes, semantic layout tags, keyboard focus rings, and screen-reader status indicators in the play hub.
- **`api-design`**:
  - Guarantee robust CORS configurations, appropriate REST response structures, and descriptive HTTP codes for Cloud Functions.