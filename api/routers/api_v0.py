from fastapi import APIRouter
from routers import actor, gwp, sector, datasource, health, root, enums

api_router = APIRouter(prefix="/api/v0")

api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(actor.router)
api_router.include_router(sector.router)
api_router.include_router(datasource.router)
api_router.include_router(gwp.router)
api_router.include_router(enums.router)
