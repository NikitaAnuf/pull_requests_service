from fastapi import FastAPI
import uvicorn
import asyncio

from variables import APP_HOST, APP_PORT
from api import team, users, pull_request, statistics

app = FastAPI()

app.include_router(team.router, prefix="/team", tags=["team"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(pull_request.router, prefix="/pullRequest", tags=["pull_request"])
app.include_router(statistics.router, prefix="/statistics", tags=["statistics"])


if __name__ == "__main__":
    config = uvicorn.Config(
        app,
        host=APP_HOST,
        port=APP_PORT,
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
