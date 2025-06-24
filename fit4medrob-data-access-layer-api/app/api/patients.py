from starlette import status
from starlette.responses import JSONResponse
from app.core.auth import get_current_user
from app.core.pyrate import get_pyrate_client
from app.functions.patient_utils import get_patient_list, get_patient_by_id, search_patient_hapi_fhir, \
    delete_patient_util, \
    search_patient_hapi_fhir_nopag, get_patient_list_full
from fastapi import APIRouter, Depends
from app.config.logger import logger
from typing import List
from dotenv import load_dotenv

load_dotenv()
from app.schemas.Patient import PatientSearchRequest, Patient, PatientSearchResult

router = APIRouter()


@router.get("/all", response_model=List[Patient], response_description='Get patient list')
async def get_all_patients(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    # Questa viene chiamata per popolare il menù a tendina per filtrare encounter e obx (ritorna solo gli identifier)
    try:
        organization = cu.get("organization")
        return get_patient_list(search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/all-full", response_model=List[Patient], response_description='Get patient list')
async def get_all_patients(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    # Questa viene chiamata per popolare il form di selezione pazienti quando si vogliono importare i dati da macchinari o da file (ritorna identifier, sesso, dob)
    try:
        organization = cu.get("organization")
        return get_patient_list_full(search, organization)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get("/{patient_id}", response_model=Patient, response_description='Get patient by id')
async def get_patient(patient_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        resp = get_patient_by_id(patient_id, search, organization)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp

    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


# Funzione chiamata per popolare le viste 
@router.post("/search-patient-nopag", response_model=PatientSearchResult)
async def search_patient_no_pag(request: PatientSearchRequest, cu=Depends(get_current_user),
                                search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        result = search_patient_hapi_fhir_nopag(request, search, organization)
        return result
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post("/stratify-patient", response_model=List[str])
async def stratify_patient(request: PatientSearchRequest, cu=Depends(get_current_user),
                           search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_patient_hapi_fhir_nopag(request, search, organization, is_stratify=True)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.delete("/all", response_description='Delete all patients')
async def delete_all_patients(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        df_patients = get_patient_list(search, organization)
        if df_patients:
            patients = [p['id'] for p in df_patients]
            for patient_id in patients:
                delete_patient_util(patient_id, search, organization)
        else:
            logger.info("No patients to delete")
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.delete("/{patient_id}", response_description='Delete patient by id')
async def delete_patient(patient_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        delete_patient_util(patient_id, search, organization)
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post("/search-patient", response_model=PatientSearchResult)
async def search_patient(request: PatientSearchRequest, cu=Depends(get_current_user),
                         search=Depends(get_pyrate_client)):
    try:
        organization = cu.get("organization")
        return search_patient_hapi_fhir(request, search, organization)

    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
