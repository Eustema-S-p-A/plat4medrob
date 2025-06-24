from starlette.responses import RedirectResponse
from app.api import analytics
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

load_dotenv()


# FastAPI app
app = FastAPI(title='fit4medrob-data-analytics-api')


@app.get("/", include_in_schema=False)
async def main():
    """Reindirizza alla documentazione Swagger"""
    return RedirectResponse(url="/docs", status_code=302)


app.include_router(analytics.router, prefix='/analytics', tags=['Analytics'])

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=20000, log_level="info")
