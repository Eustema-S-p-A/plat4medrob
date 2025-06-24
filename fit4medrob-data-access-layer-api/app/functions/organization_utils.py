import pandas as pd
from fastapi import HTTPException, status
import numpy as np
import requests, os, json
from app.schemas.Organization import Organization
from dotenv import load_dotenv
from app.config.logger import logger

load_dotenv()

# Lettura delle variabili d'ambiente relative al server hapi 
base_url = os.getenv("BASE_URL")

fhir_paths = [("identifier", "identifier.value"),
              ("name", "name"),
              "id",
              ("indirizzo", "address.line"),
              ("citta", "address.city"),
              ("cap", "address.postalCode"),
              ]


def create_organization_hapi_fhir(org_data: Organization):
    # Generazione dell'ID univoco
    identifier = validate_unique_id(org_data.identifier)
    if identifier is not None:
        # Costruzione del payload FHIR
        fhir_data = {
            "resourceType": "Organization",
            "identifier": [{"use": "official", "value": identifier}],
            "name": org_data.name,
            "address": [{
                "line": org_data.indirizzo,
                "city": org_data.citta,
                "postalCode": org_data.cap
            }]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Identifier dell''organizzazione già utilizzato',
        )

    # Endpoint del server FHIR
    # Invio della richiesta POST al server HAPI FHIR
    headers = {'Content-Type': 'application/fhir+json'}
    response = requests.post(f"{base_url}/Organization", headers=headers, data=json.dumps(fhir_data),
                             auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if response.status_code < 200 or response.status_code > 399:
        raise Exception(response.text)
    return response.status_code


def update_organization_hapi_fhir(org_data: Organization, id):
    identifier = get_organization_by_id(id)["identifier"]

    # Costruzione del payload FHIR
    fhir_data = {
        "resourceType": "Organization",
        "name": org_data.name,
        "id": id,
        "identifier": {"value": identifier},
        "address": [{
            "line": org_data.indirizzo,
            "city": org_data.citta,
            "postalCode": org_data.cap
        }]
    }

    # Invio della richiesta POST al server HAPI FHIR
    headers = {'Content-Type': 'application/fhir+json'}
    response = requests.put(f"{base_url}/Organization/{id}", headers=headers, data=json.dumps(fhir_data),
                            auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if response.status_code < 200 or response.status_code > 399:
        raise Exception(response.text)

    return response.status_code


def get_organization_list(search):
    logger.debug("get all organizations query")

    organizations_df = search.steal_bundles_to_dataframe(
        resource_type="Organization",
        fhir_paths=fhir_paths
    )
    if isinstance(organizations_df, pd.DataFrame):
        organizations_df = organizations_df.replace([np.inf, -np.inf, np.nan], None)
        return organizations_df.to_dict("records")
    else:
        return []


def get_organization_by_id(id, search):
    logger.debug("get organization by id")

    organizations_df = search.steal_bundles_to_dataframe(
        resource_type="Organization",
        request_params={
            "_id": id,
        },
        fhir_paths=fhir_paths
    )
    if isinstance(organizations_df, pd.DataFrame):
        organizations_df = organizations_df.replace([np.inf, -np.inf, np.nan], None)
        return organizations_df.to_dict("records")[0]
    else:
        return None


def search_organization_hapi_fhir(organization_input, search):
    logger.debug("search organization by filter")

    params = {key: value for key, value in organization_input.dict().items() if value is not None}
    params["_count"] = 100
    organizations_df = search.steal_bundles_to_dataframe(
        resource_type="Organization",
        request_params=params,
        fhir_paths=fhir_paths
    )
    if isinstance(organizations_df, pd.DataFrame):
        organizations_df = organizations_df.replace([np.inf, -np.inf, np.nan], None)
        return organizations_df.to_dict("records")
    else:
        return []


def delete_organization_util(id):
    logger.debug("delete organization by id")
    response = requests.delete(f"{base_url}/Organization/{id}",
                               auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if not (response.status_code == 200 or response.status_code == 204):
        logger.error(f"Failed to delete organization with ID {id}.", response.status_code, response.text)
        raise Exception(response.text)


def validate_unique_id(corr_id):
    all_org = get_organization_list()
    all_id = [org["identifier"] for org in all_org]
    if corr_id in all_id:
        return None

    return corr_id


def get_organization_by_identifier(organization_identifier, search):
    org_df = search.steal_bundles_to_dataframe(
        resource_type="Organization",
        request_params={"identifier": organization_identifier},
        fhir_paths=["id", "name"]
    )

    if isinstance(org_df, pd.DataFrame):
        return org_df.to_dict("records")[0]["id"], org_df.to_dict("records")[0]["name"]
    else:
        return None, None


def get_name_identifier_organization_by_id(organization_id, search):
    org_df = search.steal_bundles_to_dataframe(
        resource_type="Organization",
        request_params={"_id": organization_id},
        fhir_paths=["identifier.value", "name"]
    )
    if isinstance(org_df, pd.DataFrame):
        return org_df.to_dict("records")[0]["identifier.value"], org_df.to_dict("records")[0]["name"]
    else:
        return None, None
