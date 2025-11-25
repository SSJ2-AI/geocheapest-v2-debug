# Frontend Setup and Local Launch Plan

## Goal
Launch the GeoCheapest frontend locally to allow the user to test the site and verify connectivity.

## Proposed Changes

### Frontend Configuration
#### [NEW] [frontend/.env.local](file:///c:/Users/csc20/OneDrive/Desktop/geocheapest-v2-final-cursor-implement-all-real-integrations-for-geocheapest-5839/frontend/.env.local)
- Configure `NEXT_PUBLIC_API_URL` to point to the deployed backend (or minimal fallback).
- Configure `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.

### Execution
- Run `npm install` in `frontend/` to install dependencies.
- Run `npm run dev` to start the local development server.

## Verification Plan
### Automated Tests
- Verify `npm install` completes successfully.
- Verify `npm run dev` starts the server on port 3000.

### Manual Verification
- User can open `http://localhost:3000` to view the site.
