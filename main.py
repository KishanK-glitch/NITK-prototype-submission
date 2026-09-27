import uvicorn
from fastapi import FastAPI
from app.api.webhook import router as webhook_router

app = FastAPI(
    title="PM-KISAN WhatsApp Agent",
    description="Agentic workflow engine for rural government services",
    version="1.0.0"
)

# Mount the webhook router so requests hit /webhook
app.include_router(webhook_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pm-kisan-agent"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)