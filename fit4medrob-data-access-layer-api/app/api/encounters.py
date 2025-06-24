from fastapi import APIRouter, Depends
from app.config.logger import logger
from app.core.pyrate import get_pyrate_client
from typing import List
from dotenv import load_dotenv
from app.core.auth import get_current_user
from starlette import status
from starlette.responses import JSONResponse
from app.functions.encounter_utils import search_encounter_hapi_fhir, get_encounter_list, get_encounter_by_id, \
    delete_encounter_util, search_encounter_hapi_fhir_nopag, get_name_list
from app.schemas.Encounter import EncounterSearchRequest, Encounter, EncounterSearchResult

load_dotenv()

router = APIRouter()


@router.get("/all", response_model=List[Encounter], response_description='Get encounter list')
async def get_all_encounters(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_encounter_list(search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/names", response_model=List[str], response_description='Get encounter names list')
async def get_encounters_names(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    # Viene usata per filtrare le obx sulla base degli encounter associati 
    try:
        organization = cu.get("organization")
        return get_name_list(search, organization)
    except Exception as e:
        logger.error(f"errore nella get_all dei nomi degli encounter: {e}")
        return []


@router.get("/{encounter_id}", response_model=Encounter, response_description='Get encounter by id')
async def get_encounter(encounter_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_encounter_by_id(encounter_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post("/search-encounter-nopag", response_model=List[Encounter])
async def search_encounter_nopag(request: EncounterSearchRequest, cu=Depends(get_current_user),
                                 search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_encounter_hapi_fhir_nopag(request, search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post("/search-encounter", response_model=EncounterSearchResult)
async def search_encounter(request: EncounterSearchRequest, cu=Depends(get_current_user),
                           search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_encounter_hapi_fhir(request, search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.delete("/{encounter_id}", response_description='Delete encounter by id')
async def delete_encounter(encounter_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        delete_encounter_util(encounter_id, search, organization)
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
