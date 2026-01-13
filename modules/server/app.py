from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modules.server.routes import router
import asyncio


# from modules.agents.worker import run_agent_worker  # Import if running locally

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. STARTUP LOGIC (Before yield)
    print("Server Starting...")

    # Example: Start the background worker loop
    # task = asyncio.create_task(run_agent_worker())

    yield  # The application runs here

    # 2. SHUTDOWN LOGIC (After yield)
    print("Server Shutting Down...")
    # Clean up resources (e.g., close DB connections, cancel tasks)
    # await redis_service.close()
    # task.cancel()


# --- APP FACTORY ---
def create_app() -> FastAPI:
    # Pass the lifespan manager here
    app = FastAPI(title="DeepAgent Chat Server", lifespan=lifespan)

    # CORS is vital for Frontend communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify your frontend domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routes
    app.include_router(router, prefix="/api/v1")

    return app