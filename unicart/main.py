"""Run (development):  python -m unicart.main     |     production: uvicorn unicart.main:app"""
import logging

import uvicorn

from .ai.runtime import AiRuntime
from .persistence.database import Database
from .presentation.app import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
_db = Database()
app = create_app(_db, run_scheduler=True, ai=AiRuntime.from_config(_db))

if __name__ == "__main__":
    uvicorn.run("unicart.main:app", host="127.0.0.1", port=8000, reload=False)
