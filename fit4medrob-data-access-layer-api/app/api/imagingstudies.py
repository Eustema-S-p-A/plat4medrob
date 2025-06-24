import time
from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from typing import List
from starlette import status
from starlette.responses import JSONResponse, StreamingResponse
from app.config.logger import logger
from app.core.auth import get_current_user
from app.core.pyrate import get_pyrate_client
from app.db.orthanc_client import get_dicom_client
from app.functions.imagingstudies_utils import search_imagingstudy_hapi_fhir, get_imagingstudy_list, \
    get_imagingstudy_by_id, \
    delete_imagingstudy_util, get_images_by_id, search_imagingstudy_hapi_fhir_nopag, get_modality_list, \
    get_bodysite_list, download_imagingstudy_by_id
from app.schemas.ImagingStudy import ImagingStudySearchRequest, ImagingStudy, ImagingStudySearchResult

load_dotenv()

router = APIRouter()


@router.get("/all", response_model=List[ImagingStudy], response_description='Get imagingstudy list')
async def get_all_imagingstudies(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_imagingstudy_list(search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
@router.get("/modalities", response_model=list[str], response_description='Get imagingstudy modality list')
async def get_all_modalities(cu=Depends(get_current_user),search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_modality_list(search, organization)
    except Exception as e:
        logger.error(f"errore nella ricerca delle modalities degli imagingstudies: {e}")
        return []
        
@router.get("/bodysites", response_model=list[str], response_description='Get imagingstudy bodysite list')
async def get_all_bodysites(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return get_bodysite_list(organization)
    except Exception as e:
        logger.error(f"errore nella ricerca dei bodysites degli imagingstudies: {e}")
        return []
        

@router.post("/search-imagingstudy", response_model=ImagingStudySearchResult)
async def search_imagingstudy(request: ImagingStudySearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_imagingstudy_hapi_fhir(request, search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/studies/{study_uid}/series/{serie_uid}", response_model=List, response_description='Get the images of the ImagingStudy')
async def get_images(study_uid: str, serie_uid: str, cu=Depends(get_current_user), client_session=Depends(get_dicom_client)):
    try:
        organization = cu.get("organization")
        start_time = time.time()
        result = await get_images_by_id(study_uid, serie_uid, client_session, organization)
        elapsed_time = time.time() - start_time
        logger.info(f"DICOM get images completed in {elapsed_time:.2f} seconds")
        return result
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.delete("/{imagingstudy_id}", response_description='Delete imagingstudy by id')
async def delete_imagingstudy(imagingstudy_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        delete_imagingstudy_util(imagingstudy_id, search, organization)
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/download/{imagingstudy_id}", response_description="Download images for ImagingStudy")
async def download_imagingstudy_images(imagingstudy_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    """
    Endpoint per scaricare le immagini relative a uno studio ImagingStudy definito con imagingstudy_id
    """
    try:
        organization = cu.get("organization")
        zip_buffer = download_imagingstudy_by_id(imagingstudy_id, search, organization)
        headers = {"Content-Disposition": f"attachment; filename={imagingstudy_id}.zip"}
        return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
        
    except Exception as e:
        logger.error(f"Error downloading images for study {imagingstudy_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
                    
     
@router.get("/{imagingstudy_id}", response_model=ImagingStudy, response_description='Get imagingstudy by id')
async def get_imagingstudy(imagingstudy_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_imagingstudy_by_id(imagingstudy_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


     
@router.post("/search-imagingstudy-nopag", response_model=List[ImagingStudy])
async def search_imagingstudy_nopag(request: ImagingStudySearchRequest, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_imagingstudy_hapi_fhir_nopag(request, search, organization)
    
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
    
    
    
        

