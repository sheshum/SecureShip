from fastapi import FastAPI

app = FastAPI(
    title="SecureShipBackend",
    description="BFF for SecureShip client application",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Welcome to my FastAPI application!"}

@app.get("/health")
def get_health():
    return {"status": "healthy"}
