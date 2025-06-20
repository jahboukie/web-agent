from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, tasks, web_pages, execution_plans, plans

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["Tasks"]
)

api_router.include_router(
    web_pages.router,
    prefix="/web-pages",
    tags=["Web Pages"]
)

api_router.include_router(
    execution_plans.router,
    prefix="/execution-plans",
    tags=["Execution Plans"]
)

api_router.include_router(
    plans.router,
    prefix="/plans",
    tags=["AI Planning"]
)