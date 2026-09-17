# Deploying GCP Minecraft On-Demand

This guide takes you from zero to playing on your own Minecraft server hosted on Google Cloud.

The server shuts itself down when nobody is playing and wakes back up on demand, so you pay for compute only while you are actually online — typically **$1.00–$1.85 per month** for 10–20 hours of play.

---

## 📋 Step 1: Before You Start

| What you need | Why | Time |
| :--- | :--- | :--- |
| **Google account** | Access to Google Cloud | have it |
| **GCP project with billing enabled** | Nothing deploys without it | ~5 min |
| **DuckDNS subdomain + token** | The free address players connect to | ~2 min |
| **Discord server + webhook URL** | Whitelist approval cards get posted here | ~3 min |
| **GitHub account** | Hosts the player and admin pages for free | have it |
| **Your Minecraft username** | You whitelist yourself first | have it |

> [!NOTE]
> **Billing enabled is not the same as being charged.** Google requires a billing account before it will create resources. Between the always-free tier and this project's scale-to-zero design, real cost lands around a dollar or two a month. New accounts also get $300 in free credit. Step 8 sets up a budget alert so there are no surprises.

---

## 🔑 Step 2: Get Your Values

Gather these four things before running the setup wizard. This is where to click for each.

| Value | Where to get it | Example |
| :--- | :--- | :--- |
| **GCP Project ID** | [Google Cloud Console](https://console.cloud.google.com/) → project dropdown in the top bar → copy the **ID**, not the display name. They are usually different. | `minecraft-prod-412204` |
| **DuckDNS domain + token** | [duckdns.org](https://www.duckdns.org/) → sign in with Google → type a name under "sub domains" → **add domain**. Your address is `<name>.duckdns.org`. The **token** is at the top of the same page. | `myserver.duckdns.org`<br>`a1b2c3d4-e5f6-...` |
| **Discord webhook URL** | Discord → your server → **Server Settings** → **Integrations** → **Webhooks** → **New Webhook** → **Copy Webhook URL** | `https://discord.com/api/webhooks/...` |
| **Admin passcode** | You make this up. It is the password for your admin dashboard. | `MySecretPass123!` |

---

## 📥 Step 3: Set Up Your Environment

<div class="deploy-method-selector mt-4 border border-white/10 p-4 rounded bg-surface-container/20 mb-6">
<label class="block text-xs uppercase tracking-widest text-on-surface-variant mb-2">Select your deployment method:</label>
<div class="flex flex-wrap gap-2 mb-4">
<button id="deploy-btn-cloudshell" class="deploy-tab-btn active px-3 py-1.5 text-xs border border-primary text-primary font-bold uppercase transition-all duration-200 bg-primary/5" onclick="showDeployMethod('cloudshell')">Google Cloud Shell (Recommended)</button>
<button id="deploy-btn-local" class="deploy-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDeployMethod('local')">Local Workstation</button>
</div>

<!-- Cloud Shell -->
<div id="deploy-instructions-cloudshell" class="deploy-instruct-pane space-y-4">
<p class="text-sm text-on-surface/90">Cloud Shell is a free browser terminal from Google. Git, Terraform and the gcloud CLI are already installed, you are already signed in, and the repository is already cloned. Nothing to install.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li><strong>Point gcloud at your project</strong> — replace <code>YOUR_PROJECT_ID</code> with the ID from Step 2:
<pre><code class="language-bash">gcloud config set project YOUR_PROJECT_ID</code></pre>
</li>
<li>Go to Step 4. The wizard turns on every Google Cloud service this needs.</li>
</ol>
</div>

<!-- Local Workstation -->
<div id="deploy-instructions-local" class="deploy-instruct-pane space-y-4 hidden">
<p class="text-sm text-on-surface/90">Running from your own machine needs Git, Terraform and the Google Cloud CLI installed first.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li><strong>Clone the repository:</strong>
<pre><code class="language-bash">git clone https://github.com/ARodrigue7/gcp-minecraft-ondemand.git
cd gcp-minecraft-ondemand</code></pre>
</li>
<li><strong>Sign in:</strong>
<pre><code class="language-bash">gcloud auth login</code></pre>
</li>
<li><strong>Sign in again, for Terraform</strong> — this is a separate credential and it is easy to skip:
<pre><code class="language-bash">gcloud auth application-default login</code></pre>
</li>
<li><strong>Point gcloud at your project:</strong>
<pre><code class="language-bash">gcloud config set project YOUR_PROJECT_ID</code></pre>
</li>
<li>Go to Step 4.</li>
</ol>
</div>
</div>

---

## ⚙️ Step 4: Run the Setup Wizard

The wizard checks your tools, asks for the four values from Step 2, writes `terraform/terraform.tfvars`, and turns on the Google Cloud services this project needs.

* **Cloud Shell, macOS or Linux:**
  ```bash
  bash scripts/linux/setup.sh
  ```

* **Windows (PowerShell):**
  ```powershell
  .\scripts\windows\setup.ps1
  ```

What it will ask you, in order:

1. **GCP Project ID** — paste it
2. **Minecraft domain** — your full DuckDNS address, e.g. `myserver.duckdns.org`
3. **DNS provider** — choose **DuckDNS**
4. **DuckDNS token** — paste it
5. **Admin passcode** — the password you invented
6. **Discord webhook URL** — paste it

---

## 🚀 Step 5: Deploy

```bash
cd terraform && terraform init
terraform apply
```

Review what it plans to create, type **`yes`**, and press Enter.

> [!TIP]
> This takes about 3–5 minutes. When it finishes, Terraform prints your `status_function_url` and writes your settings into `docs/js/config.js`.
>
> **If the first run fails complaining about an API,** wait 30 seconds and run `terraform apply` again. Google sometimes needs a moment after switching services on.

---

## 🌐 Step 6: Finish DNS Setup

<div class="dns-selector mt-4 border border-white/10 p-4 rounded bg-surface-container/20">
<label class="block text-xs uppercase tracking-widest text-on-surface-variant mb-2">Select your DNS Provider:</label>
<div class="flex flex-wrap gap-2 mb-4">
<button id="dns-btn-duckdns" class="dns-tab-btn active px-3 py-1.5 text-xs border border-primary text-primary font-bold uppercase transition-all duration-200 bg-primary/5" onclick="showDnsInstructions('duckdns')">DuckDNS (Free, Recommended)</button>
<button id="dns-btn-dynu" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('dynu')">Dynu (Free)</button>
<button id="dns-btn-google" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('google')">Google DNS</button>
<button id="dns-btn-cloudflare" class="dns-tab-btn px-3 py-1.5 text-xs border border-white/10 text-on-surface-variant uppercase transition-all duration-200" onclick="showDnsInstructions('cloudflare')">Cloudflare</button>
</div>

<!-- DuckDNS -->
<div id="dns-instructions-duckdns" class="dns-instruct-pane space-y-4">
<p><strong>Nothing to do here.</strong> You already gave the wizard your DuckDNS subdomain and token. Every time the server boots it tells DuckDNS its new address automatically.</p>
<p class="text-sm text-on-surface-variant">One trade-off worth knowing: free DNS providers cannot tell Google Cloud when somebody looks up your address, so the server will not wake up just because a player pings it in their server list. Use the <strong>Wake Server</strong> button on your player page instead. If you would rather have automatic wake-up, see the Google DNS tab.</p>
</div>

<!-- Dynu -->
<div id="dns-instructions-dynu" class="dns-instruct-pane space-y-4 hidden">
<p>Dynu is another free option (e.g. <code>yourname.dynu.com</code>). Same trade-off as DuckDNS — no automatic wake-up.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Register free at <a href="https://www.dynu.com" target="_blank" class="text-primary underline">Dynu.com</a> and add a DDNS domain.</li>
<li>Copy your API token or update password.</li>
<li>Choose <code>dynu</code> in the wizard and paste them in.</li>
<li>The server updates its address with Dynu on every boot.</li>
</ol>
</div>

<!-- Google DNS -->
<div id="dns-instructions-google" class="dns-instruct-pane space-y-4 hidden">
<p>Requires a domain you already own, and is the only option that wakes the server automatically when a player pings it. This is the fiddliest step in the whole guide.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>Find the <code>dns_nameservers</code> block that <code>terraform apply</code> printed.</li>
<li>Log into your domain registrar (GoDaddy, Namecheap, etc.).</li>
<li>Add four separate <strong>NS records</strong>:
<ul class="list-disc pl-5 mt-1">
<li><strong>Type:</strong> <code>NS</code></li>
<li><strong>Name/Host:</strong> <code>mc</code> (for <code>mc.yourdomain.com</code>)</li>
<li><strong>Value:</strong> one googledomains.com address per record</li>
</ul>
</li>
</ol>
<p class="text-xs text-on-surface-variant">If your registrar rejects an address ending in a dot, delete the trailing dot.</p>
</div>

<!-- Cloudflare -->
<div id="dns-instructions-cloudflare" class="dns-instruct-pane space-y-4 hidden">
<p>Keeps DNS in Cloudflare, updated over their API on each boot. No automatic wake-up.</p>
<ol class="list-decimal pl-5 space-y-2 text-sm text-on-surface/90">
<li>In the Cloudflare dashboard, select your domain and copy the <strong>Zone ID</strong>.</li>
<li>Create an <strong>API Token</strong> under My Profile → API Tokens, using the "Edit zone DNS" template.</li>
<li>Choose <code>cloudflare</code> in the wizard and paste both in.</li>
</ol>
</div>
</div>

---

## 🎨 Step 7: Publish Your Web Pages

Your server comes with a player page (`play.html`) and an admin dashboard (`admin.html`). GitHub Pages hosts them for free.

1. **Commit the config Terraform generated** — the pages will not work without it:
   ```bash
   git add docs/js/config.js
   git commit -m "chore: configure frontend endpoints"
   git push origin main
   ```
2. On GitHub: **Settings** → **Pages** → **Source: Deploy from a branch** → branch **`main`**, folder **`/docs`** → **Save**.
3. After a minute or two your site is live at
   `https://<your-username>.github.io/<repo-name>/play.html`

---

## 🎮 Step 8: Whitelist Yourself, Then Play

> [!IMPORTANT]
> **You cannot log into your own admin dashboard yet.** It checks two things: the admin passcode *and* that your Minecraft username is on the approved whitelist. The whitelist starts empty — so you have to approve yourself through Discord first. This trips up almost everyone.

1. **Ask for access.** Open your `play.html`, find **Whitelist Request**, enter your Minecraft Java Edition username, submit.
2. **Approve yourself.** A card appears in your Discord channel. Click **Approve**.
3. **Log in.** Go to `admin.html`, enter your passcode and that same username. You now have logs, backups, server type, machine size and the mods manager.
4. **Wake the server and connect.** Click **Wake Server**. First boot takes 2–3 minutes. When the badge says **ONLINE**, open Minecraft Java Edition and connect to your address.

---

## 💰 Step 9: Set a Budget Alert

Two minutes of work so a surprise bill is impossible.

1. Open [Billing → Budgets & alerts](https://console.cloud.google.com/billing/budgets).
2. **Create Budget**, set the amount to **$9.00**.
3. Tick **Email alerts to billing account admins**.
4. **Finish**.

---

## 🛠️ Troubleshooting

| What you see | Why | Fix |
| :--- | :--- | :--- |
| `Error 403: ... API has not been used` | A Google Cloud service is still switching on. | Wait 30 seconds, run `terraform apply` again. |
| `Billing account not found` | The project has no billing account linked. | Console → **Billing** → **Manage billing accounts** → link your project. |
| Admin portal says **Unauthorized**, passcode is right | Your username is not whitelisted yet. | Do Step 8 — request on `play.html`, approve in Discord. |
| Player page is blank or buttons do nothing | `docs/js/config.js` was never pushed. | Check it has your `statusUrl`, commit it, push to `main`. |
| Server does not wake when pinged in Minecraft | Free DNS providers cannot trigger wake-up. | Expected. Use the **Wake Server** button, or switch to Google DNS. |
| First `terraform apply` fails, second works | Permissions take 15–30 seconds to propagate. | Wait, re-run. Nothing is wrong. |
| Portal says **Running** but Minecraft says "Connection refused" | The server is still starting up. | 60–90 seconds for vanilla, 2–3 minutes for a modpack. |
