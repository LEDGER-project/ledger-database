from fastapi import APIRouter
from api.routers import (
    actor_v1,
    #emissions,
    #gdp,
    gwp,
    health,
    #population,
    root,
    #targets,
    #energy_consumption,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(actor_v1.router)
api_router.include_router(gwp.router)
