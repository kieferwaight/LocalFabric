from fastapi import FastAPI

app = FastAPI(title="Casbin Authorization Service")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
