@echo off
set GCP_PROJECT_ID=geocheapest-v2
set BACKEND_URL=http://localhost:8000
set FRONTEND_URL=http://localhost:3000
set ADMIN_API_KEY=super_secret_admin_key_change_in_production
set RAPIDAPI_KEY=177c7aa942msh1701b1d5dabf813p12c55cjsn143f0649e797
set RAPIDAPI_AMAZON_HOST=real-time-amazon-data.p.rapidapi.com
set SECRET_KEY=your-secret-key-change-in-production
set AMAZON_CA_AFFILIATE_TAG=geocheapest-20

echo Starting GeoCheapest v2 Backend...
python -m uvicorn app.main:app --reload --port 8000
