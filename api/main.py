from fastapi import FastAPI
from routers.api_v0 import api_router

app = FastAPI(title="LEDGER Database API", version="v0")
app.include_router(api_router)
