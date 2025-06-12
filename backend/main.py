from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

# Configure logging AT THE VERY TOP, before other imports if they might log.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# For more detailed Pyppeteer logging if needed during development/debugging:
# logging.getLogger('pyppeteer').setLevel(logging.DEBUG)
# logging.getLogger('websockets').setLevel(logging.DEBUG) # Pyppeteer uses websockets

from orchestrator import Orchestrator
from browser_utils import browser_manager_instance, PYPPETEER_CHROMIUM_REVISION

app = FastAPI()

# Get a logger for this specific file (or use root logger if preferred)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup sequence initiated...")
    try:
        await browser_manager_instance.ensure_chromium_downloaded()
        logger.info("Chromium download/availability check complete via BrowserManager.")
    except Exception as e:
        logger.error(f"Critical error during Chromium download/setup on startup: {e}", exc_info=True)
        # Depending on policy, you might want to exit the application if browser is critical
        # For now, log and continue; subsequent browser operations will likely fail and inform the user.
    logger.info("Browser setup check complete. Browser launch will occur on first browser-related command.")
    logger.info("Application startup sequence finished.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown sequence initiated...")
    await browser_manager_instance.close_browser()
    logger.info("Browser closed. Application shutdown sequence complete.")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allows frontend development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Orbitron CUA Backend"}

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_message = data.get("message", "")

    orchestrator_instance = Orchestrator()
    response_generator = orchestrator_instance.process_user_message(user_message)

    return StreamingResponse(response_generator, media_type="application/x-ndjson")
