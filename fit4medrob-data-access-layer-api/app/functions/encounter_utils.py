import pandas as pd
from datetime import datetime as dt
import numpy as np
from app.functions.organization_utils import get_organization_by_identifier, get_organization_by_id
from app.functions.patient_utils import get_pat_identifier
import requests, os
from dotenv import load_dotenv
from app.config.logger import logger
from app.functions.reference_utils import resolve_resource_id_reference_encounter

load_dotenv()

# Lettura dell'url del server hapi e dell'identifier dell'organizzazione coordinatrice (vede tutti i dati)
base_url = os.getenv("BASE_URL")
coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

enc_fhir_paths = ["id",
                  ("name", "class.display"),
                  ("Patient ID", "subject.reference"),
                  ("date", "period.start"),
                  ("Rehab Center ID", "serviceProvider.reference"),
                  ("identifier", "identifier.value")
                  ]


def get_encounter_list(search, organization):
    logger.debug("get all encounters query")

    request_params = {}
    org_name = None
    if organization != coord_id:
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return []
        request_params["service-provider"] = organization
    encounters_df = search.steal_bundles_to_dataframe(
        resource_type="Encounter",
        request_params=request_params,
        fhir_paths=enc_fhir_paths
    )

    if isinstance(encounters_df, pd.DataFrame):
        encounters_df = resolve_resource_id_reference_encounter(search, encounters_df, org_name)
        return encounters_df
    else:
        return []


def get_name_list(search, organization):
    # Ritorna i nomi degli encounter (tipo T0, T1 etc)
    request_params = {}
    if organization != coord_id:
        request_params["service-provider"] = organization
    encounters_df = search.steal_bundles_to_dataframe(
        resource_type="Encounter",
        request_params=request_params,
        fhir_paths=[("name", "class.display")]
    )
    if isinstance(encounters_df, pd.DataFrame):
        name_values = encounters_df["name"].values
        unique_names = set()
        for value in name_values:
            if value is np.nan:
                continue
            if isinstance(value, list):
                value = value[0]
            unique_names.add(value)
        names = list(unique_names)
    else:
        names = []
    return names


def get_encounter_by_id(id, search, organization):
    logger.debug("get encounter by id")

    encounters_df = search.steal_bundles_to_dataframe(
        resource_type="Encounter",
        request_params={
            "_id": id,
        },
        fhir_paths=enc_fhir_paths
    )
    if isinstance(encounters_df, pd.DataFrame):
        encounters_df = resolve_resource_id_reference_encounter(search, encounters_df)[0]
        if organization != coord_id:
            org_name = get_organization_by_id(organization, search)["name"]
            if encounters_df["rehabCenter"] != org_name:
                return None
        return encounters_df
    else:
        return None


def search_encounter_hapi_fhir_nopag(encounter_input, search, organization):
    logger.debug("search encounter by filter")

    tot_params = encounter_input.dict()
    params = {}

    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return []
        params["service-provider"] = organization
    else:  # nel caso in cui l'utente sia dell'org coordinatrice può filtrare per identifier dell'org
        org_name = None
        org_filter = tot_params["organization"]
        if org_filter is not None:
            try:
                org_name = get_organization_by_id(org_filter, search)["name"]
            except:
                return []
            params["service-provider"] = organization

    if tot_params["exam_name"] is not None:
        params["class:text"] = tot_params["exam_name"]

    date_init = "1920-01-01" if not tot_params["date_init"] else str(tot_params["date_init"])[:10]
    if not tot_params["date_end"]:
        date_end = str(dt.now().date())[:10]
    else:
        date_end = str(tot_params["date_end"])[:10]

    pat_identifier = None
    pat_param = tot_params["patient"]
    if pat_param is not None:
        pat_identifier = get_pat_identifier(pat_param, search)
        params["patient"] = pat_param

    if tot_params["sortBy"] is not None:
        params["_sort"] = get_sort_par(tot_params["sortBy"])

    params["_count"] = 100
    encounters_df = search.sail_through_search_space_to_dataframe(
        resource_type="Encounter",
        time_attribute_name="date",
        date_init=date_init,
        date_end=date_end,
        request_params=params,
        fhir_paths=enc_fhir_paths
    )

    if isinstance(encounters_df, pd.DataFrame):
        encounters_df = resolve_resource_id_reference_encounter(search, encounters_df, org_name, pat_identifier)
        return encounters_df
    else:
        return []


def search_encounter_hapi_fhir(encounter_input, search, organization):
    logger.debug("search encounter by filter")

    tot_params = encounter_input.dict()
    params = {}

    # Aggiungo i par. per la paginazione
    count = tot_params["count"]
    n_page = tot_params["nPage"]
    sort_by = get_sort_par(tot_params["sortBy"])
    num_pages = 1
    offset = n_page * count
    if count == -1:
        num_pages = -1
    else:
        params["_count"] = count
        params["_offset"] = offset
    params["_sort"] = sort_by

    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return {"list": [], "total": 0}
        params["service-provider"] = organization
    else:  # nel caso in cui l'utente sia dell'org coordinatrice può filtrare per identifier dell'org
        org_name = None
        org_filter = tot_params["organization"]
        if org_filter is not None:
            try:
                org_name = get_organization_by_id(org_filter, search)["name"]
            except:
                return {"list": [], "total": 0}
            params["service-provider"] = organization

    if tot_params["exam_name"] is not None:
        params["class:text"] = tot_params["exam_name"]

    if tot_params["date_init"] is not None:
        date_init = str(tot_params["date_init"])[:10]
        params["date"] = "ge" + date_init
    if tot_params["date_end"] is not None:
        date_end = str(tot_params["date_end"])[:10]
        if tot_params["date_init"] is not None:
            params["date"] = "ge" + date_init + "&date=lt" + date_end
        else:
            params["date"] = "lt" + date_end

    pat_identifier = None
    pat_par = tot_params["patient"]
    if pat_par is not None:
        params["patient"] = pat_par
        pat_identifier = get_pat_identifier(pat_par, search)

    encounters_df = search.steal_bundles_to_dataframe(
        resource_type="Encounter",
        request_params=params,
        fhir_paths=enc_fhir_paths,
        num_pages=num_pages
    )

    if isinstance(encounters_df, pd.DataFrame):
        params["_summary"] = "count"
        params["_total"] = "accurate"
        total_count = list(search.steal_bundles(
            resource_type="Encounter",
            request_params=params,
            num_pages=-1
        ))[0].total

        encounters_df = resolve_resource_id_reference_encounter(search, encounters_df, org_name, pat_identifier)
        return {"list": encounters_df, "total": total_count}
    else:
        return {"list": [], "total": 0}


def delete_encounter_util(id, search, organization):
    logger.debug("delete encounter by id")

    encounters_df = search.steal_bundles_to_dataframe(
        resource_type="Encounter",
        request_params={
            "_id": id,
        },
        fhir_paths=["id", ("Rehab Center ID", "serviceProvider.reference")]
    )
    if isinstance(encounters_df, pd.DataFrame):
        encounters_df = encounters_df.to_dict("records")[0]
        if encounters_df["Rehab Center ID"] != "Organization/" + str(organization):
            raise Exception(
                "Cancellazione non eseguita: risorsa di un'organizzazione diversa da quella dell'utente (403)")
    else:
        raise Exception("Cancellazione non eseguita: risorsa non trovata (404)")

    response = requests.delete(f"{base_url}/Encounter/{id}?_cascade=delete",
                               auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if not (response.status_code == 200 or response.status_code == 204):
        logger.error(f"Failed to delete encounter with ID {id}, ", response.status_code, response.text)
        raise Exception(response.status_code)


def get_sort_par(sortBy):
    # [_content, _id, _lastUpdated, _profile, _security, _source, _tag, _text, account, appointment, based-on, class, 
    # date, diagnosis, episode-of-care, identifier, length, location, location-period, part-of, participant, participant-type, 
    # patient, practitioner, reason-code, reason-reference, service-provider, special-arrangement, status, subject, type]"

    # noi potremmo ricevere: _id, class, date, patient, type
    if sortBy.endswith("_id") or sortBy.endswith("date") or sortBy.endswith("patient"):
        return sortBy

    if sortBy.endswith("name"):
        if sortBy[0] == "-":
            return "-class"
        else:
            return "class"

    return "_id"
