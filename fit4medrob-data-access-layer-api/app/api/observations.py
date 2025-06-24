from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from typing import List
from starlette import status
from starlette.responses import JSONResponse, StreamingResponse
from app.config.logger import logger
from app.core.auth import get_current_user
from app.core.pyrate import get_pyrate_client
from app.functions.eeg_utils import get_eeg_observation_by_id, get_channel_eeg_observation_by_id
from app.functions.mvnx_utils import get_mvnx_observation_by_id, get_mvnx_metadata_by_id
from app.functions.observation_utils import search_observation_hapi_fhir, get_obx_by_encounter, get_observation_by_id,\
    delete_observation_util, get_name_list, search_observation_for_stratification, download_from_s3_by_id
from app.schemas.Observation import ObservationSearchRequest, Observation, ObservationSearchResult, DictItem, ObservationStratificationRequest, \
    ObsRed, Signal, MVNXMetadata

load_dotenv()

router = APIRouter()

        
@router.post("/search-observation", response_model=ObservationSearchResult, response_description='Search observations by filter them')
async def search_observation(request: ObservationSearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_observation_hapi_fhir(request, search, organization, show_eeg = False)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
        
@router.post("/search-eeg", response_model=ObservationSearchResult, response_description='Search eeg observations by filter them')
async def search_eeg_observation(request: ObservationSearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_observation_hapi_fhir(request, search, organization, show_eeg = True)
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
@router.post("/search-mvnx", response_model=ObservationSearchResult, response_description='Search mvnx observations by filter them')
async def search_mvnx_observation(request: ObservationSearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_observation_hapi_fhir(request, search, organization, show_mvnx = True)
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )

@router.post("/search-robotdata", response_model=ObservationSearchResult, response_description='Search robot data observations by filter them')
async def search_eeg_observation(request: ObservationSearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_observation_hapi_fhir(request, search, organization, show_robot = True)
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )    
    
    
@router.get("/encounter/{encounter_id}", response_model=List[Observation], response_description='Get observations by encounter_id')
async def get_observation_by_encounter(encounter_id : str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_obx_by_encounter(encounter_id, search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
@router.post("/search-observation-analytics", response_model=List[ObsRed], response_description='Get observations for the analytics')
async def search_observation_analytics(request: ObservationStratificationRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_observation_for_stratification(request, search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )    

@router.get("/{observation_id}/signals", response_model=List[Signal], response_description='Get all the signals of the observation')
async def get_all_signals(observation_id: str, cu=Depends(get_current_user),search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_eeg_observation_by_id(observation_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
  
@router.get("/{observation_id}/mvnx-signals", response_model=List, response_description='Get all the signals of the mvnx observation')
async def get_all_mvnx_signals(observation_id: str, cu=Depends(get_current_user),search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_mvnx_observation_by_id(observation_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
 
@router.get("/{observation_id}/mvnx-metadata", response_model=MVNXMetadata, response_description='Get all the signals of the mvnx observation')
async def get_mvnx_metadata(observation_id: str, cu=Depends(get_current_user),search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_mvnx_metadata_by_id(observation_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
       
@router.get("/download/{eeg_id}", response_description="Download file for EEG Observation")
async def download_eeg_observation(eeg_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    """
    Endpoint per scaricare il file dell'eeg definito da eeg:id
    """
    try:
        organization = cu.get("organization")
        edf_buffer = download_from_s3_by_id(eeg_id, search, organization)
        headers = {"Content-Disposition": f"attachment; filename={eeg_id}.edf"}
        return StreamingResponse(edf_buffer, media_type="application/edf", headers=headers)
        
    except Exception as e:
        logger.error(f"Error downloading images for study {eeg_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/download-mvnx/{mvnx_id}", response_description="Download file for MVNX Observation")
async def download_mvnx_observation(mvnx_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    """
    Endpoint per scaricare il file mvnx del sxens definito da mvnx_id
    """
    try:
        organization = cu.get("organization")
        file_buffer = download_from_s3_by_id(mvnx_id, search, organization)
        headers = {"Content-Disposition": f"attachment; filename={mvnx_id}.mvnx"}
        return StreamingResponse(file_buffer, media_type="application/octet-stream", headers=headers)
        
    except Exception as e:
        logger.error(f"Error downloading images for study {mvnx_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
                
                
@router.delete("/{observation_id}", response_description='Delete observation by id')
async def delete_observation(observation_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        delete_observation_util(observation_id, search, organization)
    except Exception as e:
        logger.error(f"Error during deletion of observation: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
        



@router.get("/{observation_id}/signal/{channel}", response_model=List[DictItem], response_description='Get the signal of the observation defined by channel')
async def get_signal(observation_id: str, channel : str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_channel_eeg_observation_by_id(observation_id, channel, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
    
    

@router.get("/names", response_model=list[str],response_description='Get observation names list')
async def get_observations_names(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_name_list(search, organization)
    except Exception as e:
        logger.error(f"errore nella get_all dei nomi delle observation: {e}")
        return []
    
    

@router.get("/{observation_id}", response_model=Observation, response_description='Get observation by id')
async def get_observation(observation_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_observation_by_id(observation_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )