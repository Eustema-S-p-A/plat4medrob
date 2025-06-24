from dotenv import load_dotenv
from starlette.responses import RedirectResponse
from fastapi import FastAPI
from app.api import patients, observations, encounters, organizations, imagingstudies
import uvicorn
from logging.config import dictConfig
from app.config.logger import log_config

load_dotenv()

dictConfig(log_config)

# FastAPI app
app = FastAPI(title='fit4medrob-data-access-layer-api')


@app.get("/")
async def main():
    return RedirectResponse(url="/docs", status_code=302)


# add routers
app.include_router(patients.router, prefix='/patients', tags=['Patients'])
app.include_router(observations.router, prefix='/observations', tags=['Observations'])
app.include_router(encounters.router, prefix='/encounters', tags=['Encounters'])
app.include_router(organizations.router, prefix='/organizations', tags=['Organizations'])
app.include_router(imagingstudies.router, prefix='/imagingstudies', tags=['Imagingstudies'])

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=19000, log_level='info')
