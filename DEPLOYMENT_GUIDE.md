# TraffiTwin AI: Deployment Guide

This guide provides step-by-step instructions to deploy the **TraffiTwin AI** backend to **Hugging Face Spaces** (Docker-based, free tier) and the frontend to **Google Firebase Hosting** (Spark plan, free tier). 

No credit card or billing accounts are required for this deployment.

---

## Part 1: Deploy Backend to Hugging Face Spaces

Hugging Face Spaces allows you to run free Docker containers. It automatically secures your app with HTTPS and handles SSL certificates.

### 1. Create a Hugging Face Space
1. Sign in or register at [Hugging Face](https://huggingface.co/).
2. Click on your profile image in the top-right corner and select **New Space**.
3. Configure the Space:
   *   **Space Name:** `traffitwin-backend` (or a name of your choice)
   *   **License:** `mit`
   *   **SDK:** Select **Docker** (very important).
   *   **Docker Template:** Select **Blank** (default).
   *   **Space Hardware:** Select **CPU basic • 2 vCPU • 16 GB • Free** (default).
   *   **Visibility:** **Public** (so the frontend can reach the API).
4. Click **Create Space**.

### 2. Provision a Postgres database
The backend persists incident summaries to Postgres, so you need a reachable
database before the app can start in production. Any managed Postgres works
(e.g. [Neon](https://neon.tech) or [Supabase](https://supabase.com) both have
a free tier suitable for this deployment) — HF Spaces itself does not provide
a database service.

1. Create a Postgres instance with your provider of choice.
2. Copy its connection string and rewrite it to use the `asyncpg` driver, e.g.:
   `postgresql+asyncpg://<user>:<password>@<host>:5432/<database>`

### 3. Configure Environment Secrets
1. In your newly created Space, click on the **Settings** tab.
2. Scroll down to the **Variables and secrets** section.
3. Click **New secret** and add each of the following:

   | Name | Value |
   |---|---|
   | `GEMINI_API_KEY` | Your Google Gemini API Key from Google AI Studio |
   | `DATABASE_URL` | The `asyncpg` connection string from step 2 |
   | `JWT_SECRET_KEY` | A real random secret, e.g. `openssl rand -hex 32` — production refuses to start with the insecure dev default |
   | `GOOGLE_OAUTH_CLIENT_ID` | An OAuth 2.0 Client ID from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials), used to verify Google Sign-In tokens server-side |

See `docs/SECRETS.md` for why each of these is required — `ENVIRONMENT=production`
(the default in the Docker image) refuses to start if any is missing or left
at its insecure default.

### 4. Apply database migrations
Before the app can serve requests against the new database, run the schema
migrations against it:
```bash
DATABASE_URL=<your production connection string> alembic upgrade head
```
This is never run automatically at app startup (see `docs/SECRETS.md`) —
run it once manually here, and again after any future schema change.

### 5. Push Code to Hugging Face
Hugging Face Spaces act as a Git remote. You can push your code directly to it.
1. Run these commands from the root of your local `TraffiTwin-AI` repository:
   ```bash
   # Add Hugging Face as a git remote
   # Replace <username> and <space-name> with your Hugging Face details
   git remote add hf https://huggingface.co/spaces/<username>/<space-name>

   # Push the main branch to Hugging Face
   # Note: You may be prompted for your Hugging Face username and password/access token
   git push -f hf main
   ```
2. Go back to the Hugging Face Space page and click the **App** tab to monitor the build. Hugging Face will read the root `Dockerfile`, build the image, and deploy it.
3. Once running, your API URL will be:
   `https://<username>-<space-name>.hf.space` (e.g., `https://sahilmangla-traffitwin-backend.hf.space`)

---

## Part 2: Configure and Build Frontend

Now we will configure the React frontend to communicate with your live Hugging Face backend API.

### 1. Configure production endpoint
Create a `.env.production` file inside the `frontend/` directory and configure the API endpoint pointing to your Hugging Face space, along with the Google OAuth Client ID used for the Sign-In gate:

```env
# File: frontend/.env.production
VITE_API_BASE_URL=https://<username>-<space-name>.hf.space
VITE_GOOGLE_CLIENT_ID=<the same OAuth Client ID you set as GOOGLE_OAUTH_CLIENT_ID above>
```

`VITE_GOOGLE_CLIENT_ID` is not secret — OAuth Client IDs identify the app rather than authenticate it, so it's safe to ship in the built frontend bundle.

### 2. Build production assets
Compile the static React assets:
```bash
cd frontend
npm install
npm run build
```
This compiles the application assets into the `frontend/dist` directory.

---

## Part 3: Deploy Frontend to Firebase Hosting

We will serve the React app using Firebase's free, high-speed Hosting CDN.

### 1. Initialize Firebase Project
1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Click **Add Project** (or select an existing project).
3. Name your project, click through the setup prompts, and ensure you remain on the **Spark (No-cost) Plan**.
4. Once the project is ready, install the Firebase CLI on your computer if you haven't already:
   ```bash
   npm install -g firebase-tools
   ```
5. Authenticate your CLI session:
   ```bash
   firebase login
   ```

### 2. Configure Firebase Hosting
1. From the `frontend/` directory, initialize the hosting setup:
   ```bash
   firebase init hosting
   ```
2. Respond to the CLI prompts as follows:
   *   **Project Setup:** Choose **Use an existing project** and select the project you created above.
   *   **What do you want to use as your public directory?** Type `dist` (this matches Vite's build folder).
   *   **Configure as a single-page app (rewrite all urls to /index.html)?** Type `y` (Yes).
   *   **Set up automatic builds and deploys with GitHub?** Type `n` (No, we will deploy manually).
   *   *If prompted to overwrite index.html:* Type `n` (No, do not overwrite).

### 3. Deploy to Firebase
Run the deployment command:
```bash
firebase deploy --only hosting
```

Once completed, the CLI will output your live URL ending in `.web.app` (e.g., `https://traffitwin-ai.web.app`).

---

## Part 4: Testing & Verification

1. Open your live Firebase Hosting URL in your browser.
2. The **Mission Briefing** modal will load.
3. Check the top bar indicators:
   *   The `RECON ACC` and `RMSE` metrics should load live values once the backend container wakes up.
   *   The status indicator should change from `CONNECTING...` to `OPERATIONAL` or `DEGRADED`.
4. Open the **Ops Intelligence** sidebar panel on the right, query the Operations Analyst, and test manual sensor failure injections on the network map.
