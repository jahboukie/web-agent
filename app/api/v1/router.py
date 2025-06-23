from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    enterprise,
    execute,
    execution_plans,
    plans,
    security,
    tasks,
    users,
    web_pages,
    webhooks,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

api_router.include_router(users.router, prefix="/users", tags=["Users"])

api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])

api_router.include_router(web_pages.router, prefix="/web-pages", tags=["Web Pages"])

api_router.include_router(
    execution_plans.router, prefix="/execution-plans", tags=["Execution Plans"]
)

api_router.include_router(plans.router, prefix="/plans", tags=["AI Planning"])

api_router.include_router(execute.router, prefix="/execute", tags=["Action Execution"])

api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

api_router.include_router(
    enterprise.router, prefix="/enterprise", tags=["Enterprise Access Control"]
)

api_router.include_router(
    security.router, prefix="/security", tags=["Security Management"]
)

api_router.include_router(
    analytics.router, prefix="/analytics", tags=["Analytics & Billing"]
)
