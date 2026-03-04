from fastapi import FastAPI
from api.routes import health, blacklist, scan

app = FastAPI(title="AI Lead Hunter Fast Scan Service")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Autonomous AI Lead Hunter Fast Scan Service"}

app.include_router(health.router, tags=["Health"])
app.include_router(blacklist.router, tags=["Blacklist"])
app.include_router(scan.router, tags=["Scanner"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)