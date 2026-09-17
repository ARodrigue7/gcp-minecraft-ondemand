# Deploying GCP Minecraft On-Demand

You are in Google Cloud Shell, so the repository is already cloned and you are already signed in to Google Cloud. Nothing to install.

This walkthrough covers the Cloud Shell specifics. The **[full guide](https://arodrigue7.github.io/gcp-minecraft-ondemand/getting-started.html)** has the detail — what each value is, where to click to get it, DNS options, and troubleshooting.

---

## Step 1: Gather four things

Have these ready before you start. The full guide explains where each one comes from.

| Value | Where |
| :--- | :--- |
| **GCP Project ID** | Cloud Console → project dropdown → copy the **ID**, not the name |
| **DuckDNS domain + token** | [duckdns.org](https://www.duckdns.org/) → sign in → add a subdomain → token is on the same page |
| **Discord webhook URL** | Server Settings → Integrations → Webhooks → New Webhook → Copy URL |
| **Admin passcode** | You invent it — the password for your admin dashboard |

Your project also needs **billing enabled**, or nothing will deploy. That does not mean you get charged: real cost is around $1–2/month, and new accounts get $300 in credit.

---

## Step 2: Point gcloud at your project

Replace `YOUR_PROJECT_ID` with your actual ID:

```bash
gcloud config set project YOUR_PROJECT_ID
```

---

## Step 3: Run the setup wizard

This asks for the four values above, writes `terraform/terraform.tfvars`, and turns on the Google Cloud services the project needs.

```bash
bash scripts/linux/setup.sh
```

Choose **DuckDNS** when it asks for a DNS provider.

---

## Step 4: Deploy

```bash
cd terraform && terraform init
terraform apply
```

Type `yes` when prompted. Takes 3–5 minutes.

If it fails complaining about an API, wait 30 seconds and run `terraform apply` again — Google needs a moment after switching services on.

---

## Step 5: Publish your web pages

Terraform wrote your settings into `docs/js/config.js`. Push it, or the pages will not work:

```bash
cd .. && git add docs/js/config.js
git commit -m "chore: configure frontend endpoints"
git push origin main
```

Then on GitHub: **Settings** → **Pages** → **Deploy from a branch** → `main` → `/docs` → **Save**.

Your site goes live at `https://<your-username>.github.io/<repo-name>/play.html`.

---

## Step 6: Whitelist yourself, then play

**You cannot log into your own admin dashboard yet.** It needs both your passcode *and* your Minecraft username on the approved whitelist — which starts empty. Approve yourself first:

1. Open your `play.html`, submit your Minecraft username under **Whitelist Request**.
2. A card appears in your Discord channel — click **Approve**.
3. Now `admin.html` will let you in.
4. Click **Wake Server**, wait for **ONLINE**, and connect in Minecraft.

---

## Last thing: set a budget alert

Open [Billing → Budgets & alerts](https://console.cloud.google.com/billing/budgets), create a budget for **$9.00**, tick email alerts, finish. Two minutes, and a surprise bill becomes impossible.

---

**Stuck?** The [full guide](https://arodrigue7.github.io/gcp-minecraft-ondemand/getting-started.html) has a troubleshooting table covering every common failure.
