import multiprocessing
import sys
from pathlib import Path
import webbrowser


from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


print("Iniciando aplicação...")
print("Pode demorar bastante na primeira vez.")
from web.routes import router

# Resolve base path: inside PyInstaller bundle or project root
BASE_DIR = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent

HOST = "0.0.0.0"
PORT = 8001
URL = f"http://{HOST}:{PORT}"

app = FastAPI()

# 1. Monta a pasta 'static' para servir o HTML e scripts
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 2. Inclui as rotas do arquivo routes.py
app.include_router(router)


import uvicorn
class CustomServer(uvicorn.Server):
    def __init__(self, config):
        super().__init__(config)

    async def startup(self, sockets=None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            webbrowser.open(URL)


def run_server():
    config = uvicorn.Config(app=app, host=HOST, port=PORT, log_level="info")
    multiprocessing.freeze_support()
    server = CustomServer(config)
    server.run()



if __name__ == "__main__":
    run_server()
