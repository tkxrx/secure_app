from fastapi import FastAPI

app = FastAPI(title="Secure App")


@app.get("/api/health")
def health():
    return {"status": "ok"}
