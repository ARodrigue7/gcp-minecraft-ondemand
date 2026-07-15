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

## 📥 Step 0: Clone the Repository

If you are deploying locally, clone the project files to your local workstation and navigate into the project directory:

```bash
# Clone the repository
git clone https://github.com/ARodrigue7/gcp-minecraft-ondemand.git

# Navigate into the project folder
cd gcp-minecraft-ondemand
```

*(Note: If you clicked the "Deploy to Google Cloud" button, Cloud Shell has already cloned and opened this repository for you, so you can skip to Step 1!)*

---

## 🔐 Step 1: Authenticate and Configure Project

First, ensure you are authenticated to Google Cloud and have selected the target project.

1. **Authenticate your CLI session:**
   ```bash
   gcloud auth login
   ```

2. **Set your target GCP Project ID:**
   Replace `YOUR_PROJECT_ID` with your actual GCP project:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Enable GCP Services APIs:**
   Enable the required APIs for Compute Engine, Cloud Functions, KMS, Pub/Sub, and Secret Manager:
   ```bash
   gcloud services enable \
     compute.googleapis.com \
     cloudfunctions.googleapis.com \
     pubsub.googleapis.com \
     dns.googleapis.com \
     secretmanager.googleapis.com \
     cloudbuild.googleapis.com
   ```

---

## ⚙️ Step 2: Configure Environment Variables

We provide an interactive script to configure your nameservers, passcode, and Discord notifications:

* **Mac/Linux:**
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

Follow the prompts. This script automatically generates your secure `terraform/terraform.tfvars` file.

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

1. **Update portal configuration:**
   Open the file `docs/js/config.js` and input your Minecraft domain name and `statusUrl` (use the `function_url` output from Terraform):
   ```javascript
   window.serverConfig = {
     "domainName": "mc.yourdomain.com",
     "statusUrl": "https://<your-cloud-function-url>"
   };
   ```

2. **Host the portal:**
   Deploy the `docs/` folder to GitHub Pages (free and recommended) or upload it to a public GCP Cloud Storage bucket.

---

## 🎉 Deployment Complete!

Congratulations! Your event-driven server is fully set up.
* Players can query the status, request whitelisting, and click **Wake Up Cluster** on your web portal.
* Attempting to connect to the IP `mc.yourdomain.com` in Minecraft will trigger DNS lookup logs, invoking the wakeup function automatically!
