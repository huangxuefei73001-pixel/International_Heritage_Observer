from fastapi import FastAPI

from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router


app = FastAPI(title="国际遗产观察 Web API")
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
