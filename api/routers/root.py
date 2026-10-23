from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
def read_root(request: Request):
    return {
        "name": request.app.title,
        "version": request.app.version,
        "description": "API for the LEDGER database",
        "status": "available",
        "documentation": str(request.url_for("swagger_ui_html")),
        "openapi_schema": str(request.url_for("openapi")),
    }
