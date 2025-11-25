from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World", "Env": os.environ.get("GCP_PROJECT_ID")}

@app.get("/health")
def health():
    return {"status": "ok"}
