import pandas as pd
import numpy as np
from app.functions.organization_utils import get_organization_by_id
from app.functions.reference_utils import resolve_resource_id_reference_observation
from app.functions.s3_utils import delete_s3_file, load_s3_file
import requests, os
from dotenv import load_dotenv
from app.config.logger import logger

load_dotenv()

# Lettura dell'url del server hapi e dell'identifier dell'organizzazione coordinatrice (vede tutti i dati)
base_url = os.getenv("BASE_URL")
coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

obs_fhir_paths = ["id",
                  ("Patient ID", "subject.reference"),
                  ("name", "code.text"),
                  ("value", "valueQuantity.value"),
                  ("unit", "valueQuantity.unit"),
                  ("Device ID", "device.reference"),
                  ("date", "effectiveDateTime"),
                  ("Encounter ID", "encounter.reference"),
                  ("Rehab Center ID", "performer.reference"),
                  ("valueCode", "valueCodeableConcept.coding.display"),
                  ("channelLabels", "note.text"),
                  ("identifier", "identifier.value"),
                  ("component")
                  ]


mappingSortBy = {
    'code': 'name',
    'value-quantity': 'value',
    'patient': 'Patient ID',
    'encounter': 'Encounter ID',
    'date': 'date'
}


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


def search_observation_for_stratification(observation_input, search, organization):
    # Funzione che riceve la lista degli deintiferi dei pazienti, il nome della obs da trovare, il nome del timepoint (encounter)
    # ritorna la lista di dict delle obx che contengono chiavi patient (identifier) e value (il valore della obx)
    logger.debug("search observation by filter for startification")

    tot_params = observation_input.dict()
    req_params = {}
    if organization != coord_id:
        req_params["service-provider"] = organization

    patient_filter = tot_params.get("patients")  # lista di id di pazienti
    event_name = tot_params.get("encounter_name")
    obx_code = tot_params.get("code")

    if patient_filter and event_name and obx_code:
        req_params["class:text"] = event_name
        patient_df = pd.DataFrame(patient_filter, columns=["patient"])
        # cerco gli encounter scelti per i pazienti scelti
        merged_df = search.trade_rows_for_dataframe(
            df=patient_df,
            resource_type="Encounter",
            df_constraints={"subject.identifier": "patient"},
            fhir_paths=["id"],
            request_params=req_params,
            with_ref=False,
            with_columns=["patient"],
        )

        # Verifica se il risultato è un DataFrame
        if isinstance(merged_df, pd.DataFrame):
            # cerco le obx scelte negli encounter trovati prima
            merged_df = search.trade_rows_for_dataframe(
                df=merged_df,
                resource_type="Observation",
                df_constraints={"encounter": "id"},
                fhir_paths=[("value", "valueQuantity.value")],
                request_params={"code": obx_code},
                with_ref=False,
                with_columns=["patient"],
            )

            merged_df = merged_df.replace([np.inf, -np.inf, np.nan], None)
            merged_df = merged_df.drop("id", axis=1)
            merged_df = merged_df.to_dict("records")
        else:
            merged_df = []
    else:
        merged_df = []

    return merged_df


def get_obx_by_encounter(encounter_id, search, organization):
    # Viene usata nel veritcale degli encounter per aprire il menu a tendina che contiene tutte le obx di uno specifico encounter
    logger.debug("search observation by filtering on encounter_id")

    params = {}
    params["encounter"] = encounter_id

    org_name = None
    if organization != coord_id:
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return []
        params["performer"] = organization

    params["_count"] = 100

    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params=params,
        fhir_paths=obs_fhir_paths,
        num_pages=-1
    )
    if isinstance(observations_df, pd.DataFrame):
        observations_df = resolve_resource_id_reference_observation(search, observations_df, org_name)
    else:
        observations_df = []

    return observations_df


def search_observation_hapi_fhir(observation_input, search, organization, show_eeg=False, show_mvnx = False, show_robot = False):
    # Questa viene usata nel verticale delle obx, è possibile filtrare la ricerca
    logger.debug("search observation by filter")

    tot_params = observation_input.dict()

    count = tot_params["count"]
    n_page = tot_params["nPage"]
    sort_by = tot_params["sortBy"]
    num_pages = 1
    offset = n_page * count

    params = {}

    # Aggiungo il filtro sulla organization
    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return {"list": [], "total": 0}
        params["performer"] = organization
    else:  # nel caso in cui l'utente sia dell'org coordinatrice può filtrare per identifier dell'org
        org_name = None
        org_filter = tot_params["organization"]
        if org_filter is not None:
            try:
                org_name = get_organization_by_id(org_filter, search)["name"]
            except:
                return {"list": [], "total": 0}
            params["performer"] = org_filter

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
    patient_filter = tot_params.get("patient")
    if patient_filter:
        pat_identifier = get_pat_identifier(patient_filter, search)
        params["patient"] = patient_filter

    encounter_name = tot_params.get("encounter_name")

    params["_sort"] = sort_by
    if count == -1:
        num_pages = -1
    else:
        params["_count"] = count
        params["_offset"] = offset

    # Controllo se la chiamata è per vedere gli eeg o meno
    if not show_eeg and not show_mvnx and not show_robot:
        ## Tolgo le observation con code=EEG e code=MVNX se non sono nel verticale degli eeg e dei mvnx
        params["code:not"] = ["24708-6", "93042-4", "1303930001"] # and "93042-4"
        if tot_params["name"] is not None:
            params["code:text"] = tot_params["name"]
    elif show_eeg and not show_mvnx and not show_robot:  # se è per vedere gli eeg, metto il filtro
        params["code"] = "24708-6"
    elif show_mvnx and not show_eeg and not show_robot:  # se è per vedere gli mvnx, metto il filtro
        params["code"] = "93042-4"
    elif show_robot and not show_eeg and not show_mvnx:  # se è per vedere i dati robot, metto il filtro
        params["code"] = "1303930001"

    # Aggiungo il filtro per encounter_name
    if encounter_name:
        params["encounter:Encounter.class:text"] = encounter_name

    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params=params,
        fhir_paths=obs_fhir_paths,
        num_pages=num_pages
    )
    params["_summary"] = "count"
    params["_total"] = "accurate"
    total_count = list(search.steal_bundles(
        resource_type="Observation",
        request_params=params,
        num_pages=-1
    ))[0].total

    if isinstance(observations_df, pd.DataFrame):
        observations_df = resolve_resource_id_reference_observation(search, observations_df, org_name, pat_identifier,
                                                                    show_eeg=show_eeg,show_mvnx=show_mvnx)
        return {"list": observations_df, "total": total_count}
    else:
        return {"list": [], "total": 0}


def delete_observation_util(id, search, organization):
    logger.debug("delete observation by id")
    # Check che la risorsa che si vuole cancellare sia effettivamente associata all'organizzazione dell'utente che ha fatto la chiamata
    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params={
            "_id": id,
        },
        fhir_paths=["id",  
                    ("Rehab Center ID", "performer.reference"), 
                    ("code", "code.coding.code"),
                    ("docref", "derivedFrom.reference")]
        )
    
    if isinstance(observations_df, pd.DataFrame):
        obs_dict = observations_df.iloc[0]
        # Al momento anche utenti della org coord possono cancellare solo risorse della proprio org
        if obs_dict["Rehab Center ID"] != "Organization/" + organization:
            raise Exception(
                "Cancellazione non eseguita: risorsa di un'organizzazione diversa da quella dell'utente (403)")
    else:
        raise Exception("Cancellazione non eseguita: risorsa non trovata (404)")
    
    response = requests.delete(f"{base_url}/Observation/{id}?_cascade=delete",
                               auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if not (response.status_code == 200 or response.status_code == 204):
        logger.error(f"Failed to delete Observation with ID {id}.")
        raise Exception(response.text)
    
    # Se l'obx è di un EEG o XSENS, cancello la risorsa Document Reference associata e il file salvato sul bucket s3
    if obs_dict["code"] == "24708-6" or obs_dict["code"] == "93042-4":
        docref_id = obs_dict["docref"].split("/")[-1]
        docref_df = search.steal_bundles_to_dataframe(
            resource_type="DocumentReference",
            request_params={"_id": docref_id},
            fhir_paths=[("url", "content.attachment.url")]
        )
        if isinstance(docref_df, pd.DataFrame):
            url = docref_df.iloc[0]["url"]
            deleted = delete_s3_file(url)
            if deleted:
                response = requests.delete(f"{base_url}/DocumentReference/{docref_id}?_cascade=delete", auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
                if not (response.status_code == 200 or response.status_code == 204):
                    logger.error(f"Cancellazione della risorsa DocumentReference {docref_id} della obse {id} non avvenuta.")
            else:
                logger.error(f"Cancellazione del file su s3 {url} della risorsa {id} non correttamente avvenuta; non cancellazione della risorsa documentReference associata")
        else:
            logger.error(f"URL {url} dell'obs {id} non trovato, cancellazione del file nel bucket e della risorsa documentReference non avvenute")
    
    
def get_all_s3_urls(pat_id, search):
    docref_df = search.steal_bundles_to_dataframe(
        resource_type="DocumentReference",
        request_params={"patient": pat_id},
        fhir_paths=[("url", "content.attachment.url")]
    )
    if isinstance(docref_df, pd.DataFrame):
        urls = list(docref_df["url"])
        return urls
    return []


def download_from_s3_by_id(obx_id, search, organization):
    """
    Scarica il file mvnx in formato mvnx indicato con mvnx_id
    """
    params = {}
    params["_id"] = obx_id
    if organization != coord_id:
        params["performer"] = coord_id
        
    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params=params,
        fhir_paths=[("docref", "derivedFrom.reference")]
    )
    if isinstance(observations_df, pd.DataFrame):
        docref_id = observations_df.iloc[0]["docref"].split("/")[-1]
        docref_df = search.steal_bundles_to_dataframe(
            resource_type="DocumentReference",
            request_params={"_id": docref_id},
            fhir_paths=[("url", "content.attachment.url")]
        )
        if isinstance(docref_df, pd.DataFrame):
            url = docref_df.iloc[0]["url"]
            file_buffer = load_s3_file(url)
            return file_buffer
        else:
            raise Exception(f"No url found for the provided the obx_id {obx_id}")
    else:
        raise Exception(f"No observation found for the provided obx_id {obx_id}")
    
    


def get_observation_by_id(id, search, organization):
    logger.debug("get observation by id")

    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params={
            "_id": id,
        },
        fhir_paths=obs_fhir_paths
    )
    if isinstance(observations_df, pd.DataFrame):
        observations_df = resolve_resource_id_reference_observation(search, observations_df)[0]
        if organization != coord_id:
            org_name = get_organization_by_id(organization, search)["name"]
            if observations_df["rehabCenter"] != org_name:
                return None
    else:
        observations_df = None
    return observations_df



def get_name_list(search, organization):
    request_params = {}
    if organization != coord_id:
        request_params["performer"] = organization
    observations_df = search.steal_bundles_to_dataframe(
        resource_type="Observation",
        request_params=request_params,
        fhir_paths=[("name", "code.text"), ]
    )
    if isinstance(observations_df, pd.DataFrame):
        name_values = observations_df["name"].values
        unique_names = set()
        for value in name_values:
            if isinstance(value, list):
                value = value[0]
            unique_names.add(value)
        names = list(unique_names)
    else:
        names = []
    return names
