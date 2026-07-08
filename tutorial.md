# Deploying GCP Minecraft On-Demand

Welcome! This interactive guide will walk you through deploying your own cost-optimized, event-driven Minecraft server on Google Cloud Platform (GCP).

By the end of this tutorial, you will have a containerized Minecraft server that automatically shuts down (scales to zero compute usage) when idle and wakes up instantly on-demand when a connection or DNS lookup is initiated.

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

1. **Make the setup script executable:**
   ```bash
   chmod +x scripts/linux/setup.sh
   ```

2. **Run the setup script:**
   ```bash
   ./scripts/linux/setup.sh
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

To route server wake-up connection pings directly to GCP Cloud DNS, you need to point your registrar's nameservers:

1. Look at the output value `dns_nameservers` printed in your terminal (or run `terraform output dns_nameservers`).
2. Log into your domain registrar (GoDaddy, Namecheap, Route 53, Cloudflare, etc.).
3. Replace the default Nameservers (NS records) for your Minecraft domain delegation (e.g. `mc.yourdomain.com`) with the four Google Cloud NS URLs.

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
