from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from app.config.logger import logger
from app.core.pyrate import get_pyrate_client
from typing import List
from starlette import status
from starlette.responses import JSONResponse
from app.core.auth import get_current_user
from app.functions.organization_utils import (
    search_organization_hapi_fhir,
    get_organization_list,
    get_organization_by_id,
    delete_organization_util,
    create_organization_hapi_fhir,
    update_organization_hapi_fhir
)
from app.schemas.Organization import OrganizationSearchRequest, Organization

load_dotenv()

router = APIRouter()


@router.get(
    "/all",
    response_model=List[Organization],
    response_description='Get organizations list',
    summary="Retrieve all organizations"
)
async def get_all_organizations(cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        return get_organization_list(search)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.get(
    "/{organization_id}",
    response_model=Organization,
    response_description='Get organization by id',
    summary="Retrieve organization by ID"
)
async def get_organization(organization_id: str, cu=Depends(get_current_user), search=Depends(get_pyrate_client)):
    try:
        resp = get_organization_by_id(organization_id, search)
        if not resp:
            return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
        return resp
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post(
    "/search-organization",
    response_model=List[Organization],
    summary="Search organizations by criteria"
)
async def search_organization(
        request: OrganizationSearchRequest,
        cu=Depends(get_current_user),
        search=Depends(get_pyrate_client)
):
    try:
        return search_organization_hapi_fhir(request, search)
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.post(
    "/create-organization",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization"
)
async def create_organization(request: Organization, cu=Depends(get_current_user)):
    try:
        response_code = create_organization_hapi_fhir(request)
        return response_code
    except HTTPException as http_exc:
        # Propaga l'HTTPException senza alterarla
        raise http_exc
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.put(
    "/{organization_id}",
    summary="Update an existing organization"
)
async def update_organization(
        request: Organization,
        organization_id: str,
        cu=Depends(get_current_user)
):
    try:
        response_code = update_organization_hapi_fhir(request, organization_id)
        return response_code
    except Exception as e:
        logger.error(f"errore: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )


@router.delete(
    "/{organization_id}",
    response_description='Delete organization by id',
    summary="Delete an organization"
)
async def delete_organization(organization_id: str, cu=Depends(get_current_user)):
    try:
        delete_organization_util(organization_id)
    except Exception as e:
        logger.error(f"Error during deletion: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(e)},
        )
