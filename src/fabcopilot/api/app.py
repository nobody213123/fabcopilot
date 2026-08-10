from fastapi import FastAPI

from fabcopilot import __version__

app = FastAPI(
    title="FabCopilot",
    version=__version__,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
