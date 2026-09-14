# Deploying GCP Minecraft On-Demand

Welcome! This interactive guide will walk you from zero to playing on your own cost-optimized, scale-to-zero Minecraft server on Google Cloud Platform (GCP).

Because you opened this in Google Cloud Shell, the repository is already cloned and your session is authenticated to your Google account.

---

## 📋 Section 1: Before You Start

Here is what you need before deploying:

| Item | Why It Is Needed | Typical Time |
| :--- | :--- | :--- |
| **Google Account** | Access to Google Cloud Shell and GCP console | Available |
| **GCP Project with Billing Enabled** | Nothing deploys without a billing account linked | ~3–5 min |
| **DuckDNS Subdomain + Token** | The free address players use to connect | ~2 min |
| **Discord Server + Webhook URL** | Whitelist approval cards are sent here | ~3 min |
| **GitHub Account** | Hosts your player splash page and admin dashboard | Available |
| **Minecraft Username** | You must whitelist yourself to access the portal | Available |

> [!NOTE]
> **Billing Enabled ≠ Being Charged**: GCP requires billing enabled to provision resources. Thanks to scale-to-zero compute and GCP always-free quotas, typical usage costs around **$1.00 – $1.85 / month** (for ~10–20 hours of play), making it fully sustainable under standard credits.

---

## 🔑 Section 2: Get Your Values

Before running the setup wizard, gather these 4 values. Here is where to find each:

| Prompt | Where to Click / How to Get It | Example |
| :--- | :--- | :--- |
| **GCP Project ID** | Go to [Google Cloud Console](https://console.cloud.google.com/), click the project dropdown in the top bar, and copy the **ID** (alphanumeric string, e.g. `mc-servers-412204`), *not* the project name. | `minecraft-prod-412204` |
| **DuckDNS Domain & Token** | Go to [duckdns.org](https://www.duckdns.org/), sign in with Google, enter a subdomain name under "sub domains", click "add domain". Your domain is `<subdomain>.duckdns.org`. Copy your **token** from the top of the page. | Domain: `myserver.duckdns.org`<br>Token: `a1b2c3d4-e5f6-...` |
| **Discord Webhook URL** | Open Discord → Your Server → Server Settings → Integrations → Webhooks → Click **New Webhook** → Name it (e.g. "Minecraft") → Click **Copy Webhook URL**. | `https://discord.com/api/webhooks/...` |
| **Admin Passcode** | Invent a strong, secure password. You will use this along with your whitelisted Minecraft username to log into the web admin portal. | `MySecretPass123!` |

---

## ⚙️ Section 3: Run the Setup Wizard

Run the interactive setup script. It verifies dependencies, checks your GCP authentication, asks for the values you gathered above, generates `terraform/terraform.tfvars`, and automatically enables all 13 required GCP APIs:

```bash
bash scripts/linux/setup.sh
```

### Wizard Prompts Overview:
1. **GCP Project ID**: Paste your Project ID.
2. **Minecraft Domain**: Enter your full DuckDNS domain (e.g., `myserver.duckdns.org`).
3. **DNS Provider**: Select `1` for **DuckDNS** (recommended).
4. **DuckDNS Token**: Paste the token copied from duckdns.org.
5. **Admin Passcode**: Enter your chosen password.
6. **Discord Webhook URL**: Paste your Discord webhook URL.

The script writes your configuration to `terraform/terraform.tfvars` and enables all required Google Cloud APIs (`compute`, `dns`, `cloudfunctions`, `run`, `eventarc`, `storage`, `iam`, `secretmanager`, etc.).

---

## 🚀 Section 4: Deploy Infrastructure (Terraform)

Now deploy the infrastructure to your Google Cloud project:

1. **Initialize Terraform**:
   ```bash
   cd terraform && terraform init
   ```

2. **Deploy the stack**:
   ```bash
   terraform apply
   ```

3. When prompted:
   - Review the planned resources.
   - Type **`yes`** and hit Enter.

> [!TIP]
> The deployment takes approximately **3 to 5 minutes**. Once finished, Terraform will output your `status_function_url` and update `docs/js/config.js` with your deployment endpoints.
> 
> *If the first apply fails with an API propagation warning, wait 30 seconds and simply re-run `terraform apply`.*

---

## 🌐 Section 5: Publish Your Web Pages (GitHub Pages)

Your server includes a splash portal for players (`play.html`) and an admin dashboard (`admin.html`). You can host them for free on GitHub Pages:

1. Push your repository to your GitHub account:
   ```bash
   git add docs/js/config.js
   git commit -m "chore: configure frontend endpoints"
   git push origin main
   ```
2. In your GitHub repository:
   - Go to **Settings** → **Pages** (in the left sidebar).
   - Under **Build and deployment** → **Source**, select **Deploy from a branch**.
   - Under **Branch**, select **`main`** and folder **`/docs`**, then click **Save**.
3. In ~1–2 minutes, your website will be live at:
   `https://<your-github-username>.github.io/<repo-name>/play.html`

---

## 🎮 Section 6: Whitelist Yourself, Then Play!

> [!IMPORTANT]
> **The Admin Portal Dual-Authentication Loop**:
> To prevent unauthorized access, the admin portal requires both your **Admin Passcode** AND that your Minecraft username is on the **approved whitelist**. Because the server starts with an empty whitelist, you must approve yourself first via Discord:

1. **Request Whitelist**:
   - Open your GitHub Pages `play.html` in your browser.
   - Scroll to the **Whitelist Request** section, enter your Minecraft username, and click **Submit Request**.
2. **Approve via Discord**:
   - Open the Discord channel where you set up your webhook.
   - You will see an interactive card with your username. Click the **Approve** link.
3. **Log Into Admin Portal**:
   - Navigate to `admin.html` on your GitHub Pages site.
   - Log in using your **Admin Passcode** and your approved Minecraft username.
   - From here you can view logs, trigger backups, customize machine sizing, and install mods/plugins!
4. **Wake the Server & Connect**:
   - On DuckDNS, automatic DNS query wakeup is not supported by free DDNS providers. Simply click the **Wake Server** button on `play.html` (or in `admin.html`).
   - The VM will boot up and start the Minecraft container (initial boot takes ~2–3 minutes).
   - Once the badge displays **ONLINE**, launch Minecraft Java Edition and connect to your domain (e.g. `myserver.duckdns.org`)!

---

## 💰 Pro-Tip: Set a $9.00 GCP Budget Alert

To guarantee you never receive an unexpected bill:
1. Open [Google Cloud Console Billing Budgets](https://console.cloud.google.com/billing/budgets).
2. Click **Create Budget**.
3. Set the target amount to **$9.00**.
4. Check **Email alerts to billing account admins**.
5. Click **Finish**.

---

## 🛠️ Troubleshooting Guide

| What You See | Root Cause | Solution |
| :--- | :--- | :--- |
| `Error 403: ... API has not been used` | A Google Cloud API was not yet activated or has not finished propagating. | Re-run `bash scripts/linux/setup.sh` or wait 30 seconds and re-run `terraform apply`. |
| `Billing account not found` or `project not linked` | Your GCP Project is not linked to an active billing account. | In the GCP Console, go to **Billing** → **Manage billing accounts** and link your project. |
| Admin portal says **"Unauthorized"** despite typing the correct passcode | Your Minecraft username is not on the approved whitelist. | Go to `play.html`, submit your username, approve it in your Discord channel, and log in again. |
| Player page shows blank status or buttons do nothing | `docs/js/config.js` was not committed or pushed to your GitHub repo. | Verify `docs/js/config.js` contains your `statusUrl`, commit it, and push to your `main` branch. |
| Server does not wake up automatically when pinging in Minecraft | DuckDNS does not support GCP DNS query logging policies. | This is normal for free DDNS. Use the **Wake Server** button on `play.html` or `admin.html`. |
| `terraform apply` fails on first run, succeeds on retry | GCP IAM permissions occasionally take 15–30 seconds to propagate after enabling new services. | Wait 30 seconds and run `terraform apply` again. |
| Portal says **Running**, but Minecraft says "Connection refused" | The VM is up, but the Minecraft container is still downloading world files or generating chunks. | Wait 60–90 seconds for vanilla (or 2–3 minutes for modpacks) and refresh your server list. |
