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
* [ ] Initialize Git repository with proper `.gitignore` configuration.
* [ ] Establish modular folder structure (`/terraform`, `/functions`, `/scripts`).
* [ ] Configure local workstation authentication with the `gcloud` CLI.
* [x] Initialize Git repository with proper `.gitignore` configuration.
* [x] Establish modular folder structure (`/terraform`, `/functions`, `/scripts`).
* [x] Configure local workstation authentication with the `gcloud` CLI.

### ⬜ Phase 2: Infrastructure as Code (Terraform)
* [ ] Write provider configuration and backend state declarations.
* [x] Write provider configuration and backend state declarations.
* [ ] Define the `google_compute_disk` resource for persistent game data storage.
* [ ] Define the `google_compute_instance` block utilizing a container spec.
* [ ] Configure `google_dns_managed_zone` and log-enabled `google_dns_policy`.
* [ ] Create the `google_logging_project_sink` to route traffic event alerts.

### ⬜ Phase 3: Automation Logic & Scripting
* [ ] Code the Cloud Function `main.py` launcher using the Google API Python client.
* [ ] Inject environment variables dynamically from Terraform outputs into the Cloud Function.
* [ ] Configure the container environment variables (`AUTOPAUSE=true`) for automatic idle shutdowns.

### ⬜ Phase 4: Integration, Testing & Security Hardening
* [ ] Execute `terraform apply` in an isolated sandbox environment.
* [ ] Verify end-to-end event chain (DNS Ping -> Cloud Function -> VM Startup).
* [ ] Validate data persistence across clean instance lifecycles.
* [ ] Establish a hard Billing Budget alert notification in the GCP console at the $9.00 threshold.

---

## 📋 Active Scratchpad & Architecture Variables
*This section will store configuration structures, log snippets, and variables as we build them out.*

### Proposed Directory Layout
```text
├── .github/workflows/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── functions/
│   ├── main.py
│   └── requirements.txt
├── scripts/
└── README.md
Critical Security Filters (.gitignore)
Plaintext
.terraform/
*.tfstate
*.tfstate.backup
*.json
*.env
🔄 Change Log & Active Focus
Current Iteration: Kickoff & Scaffolding.
Current Iteration: Phase 2 - Provider & Variables.

Active Blockers: None.

Immediate Next Step: Define the exact folder scaffolding locally and draft the base Terraform provider file.
Immediate Next Step: Define the persistent disk and VM instance resources.