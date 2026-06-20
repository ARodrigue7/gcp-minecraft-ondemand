# 🚀 Bring Your Own Cloud (BYOC) SaaS Platform Architecture

Transitioning the isolated, single-tenant GameOps platform from a private, single-token proof-of-concept into a public, secure, multi-tenant **"Bring Your Own Cloud" (BYOC)** SaaS platform.

## 🔄 Dual-Track Evolution Strategy

To maximize utility for both the open-source community and casual users, the project is structured into two paths:

1. **Standard Edition (DIY / Open Source)**:
   - **Target Audience:** Tech-savvy developers who want to self-host.
   - **Architecture:** Single-tenant, decentralized. Users clone the repository, run Terraform to spin up their own GCP resources, and host the client-side files directly on GitHub Pages.
   - **Focus:** Cost-efficiency (scale-to-zero), complete privacy, and full ownership of computing resources.

2. **Premium Edition (SaaS / Managed)**:
   - **Target Audience:** General users, server administrators, and groups desiring managed hosting without setting up GCP manually.
   - **Architecture:** Centralized SaaS with a global API Gateway (Cloud Run), a multi-tenant database (Supabase), secure vaulting of user-supplied GCP credentials, and templates for dynamic multi-game deployments.
   - **Focus:** No-code setup, cryptographic security, multi-game support (e.g., Minecraft, Valheim, Terraria), and advanced admin agent integration.

## 💡 Strategic Implementation Notes

*   **Unified Core Architecture:** To avoid maintaining separate codebases, the Core Engine (Terraform modules and Cloud Functions) should remain universal. The Premium Edition will act as a higher-level orchestration layer that programmatically executes these core scripts on behalf of the user, rather than recreating them from scratch.
*   **UI/UX Differentiation:** The DIY edition will retain a lightweight, statically hosted frontend (e.g., GitHub Pages). The Premium SaaS will require a robust web application (e.g., Next.js) for handling user authentication, billing, template selections, and real-time state visualization.
*   **BYOC Security Constraints:** As users provide their own GCP Service Account keys, we must enforce a strict **Least Privilege** model. We will provide users with a specialized script to generate a Service Account with *only* the minimum required roles.
*   **Branding:** Consider establishing a cohesive, overarching brand name for the platform (e.g., *GameOps*, *CloudCrafter*, or *NodeWake*) as it evolves beyond Minecraft into a universal game hosting hub.

---

## 🛠️ Architecture Upgrades (Premium Edition)

```
       [ Public Frontend Web App ]
                    │
                    ▼
       [ Central API Gateway Layer ]
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  [ Supabase DB ]      [ Cloud Run Workers ]
 (Vaulted Secrets)     (Dynamic Provisioning)
        │                       │
        ▼                       ▼
   (Decrypt SA Keys)    (Ephemeral GCP Clients)
        └───────────┬───────────┘
                    ▼
      [ User's Google Cloud Project ]
         (Spot Compute Engine VM)
```

## ⚙️ Detailed Technical Specifications (Premium Edition)

### 1. Multi-Tenant Credentials Vaulting (Supabase & Crypto)
* **Goal:** Safely store external user GCP service account keys.
* **Technical Spec:** Encrypt user service account JSON keys using AES-256-GCM via a master key managed in GCP Secret Manager before saving them to the Supabase database.

### 2. Transient IAM Token Authorization (Cloud Run Workers)
* **Goal:** Execute deployment tasks in user-owned GCP projects without persisting long-lived credentials.
* **Technical Spec:** When a user triggers an action (start/stop/deploy), the Cloud Run API Gateway retrieves the encrypted service account key, decrypts it in-memory, generates short-lived OAuth2 access tokens, initializes the ephemeral GCP compute client with those transient tokens, and executes the deployment context. **Tokens must never be cached or logged.**

### 3. Parameterized Game Engine (Universal Initialization metadata)
* **Goal:** Abstract container configurations to support multi-game deployment beyond Minecraft.
* **Technical Spec:**
  - Define a strict validation schema for server definitions:
    ```json
    {
      "server_id": "string",
      "game_type": "minecraft | valheim | terraria",
      "hardware_profile": "e2-standard-2 | n2-custom",
      "gcs_backup_bucket": "string"
    }
    ```
  - Update the GCP Compute engine instance-creation metadata scripts to read the parameters dynamically, pull the corresponding optimized Docker image (e.g., `itzg/minecraft-server` or `linuxgsm`), and mount the isolated storage bucket path.

### 4. Decentralized State & Metric Tracking
* **Goal:** Eliminate local storage dependency by routing metrics back to the central data node.
* **Technical Spec:**
  - Build a lightweight, secure telemetry webhook endpoint (`POST /api/v1/telemetry/heartbeat`).
  - The running Spot VM script must periodically execute a background cron-job querying player activity, sending the status to the central API gateway to manage state visibility, billing metrics, and the auto-shutdown logic.

## 🚦 Definition of Done (DoD)
* [ ] Database tables schema for encrypted multi-tenant mapping defined and migrated.
* [ ] Zero hardcoded GCP configurations remain inside the orchestration graph code.
* [ ] End-to-end integration test passes: Simulating User B initiating a command results in zero trace or crossover visibility with User A's runtime files or logs.
* [ ] `agents-cli eval run` runs successfully against a multi-tenant test matrix.
