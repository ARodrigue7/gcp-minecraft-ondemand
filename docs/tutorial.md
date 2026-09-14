# Deploying GCP Minecraft On-Demand

Welcome! This interactive guide will walk you through deploying your own cost-optimized, event-driven Minecraft server on Google Cloud Platform (GCP).

By the end of this tutorial, you will have a containerized Minecraft server that automatically shuts down (scales to zero compute usage) when idle and wakes up instantly on-demand when a connection or DNS lookup is initiated.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following resources ready:

1. **Google Cloud Platform (GCP) Account:**
   * A GCP Project with billing enabled. New accounts get **$300 in free credits**, which is more than enough to host this server for free for several years.
2. **Domain Name:**
   * **Paid Domain options (Recommended):** A custom domain name managed via **Google Cloud DNS** or **Cloudflare** (e.g., `mc.yourdomain.com`).
   * **Free Domain options (DDNS):** A free dynamic DNS subdomain from **DuckDNS** (e.g., `yoursubdomain.duckdns.org`) or **Dynu DNS** (e.g., `yourdomain.dynu.com`).
3. **Discord Account (Optional):**
   * A Discord Webhook URL if you want your server to post status updates and whitelist approval alerts to a Discord channel.

---

## 📥 Step 1: Authenticate and Configure Project

To start, you must select your deployment environment to authorize the session and configure your Google Cloud Platform (GCP) project.

<details class="border border-white/10 p-4 rounded bg-surface-container/20 mt-4 mb-6">
<summary class="cursor-pointer font-bold text-sm text-primary select-none hover:underline">📋 View Configuration Reference Table</summary>
<div class="mt-4">
<p class="text-xs text-on-surface-variant mb-4">Use these examples to guide you on what values to input for the placeholders and prompts:</p>

| Prompt Name | Example Value (Google Cloud DNS - Recommended) | Example Value (Cloudflare / DuckDNS) | Description / Notes |
| :--- | :--- | :--- | :--- |
| **GCP Project ID** | `minecraft-servers-412204` | `my-gcp-sandbox` | Your actual GCP project alphanumeric ID. |
| **Minecraft Domain** | `mc.mycustomdomain.com` | `mycoolserver.duckdns.org` | The domain/subdomain players will connect to. |
| **Cloud DNS Zone** | `mc-mycustomdomain-com` | `mycoolserver-duckdns-org` | Internal GCP name for the zone (automatic default is fine). |
| **Admin Passcode** | `DiamondArmor99!` | `MySecretPass123` | Password used to log into the web admin dashboard. |
| **Discord Webhook URL** | `https://discord.com/api/webhooks/...` | `https://discord.com/api/webhooks/...` | Webhook URL to route whitelist approval cards. |
| **DNS Provider** | `1` (Google Cloud DNS) | `2` (Cloudflare) or `3` (DuckDNS) | Choose the provider managing the target domain. |
| **API Token / Zone ID** | `N/A (Uses secure GCP IAM)` | `a1b2c3d4-e5f6-...` (API key or Zone ID) | Credentials for your dynamic DNS provider. |
</div>
</details>

Select your deployment method below:

<div class="deploy-method-selector mt-4 border border-white/10 p-4 rounded bg-surface-container/20 mb-6">
<label class="block text-xs uppercase tracking-widest text-on-surface-variant mb-2">Select your deployment method:</label>
<div class="flex flex-wrap gap-2 mb-4">
<button id="deploy-btn-cloudshell" class="deploy-tab-btn active px-3 py-1.5 text-xs border border-primary text-primary font-bold uppercase transition-all duration-200 bg-primary/5" onclick="showDeployMethod('cloudshell')">Google Cloud Shell (Recommended)</button>
<button id="deploy-btn-local" class="deploy-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDeployMethod('local')">Local Workstation</button>
</div>

<!-- Cloud Shell -->
<div id="deploy-instructions-cloudshell" class="deploy-instruct-pane space-y-4">
<p class="text-sm text-on-surface/90">Google Cloud Shell is a free, pre-configured browser terminal. All CLI tools (Git, Terraform, gcloud) are already installed and authenticated to your account, and the repository is already cloned.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li><strong>Set your target GCP Project ID:</strong><br>
Replace <code>YOUR_PROJECT_ID</code> with your GCP Project ID:
<pre><code class="language-bash">gcloud config set project YOUR_PROJECT_ID</code></pre>
</li>
<li>Proceed directly to <strong>Step 2: Configure Environment Variables</strong>. The setup wizard automatically enables all required GCP APIs for you.</li>
</ol>
</div>


<!-- Local Workstation -->
<div id="deploy-instructions-local" class="deploy-instruct-pane space-y-4 hidden">
<p class="text-sm text-on-surface/90">Deploying from your local machine (macOS, Linux, or Windows) requires having Git, Terraform, and the Google Cloud CLI installed.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li><strong>Clone the Repository & Navigate:</strong>
<pre><code class="language-bash">git clone https://github.com/ARodrigue7/gcp-minecraft-ondemand.git
cd gcp-minecraft-ondemand</code></pre>
</li>
<li><strong>Authenticate your CLI session:</strong>
<pre><code class="language-bash">gcloud auth login</code></pre>
</li>
<li><strong>Configure Application Default Credentials (for Terraform):</strong>
<pre><code class="language-bash">gcloud auth application-default login</code></pre>
</li>
<li><strong>Set your target GCP Project ID:</strong>
<pre><code class="language-bash">gcloud config set project YOUR_PROJECT_ID</code></pre>
</li>
<li>Proceed to <strong>Step 2: Configure Environment Variables</strong>. The setup wizard will automatically enable all 13 required GCP APIs for your project.</li>
</ol>

</div>
</div>

---

## ⚙️ Step 2: Configure Environment Variables

We provide an interactive script to configure your nameservers, admin passcode, and Discord webhooks:

* **If using Google Cloud Shell or Mac/Linux:**
  ```bash
  # Make the setup script executable
  chmod +x scripts/linux/setup.sh
  # Run the interactive wizard
  ./scripts/linux/setup.sh
  ```

* **Windows (PowerShell):**
  ```powershell
  # Run the interactive wizard
  .\scripts\windows\setup.ps1
  ```

Follow the prompts. The script automatically generates your secure `terraform/terraform.tfvars` file.

---

## 🚀 Step 3: Deploy Infrastructure (Terraform)

With your vars set, we can deploy the stack.

1. **Initialize Terraform:**
   This downloads GCS state backends and required providers:
   ```bash
   cd terraform && terraform init
   ```

2. **Review Deployment Plan:**
   ```bash
   terraform plan
   ```

3. **Deploy stack to Google Cloud:**
   ```bash
   terraform apply
   ```

*Note: The apply process takes around 2-3 minutes. Make sure to keep the URL outputs generated at the end!*

---

## 🌐 Step 4: Delegate Domain Nameservers

To enable the event-driven autostart feature (where playing or pinging your address triggers the VM boot process), you must delegate DNS authority to your configured provider.

Select your provider below to view custom setup steps:

<div class="dns-selector mt-4 border border-white/10 p-4 rounded bg-surface-container/20">
<label class="block text-xs uppercase tracking-widest text-on-surface-variant mb-2">Select your DNS Provider:</label>
<div class="flex flex-wrap gap-2 mb-4">
<button id="dns-btn-google" class="dns-tab-btn active px-3 py-1.5 text-xs border border-primary text-primary font-bold uppercase transition-all duration-200 bg-primary/5" onclick="showDnsInstructions('google')">Google DNS</button>
<button id="dns-btn-cloudflare" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('cloudflare')">Cloudflare</button>
<button id="dns-btn-duckdns" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('duckdns')">DuckDNS (Free)</button>
<button id="dns-btn-dynu" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('dynu')">Dynu (Free)</button>
</div>

<!-- Google DNS -->
<div id="dns-instructions-google" class="dns-instruct-pane space-y-4">
<p>Google Cloud DNS is the default provider. Points your subdomain NS records to the four GCP nameservers generated on deployment.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Find the <code>dns_nameservers</code> output block generated at the end of <code>terraform apply</code>.</li>
<li>Log into your domain registrar (GoDaddy, Namecheap, etc.).</li>
<li>Add four separate <strong>NS Records</strong> in your domain settings:
<ul class="list-disc pl-5 mt-1">
<li><strong>Type:</strong> <code>NS</code></li>
<li><strong>Name/Host:</strong> <code>mc</code> (if you want <code>mc.yourdomain.com</code>)</li>
<li><strong>Value/Target:</strong> Copy one googledomains.com address into each record.</li>
</ul>
</li>
</ol>
<p class="text-xs text-on-surface-variant">Note: If your registrar rejects nameservers with a trailing dot (e.g. <code>.googledomains.com.</code>), simply delete that trailing dot.</p>
</div>

<!-- Cloudflare -->
<div id="dns-instructions-cloudflare" class="dns-instruct-pane space-y-4 hidden">
<p>Uses Cloudflare's API to update records directly. This allows you to manage DNS routing through Cloudflare while the VM boots.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Log into your Cloudflare dashboard, select your domain, and find your <strong>Zone ID</strong>.</li>
<li>Create a Cloudflare <strong>API Token</strong> under User Profile -> API Tokens -> Create Token (select template "Edit zone DNS").</li>
<li>During Step 2 (configuration wizard), select <code>cloudflare</code> and provide your API Token and Zone ID.</li>
<li>Terraform will automatically create and update the target DNS records in your Cloudflare dashboard on every server start!</li>
</ol>
</div>

<!-- DuckDNS -->
<div id="dns-instructions-duckdns" class="dns-instruct-pane space-y-4 hidden">
<p>DuckDNS provides 100% free subdomains (e.g. <code>yoursubdomain.duckdns.org</code>). Ideal for testing and zero-cost hosting.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Visit <a href="https://www.duckdns.org" target="_blank" class="text-primary underline">DuckDNS.org</a> and sign in.</li>
<li>Create a free subdomain. Note your DuckDNS <strong>Token</strong>.</li>
<li>During Step 2 (configuration wizard), select <code>duckdns</code> and enter your subdomain and DuckDNS token.</li>
<li>When the Minecraft instance boots, it automatically calls the DuckDNS API to map your custom subdomain to its current external IP.</li>
</ol>
</div>

<!-- Dynu -->
<div id="dns-instructions-dynu" class="dns-instruct-pane space-y-4 hidden">
<p>Dynu DNS offers free custom subdomains (e.g. <code>yourdomain.dynu.com</code>) with a highly reliable API.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Register a free account on <a href="https://www.dynu.com" target="_blank" class="text-primary underline">Dynu.com</a>.</li>
<li>Add a DDNS service domain name.</li>
<li>Grab your Dynu API credentials (token or update password).</li>
<li>During Step 2 (configuration wizard), select <code>dynu</code> and input your domain and credentials.</li>
<li>The server VM automatically updates its IP in Dynu's directory during startup.</li>
</ol>
</div>
</div>

---

## 🎨 Step 5: Configure and Host Web Portal

Finally, configure the Player Portal and Admin Dashboard:

1. **Automatic configuration:**
   Terraform automatically writes your generated endpoints directly to `docs/js/config.js` upon completion of `terraform apply`.
2. **Host the portal on GitHub Pages:**
   - Commit and push `docs/js/config.js` to your repository's `main` branch.
   - Go to your repository's **Settings** -> **Pages**.
   - Under **Build and deployment**, set Source to **Deploy from a branch**, Branch to **`main`**, and folder to **`/docs`**. Click **Save**.
   - Your web splash page will be live at `https://<your-username>.github.io/<repo-name>/play.html`!

---

## 🎮 Step 6: Whitelist Yourself, Then Play!

> [!IMPORTANT]
> **Admin Portal Access Requirement**: The admin portal enforces dual-factor authentication: it requires both your **Admin Passcode** and that your Minecraft username exists on the **approved whitelist**. Because the server starts with an empty whitelist, you must approve yourself first via Discord:

1. **Submit Whitelist Request:**
   Open your GitHub Pages `play.html`, scroll to **Whitelist Request**, enter your Minecraft Java Edition username, and submit.
2. **Approve in Discord:**
   Open your Discord channel with the configured webhook. An interactive card will appear—click **Approve**.
3. **Log Into Admin Portal:**
   Visit `admin.html` on your GitHub Pages site. Enter your **Admin Passcode** and your approved Minecraft username to access server controls, logs, backups, and the mods/plugins manager.
4. **Wake the Server:**
   Click **Wake Server** on `play.html` or `admin.html`. The VM will boot and launch the Minecraft container (~2–3 minutes for initial setup). Once the badge indicates **ONLINE**, connect in Minecraft Java Edition!

---

## 🛠️ Troubleshooting

| Issue / Error Message | Root Cause | Solution |
| :--- | :--- | :--- |
| `Error 403: ... API has not been used` | A required GCP API has not finished activating. | Wait 30 seconds and re-run `terraform apply`, or run `./scripts/linux/setup.sh`. |
| `Billing account not found` | Your GCP project lacks an active billing link. | In GCP Console, link an active billing account under **Billing** -> **Manage billing accounts**. |
| Admin portal says **Unauthorized** with correct password | Your Minecraft username is not yet on the approved whitelist. | Request access on `play.html` and approve the card in your Discord channel (Step 6). |
| Player page shows blank status or buttons do nothing | `docs/js/config.js` was not pushed to your GitHub repo. | Commit `docs/js/config.js` and push to your `main` branch. |
| Server won't wake on DuckDNS | Free DDNS providers do not support GCP DNS query policies. | Normal for free DDNS; use the **Wake Server** button on `play.html` or `admin.html`. |
| First `terraform apply` fails | GCP IAM permissions occasionally take 15–30s to propagate. | Wait 30 seconds and run `terraform apply` again. |
| Portal says **Running** but Minecraft says "Connection refused" | The Minecraft server container is still loading chunks or downloading assets. | Wait 60–90 seconds for vanilla (or 2–3 minutes for modpacks) and refresh server list. |

