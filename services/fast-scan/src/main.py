from fastapi import FastAPI
from api.scan import router as scan_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Autonomous AI Lead Hunter Fast Scan Service"}

app.include_router(scan_router)