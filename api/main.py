from fastapi import FastAPI, status
from fastapi.responses import Response

from api.middleware import ExceptionHandlerMiddleware
from api.routers.feed import router as feed_router
from api.routers.user import router as user_router

app = FastAPI()
app.add_middleware(ExceptionHandlerMiddleware)

app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(feed_router, prefix="/feed", tags=["feed"])


@app.get("/healthcheck")
def healthcheck() -> Response:
    return Response(status_code=status.HTTP_200_OK)
