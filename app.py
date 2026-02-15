from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes import router

app = FastAPI()

# 1. Monta a pasta 'static' para servir o HTML e scripts
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Inclui as rotas do arquivo routes.py
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
