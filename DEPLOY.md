# Deploying Jutsu Academy to Vercel

The web interface for Jutsu Academy (located in `/web`) is a Next.js application that can be easily deployed to Vercel.

## 1. Prerequisites

You need a [Vercel](https://vercel.com) account.

## 2. Environment Variables

The application connects to your Supabase backend. You must configure the following Environment Variables in your Vercel Project Settings:

- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase Project URL (e.g., `https://xyz.supabase.co`)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase Anon/Public Key

*You can find these in your Supabase Dashboard under Project Settings > API.*

## 3. Deployment Steps

### Method A: Vercel CLI (Recommended)

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Deploy**:
   Run the following command from the root of this repository:
   ```bash
   vercel
   ```

3. **Follow the prompts**:
   - Set up and deploy? **Y**
   - Which scope? **(Select your team/account)**
   - Link to existing project? **N**
   - Project Name: **jutsu-academy-web**
   - In which directory is your code located? **./web**  <-- IMPORTANT: Type `./web` here (or select the web directory option).
   - Want to modify these settings? **N**

4. **Add Environment Variables**:
   Go to the Vercel Dashboard for your new project, navigate to **Settings > Environment Variables**, and add the Supabase keys mentioned above.
   
5. **Redeploy**:
   After adding variables, you may need to redeploy for them to take effect.
   ```bash
   vercel --prod
   ```

### Method B: Git Integration

1. Push this repository to GitHub/GitLab/Bitbucket.
2. Import the project in Vercel.
3. **IMPORTANT**: In the "Root Directory" setting, edit it and select `web`.
4. Add the Environment Variables during the import process.
5. Click **Deploy**.

## 4. Features

Once deployed, your website will host:
- **Landing Page**: Promotional material for the project.
- **Web Dojo**: A client-side AI demo using ONNX Runtime (accessible at `/play`).
- **Leaderboard**: A live view of the top Shinobi speeds (accessible at `/leaderboard`).

## 5. Troubleshooting

- **Model Loading Error**: Ensure `model.onnx` is present in `web/public/model/`.
- **404 on Leaderboard**: Ensure your Supabase `leaderboard` table has RLS (Row Level Security) policies that allow "Select" for anonymous users (or public access).
