from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat import router as chat_router
from routes.health import router as health_router

app = FastAPI(title="AgentMesh Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "AgentMesh Gateway", "status": "operational"}
