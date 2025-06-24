import pandas as pd
import numpy as np
from app.functions.organization_utils import get_organization_by_id
import requests, os
from dotenv import load_dotenv
from app.config.logger import logger
from app.functions.patient_data_operations import get_patient_obx, apply_filters
from datetime import datetime, timedelta
from app.functions.s3_utils import delete_all_s3_urls
from app.functions.imagingstudies_utils import get_all_dicom_uids, delete_all_dicom_uids
from app.functions.reference_utils import resolve_resource_id_reference_patient
from app.functions.observation_utils import get_all_s3_urls

load_dotenv()

# Lettura dell'url del server hapi e dell'identifier dell'organizzazione coordinatrice (vede tutti i dati)
base_url = os.getenv("BASE_URL")
coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

# FHIR PATHS DA LEGGERE NEL DB
pat_fhir_paths = ["id",
                  ("identifier", "identifier.value"),
                  "gender",
                  "birthDate",
                  ("Rehab Center ID", "managingOrganization.reference"),
                  ("linguaMadre", "communication.language.text"),
                  ]


def get_patient_list(search, organization):
    # Questa viene chiamata per popolare il menù a tendina per filtrare encounter e obx
    logger.debug("get all patients query")

    request_params = {}

    if organization != coord_id:
        request_params["organization"] = organization
    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=request_params,
        fhir_paths=["id", ("identifier", "identifier.value")]
    )
    if isinstance(patients_df, pd.DataFrame):
        patients_df = patients_df.replace([np.inf, -np.inf, np.nan], None)
        patients_df = patients_df.to_dict("records")
        return patients_df
    else:
        return []


def get_patient_list_full(search, organization):
    # Questa viene chiamata per popolare il form di selezione pazienti quando si vogliono importare i dati da macchinari o da file
    logger.debug("get all patients query")

    request_params = {}

    request_params["organization"] = organization

    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=request_params,
        fhir_paths=["id",
                    ("identifier", "identifier.value"),
                    "gender",
                    "birthDate",
                    ]
    )

    if isinstance(patients_df, pd.DataFrame):
        patients_df = patients_df.replace([np.inf, -np.inf, np.nan], None)
        patients_df = patients_df.to_dict("records")
        return patients_df
    else:
        return []


def get_patient_by_id(id, search, organization):
    logger.debug("get patient by id")

    request_params = {"_id": id}
    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=request_params,
        fhir_paths=pat_fhir_paths
    )

    if isinstance(patients_df, pd.DataFrame):
        if organization != coord_id:
            if patients_df.iloc[0]["Rehab Center ID"] != "Organization/" + organization:
                return None
        patients_df = resolve_resource_id_reference_patient(search, patients_df)
        patients_df = get_patient_obx(search, pd.DataFrame(patients_df), is_stratify=False, get_all=True)[0]
        patients_df['an_rem_patologie'] = [k for k in patients_df if k.startswith('an_rem') and patients_df[k] is not None]
       
        return patients_df
    else:
        return None


def search_patient_hapi_fhir_nopag(patient_input, search, organization, is_stratify=False):
    logger.debug("search patient by filter")

    # Inizializzazione dei parametri della query in pyrate
    tot_params = patient_input.dict()
    params = {}

    if tot_params["sortBy"] is not None:
        params["_sort"] = get_sort_par(tot_params["sortBy"])
    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice, filtro per avere solo i dati di quella org
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return {"list": [], "total": 0}
        params["organization"] = organization
    else:  # nel caso in cui l'utente sia dell'org coordinatrice può filtrare per identifier dell'org
        org_name = None
        org_filter = tot_params["organization"]
        if org_filter is not None:
            try:
                org_name = get_organization_by_id(org_filter, search)["name"]
            except:
                return {"list": [], "total": 0}
            params["organization"] = org_filter

    # Controllo se c'è il filtro sul gender
    if tot_params["pz_sesso"] is not None:
        if tot_params["pz_sesso"] == "1":
            params["gender"] = "female"
        elif tot_params["pz_sesso"] == "2":
            params["gender"] = "male"

    # trovare date_init e date_end sulla base della fascia d'etè che è salvata in pz_eta [eta_min, eta_max]
    if tot_params["pz_eta"] and len(tot_params["pz_eta"]) == 2:
        eta_min = tot_params["pz_eta"][0]
        eta_max = tot_params["pz_eta"][1]

        # Calcola le date di nascita massime e minime
        today = datetime.today()
        date_init = (today - timedelta(days=eta_max * 365.25)).strftime('%Y-%m-%d')  # Data minima (età massima)
        date_end = (today - timedelta(days=eta_min * 365.25)).strftime('%Y-%m-%d')  # Data massima (età minima)
        params["birthdate"] = "ge" + date_init + "&birthdate=lt" + date_end

    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=params,
        fhir_paths=pat_fhir_paths,
        num_pages=-1
    )
    if isinstance(patients_df, pd.DataFrame):
        patients_df = resolve_resource_id_reference_patient(search, patients_df, org_name)
        patients_df = get_patient_obx(search, pd.DataFrame(patients_df), is_stratify, tot_params, get_all=False)
        # Implementa gli altri possibili filtri 
        patients_df = apply_filters(patients_df, tot_params)
        total = len(patients_df)
        if is_stratify:
            patients_df = [corr["identifier"] for corr in patients_df]
            return patients_df
        return {"list": patients_df, "total": total}
    else:
        if is_stratify:
            return []
        return {"list": [], "total": 0}


def delete_patient_util(id, search, organization):
    logger.debug("delete patient by id")

    request_params = {"_id": id, "organization" : organization}
    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=request_params,
        fhir_paths=pat_fhir_paths
    )
    if isinstance(patients_df, pd.DataFrame):
        ## TROVARE LISTA DI EEG E DICOM PER POTER CANCELLARE I DATI DA S3 E ORTHANC
        s3_url_list = get_all_s3_urls(id, search)
        dicom_uids_list = get_all_dicom_uids(id, search)
        
        response = requests.delete(f"{base_url}/Patient/{id}?_cascade=delete",
                               auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
        if not (response.status_code == 200 or response.status_code == 204):
            logger.error(f"Failed to delete patient with ID {id}.", response.status_code, response.text)
            raise Exception(response.text)
        ### CANCELLARE ANCHE LE RISORSE SU ORTHANC E SU S3 ASSOCIATE AL PAZIENTE
        S3_not_deleted = delete_all_s3_urls(s3_url_list)
        if S3_not_deleted:
            logger.error(f"Failed to delete file from s3 with urls {S3_not_deleted}.")
        dicom_not_deleted = delete_all_dicom_uids(dicom_uids_list)
        if dicom_not_deleted:
            logger.error(f"Failed to delete DICOM file from orthanc with uids {dicom_not_deleted}.")
    else:
        raise Exception("Cancellazione non eseguita: risorsa non trovata (404)")

    

def get_sort_par(sortBy: str):
    # [_content, _id, _lastUpdated, _profile, _security, _source, _tag, _text, active, address, address-city, address-country, 
    # address-postalcode, address-state, address-use, birthdate, death-date, deceased, email, family, gender, general-practitioner, 
    # given, identifier, language, link, name, organization, phone, phonetic, telecom]"

    # noi possiamo ricevere: _id, birthdate, gender, identifier
    if sortBy.endswith("_id") or sortBy.endswith("birthdate") or sortBy.endswith("gender") or sortBy.endswith(
            "identifier"):
        return sortBy

    return "_id"


def search_patient_hapi_fhir(patient_input, search, organization):

    logger.debug("search patient by filter")

    tot_params = patient_input.dict()

    count = tot_params["count"]
    n_page = tot_params["nPage"]
    sort_by = get_sort_par(tot_params["sortBy"])
    num_pages = 1
    offset = n_page * count

    # Inizializzazione dei parametri della query in pyrate
    params = {}

    # Aggiungo i par. per la paginazione
    if count == -1:
        num_pages = -1
    else:
        params["_count"] = count
        params["_offset"] = offset
    params["_sort"] = sort_by

    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice, filtro per avere solo i dati di quella org
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return {"list": [], "total": 0}
        params["organization"] = organization
    else:  # nel caso in cui l'utente sia dell'org coordinatrice può filtrare per identifier dell'org
        org_name = None
        org_filter = tot_params["organization"]
        if org_filter is not None:
            try:
                org_name = get_organization_by_id(org_filter, search)["name"]
            except:
                return {"list": [], "total": 0}
            params["organization"] = org_filter


    # trovare date_init e date_end sulla base della fascia d'etè che è salvata in pz_eta [eta_min, eta_max]
    if tot_params["pz_eta"] and len(tot_params["pz_eta"]) == 2:
        eta_min = tot_params["pz_eta"][0]
        eta_max = tot_params["pz_eta"][1]

        # Calcola le date di nascita massime e minime
        today = datetime.today()
        date_init = (today - timedelta(days=eta_max * 365.25)).strftime('%Y-%m-%d')  # Data minima (età massima)
        date_end = (today - timedelta(days=eta_min * 365.25)).strftime('%Y-%m-%d')  # Data massima (età minima)
        params["birthdate"] = "ge" + date_init + "&birthdate=lt" + date_end

    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=params,
        fhir_paths=pat_fhir_paths,
        num_pages=num_pages
    )

    if isinstance(patients_df, pd.DataFrame):
        params["_summary"] = "count"
        params["_total"] = "accurate"
        total_count = list(search.steal_bundles(
            resource_type="Patient",
            request_params=params,
            num_pages=-1
        ))[0].total

        patients_df = resolve_resource_id_reference_patient(search, patients_df, org_name)
        patients_df = get_patient_obx(search, pd.DataFrame(patients_df))
        return {"list": patients_df, "total": total_count}
    else:
        return {"list": [], "total": 0}


def get_patient_list_full_full(search, organization):
   
    logger.debug("get all patients query")

    request_params = {}
    org_name = None
    if organization != coord_id:
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return []
        request_params["organization"] = organization
    patients_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params=request_params,
        fhir_paths=pat_fhir_paths
    )
    if isinstance(patients_df, pd.DataFrame):
        patients_df = resolve_resource_id_reference_patient(search, patients_df, org_name)
        patients_df = get_patient_obx(search, pd.DataFrame(patients_df))
        return patients_df
    else:
        return []


def get_pat_identifier(pat_id, search):
    pat_df = search.steal_bundles_to_dataframe(
        resource_type="Patient",
        request_params={"_id": pat_id},
        fhir_paths=[("identifier", "identifier.value")]
    )
    if isinstance(pat_df, pd.DataFrame):
        return pat_df.to_dict("records")[0]["identifier"]
    else:
        return None