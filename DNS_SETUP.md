# DNS Configuration Guide

To connect your custom domain to your deployed application, follow these steps:

## 1. Frontend (Vercel)

1.  Log in to your Vercel dashboard.
2.  Go to your project settings -> **Domains**.
3.  Add your custom domain (e.g., `geocheapest.com`).
4.  Vercel will provide you with DNS records to add to your domain registrar (e.g., GoDaddy, Namecheap).
    *   **A Record**: `@` -> `76.76.21.21`
    *   **CNAME Record**: `www` -> `cname.vercel-dns.com`

## 2. Backend (Google Cloud Run)

Your backend is hosted on Google Cloud Run. You have two options:

### Option A: Use the default Cloud Run URL (Easiest)
Your backend will be available at a URL like `https://geocheapest-backend-xyz-uc.a.run.app`.
*   Update your Frontend environment variable `NEXT_PUBLIC_API_URL` in Vercel to point to this URL.

### Option B: Map a subdomain (e.g., `api.geocheapest.com`)
1.  Go to Google Cloud Console -> **Cloud Run**.
2.  Click **Manage Custom Domains**.
3.  Click **Add Mapping**.
4.  Select your service (`geocheapest-backend`) and select "Verify a new domain" if needed.
5.  Enter `api.geocheapest.com`.
6.  Google will provide DNS records (usually A or AAAA records) to add to your registrar.

## 3. Environment Variables

Ensure your Vercel project has the following environment variables:
*   `NEXT_PUBLIC_API_URL`: The URL of your backend (e.g., `https://api.geocheapest.com` or the Cloud Run URL).

Ensure your Google Cloud Run service has the following environment variables:
*   `ADMIN_API_KEY`: Your secure admin key.
*   `RAPIDAPI_KEY`: Your RapidAPI key.
*   `AMAZON_CA_AFFILIATE_TAG`: Your Amazon CA tag.
*   `SECRET_KEY`: A long random string for JWT signing.
