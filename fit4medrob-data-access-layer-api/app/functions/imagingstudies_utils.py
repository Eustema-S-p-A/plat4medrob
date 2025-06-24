from app.functions.reference_utils import resolve_resource_id_reference_imagingstudy
import pandas as pd
import io, zipfile
from app.functions.organization_utils import get_organization_by_id
import requests, os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from app.config.logger import logger
import base64
import asyncio


load_dotenv()

# Lettura dell'url del server hapi e dell'identifier dell'organizzazione coordinatrice (vede tutti i dati)
base_url = os.getenv("BASE_URL")
coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

ORTHANC_URL = os.getenv("ORTHANC_URL")
DICOM_WEB_URL = ORTHANC_URL + '/dicom-web'
dicom_server_user = os.getenv("ORTHANC_SERVER_USER")
dicom_server_psw = os.getenv("ORTHANC_SERVER_PSW")

fhir_paths = ["id",
              ("Patient ID", "subject.reference"),
              ("identifier", "identifier.value"),
              ("date", "started"),
              "numberOfSeries",
              "numberOfInstances",
              ("modality", "modality.display"),
              ("bodysite", "series.bodySite.display"),
              ("Rehab Center ID", "series.performer.actor.reference"),
              ("series", "series.uid"),
              ("Endpoint ID", "endpoint.reference"),
              ("Encounter ID", "encounter.reference")
              ]
images_fhir_paths = [
    "id",
    ("identifier", "identifier.value"),
    ("series_instance_uid", "series.uid"),
    ("numberOfInstances", "series.numberOfInstances"),
    ("Endpoint ID", "endpoint.reference"),
    ("Rehab Center ID", "series.performer.actor.reference"),
]

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
    
def search_imagingstudy_hapi_fhir(input, search, organization):
    logger.debug("search imagingstudy by filter")

    tot_params = input.dict()

    count = tot_params["count"]
    n_page = tot_params["nPage"]
    sort_by = get_sort_par(tot_params["sortBy"])
    num_pages = 1
    offset = n_page * count

    params = {}

    if organization != coord_id:  # se l'utente non è dell'organizzazion coordinatrice, filtro per avere solo i dati di quella org
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
            params["performer"] = organization

    # Aggiungo i filtri per modality e per bodysite    
    if tot_params["modality"] is not None:
        params["modality:text"] = tot_params["modality"]

    if tot_params["bodysite"] is not None:
        params["bodysite:text"] = tot_params["bodysite"]

        # Aggiungo il parametro per data di inizio e di fine
    if tot_params["date_init"] is not None:
        date_init = str(tot_params["date_init"])[:10]
        params["date"] = "ge" + date_init
    if tot_params["date_end"] is not None:
        date_end = str(tot_params["date_end"])[:10]
        if tot_params["date_init"] is not None:
            params["date"] = "ge" + date_init + "&date=lt" + date_end
        else:
            params["date"] = "lt" + date_end

    # Aggiungo il filtro per identifier del patient
    pat_identifier = None
    if tot_params["patient"] is not None:
        params["patient"] = tot_params["patient"]
        pat_identifier = get_pat_identifier(tot_params["patient"], search)

    # Aggiungo il filtro per encounter_name
    encounter_name = tot_params.get("encounter_name")
    if encounter_name:
        params["encounter:Encounter.class:text"] = encounter_name

    # Aggiungo i par. per la paginazione
    if count == -1:
        num_pages = -1
    else:
        params["_count"] = count
        params["_offset"] = offset
    params["_sort"] = sort_by

    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=params,
        fhir_paths=fhir_paths,
        num_pages=num_pages
    )

    if isinstance(imagingstudies_df, pd.DataFrame):
        # Trovo il numero totale di risorse per riempire il contatore nel frontend
        params["_summary"] = "count"
        params["_total"] = "accurate"
        total_count = list(search.steal_bundles(
            resource_type="ImagingStudy",
            request_params=params,
            num_pages=-1
        ))[0].total

        imagingstudies_df = resolve_resource_id_reference_imagingstudy(search, imagingstudies_df, org_name,
                                                                       pat_identifier,
                                                                       encounter_name)

        return {"list": imagingstudies_df, "total": total_count}
    else:
        return {"list": [], "total": 0}


def get_modality_list(search, organization):
    request_params = {}
    if organization != coord_id:
        request_params["performer"] = organization
    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=request_params,
        fhir_paths=[("modality", "modality.display")]
    )
    if isinstance(imagingstudies_df, pd.DataFrame):
        modality_values = imagingstudies_df["modality"].values
        unique_modalities = set()
        for value in modality_values:
            if isinstance(value, list):
                value = value[0]
            unique_modalities.add(value)
        modalities = list(unique_modalities)
        if "Unknown SOP Description" in modalities:
            modalities.remove("Unknown SOP Description")
    else:
        modalities = []
    return modalities


def get_bodysite_list(search, organization):
    request_params = {}
    if organization != coord_id:
        request_params["performer"] = organization
    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=request_params,
        fhir_paths=[("bodysite", "series.bodySite.display")]
    )
    if isinstance(imagingstudies_df, pd.DataFrame):
        bodysite_values = imagingstudies_df["bodysite"].values
        unique_bodysites = set()
        for value in bodysite_values:
            if isinstance(value, list):
                value = value[0]
            unique_bodysites.add(value)
        bodysites = list(unique_bodysites)
        if "No Bodysite Available" in bodysites:
            bodysites.remove("No Bodysite Available")
    else:
        bodysites = []
    return bodysites


async def get_images_by_id(study_uid, serie_uid, session, organization=None, compress_level="low"):
    """
    Recupera immagini DICOM da Orthanc con compressione ottimizzata mantenendo la compatibilità con il frontend.

    Args:
        study_uid: UID dello studio
        serie_uid: UID della serie
        session: Sessione client aiohttp
        organization: Organizzazione dell'utente
        compress_level: Livello di compressione ('low', 'medium', 'high')

    Returns:
        Lista di stringhe base64 rappresentanti i file DICOM compressi
    """
    # Set the base URL
    base_url = f"{DICOM_WEB_URL}/studies/{study_uid}/series/{serie_uid}/instances"

    # Make a request to get the list of instances
    async with session.get(base_url) as response:
        if response.status != 200:
            raise Exception(
                f"Failed to retrieve instances. Status code: {response.status}, Message: {await response.text()}")
        instances = await response.json()

    # Selezione del Transfer Syntax UID in base al livello di compressione
    transfer_syntax = None
    if compress_level == "low":
        # JPEG 2000 con perdita di qualità (alta compressione)
        transfer_syntax = "1.2.840.10008.1.2.4.91"
    elif compress_level == "medium":
        # JPEG con perdita di qualità (compressione media)
        transfer_syntax = "1.2.840.10008.1.2.4.51"
    elif compress_level == "high":
        # JPEG 2000 lossless (qualità alta, compressione minore)
        transfer_syntax = "1.2.840.10008.1.2.4.90"

    # Define a coroutine to fetch a single DICOM instance
    async def fetch_instance(instance):
        instance_id = instance["00080018"]["Value"][0]
        instance_url = f"{DICOM_WEB_URL}/studies/{study_uid}/series/{serie_uid}/instances/{instance_id}"

        # Headers per richiedere una specifica compressione mantenendo il formato DICOM
        headers = {}
        if transfer_syntax:
            headers["Accept"] = f"multipart/related; type=application/dicom; transfer-syntax={transfer_syntax}"
            headers["Prefer"] = "respond-single-application/dicom"
        async with session.get(instance_url, headers=headers) as instance_response:
            if instance_response.status != 200:
                raise Exception(
                    f"Failed to retrieve instance {instance_id}. Status code: {instance_response.status}, Message: {await instance_response.text()}")

            content = await instance_response.read()

            # Processiamo la risposta multipart se necessario
            if content.startswith(b'--'):
                mime_boundary = content.split(b'\r\n')[0]
                dicom_start = content.find(b'\r\n\r\n') + 4
                dicom_end = content.find(mime_boundary, dicom_start) - 2
                dicom_data = content[dicom_start:dicom_end]
            else:
                dicom_data = content

            return base64.b64encode(dicom_data).decode('utf-8')

    # Create tasks for all instance fetches and run them concurrently
    semaphore = asyncio.Semaphore(10)  # Limita le connessioni simultanee

    async def fetch_with_semaphore(instance):
        async with semaphore:
            return await fetch_instance(instance)

    tasks = [fetch_with_semaphore(instance) for instance in instances]
    dicom_blobs = await asyncio.gather(*tasks)

    return dicom_blobs


def get_image_urls_by_study(study_uid):
    """
    Recupera la lista degli URL delle immagini DICOM associate a uno study_uid su Orthanc.
    """
    base_url = f"{DICOM_WEB_URL}/studies/{study_uid}/series"
    auth = HTTPBasicAuth(os.getenv("ORTHANC_SERVER_USER"), os.getenv("ORTHANC_SERVER_PSW"))

    response = requests.get(base_url, auth=auth)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve series. Status code: {response.status_code}")

    series_list = response.json()
    image_urls = []

    for series in series_list:
        series_uid = series["0020000E"]["Value"][0]  # SeriesInstanceUID
        instances_url = f"{DICOM_WEB_URL}/studies/{study_uid}/series/{series_uid}/instances"

        response_instances = requests.get(instances_url, auth=auth)
        if response_instances.status_code != 200:
            continue

        instances = response_instances.json()
        for instance in instances:
            instance_uid = instance["00080018"]["Value"][0]  # SOPInstanceUID
            image_url = f"{DICOM_WEB_URL}/studies/{study_uid}/series/{series_uid}/instances/{instance_uid}"
            image_urls.append(image_url)

    return image_urls


def download_imagingstudy_by_id(study_id, search, organization):
    """
    Scarica tutte le immagini DICOM di uno studio ImagingStudy e le comprime in un file ZIP in memoria.
    """

    params = {}
    params["_id"] = study_id
    if organization != coord_id:
        params["performer"] = organization

    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=params,
        fhir_paths=images_fhir_paths
    )

    if imagingstudies_df.empty:
        raise Exception("ImagingStudy not found")

    study = imagingstudies_df.to_dict("records")[0]
    study_uid = study["identifier"]

    # recupera gli URL delle immagini DICOM dall'istanza Orthanc
    dicom_urls = get_image_urls_by_study(study_uid)

    if not dicom_urls:
        raise Exception("No images found for the study")

    # Crea un file ZIP in memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for url in dicom_urls:
            response = requests.get(url, auth=HTTPBasicAuth(
                os.getenv("ORTHANC_SERVER_USER"),
                os.getenv("ORTHANC_SERVER_PSW")
            ))
            if response.status_code == 200:
                file_name = url.split("/")[-1] + ".dcm"  # Estrai il nome del file dall'URL
                zip_file.writestr(file_name, response.content)
            else:
                raise Exception(f"Failed to download image from {url}")

    zip_buffer.seek(0)
    return zip_buffer


def delete_imagingstudy_util(id, search, organization):
    logger.debug("delete imagingstudy by id")

    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params={
            "_id": id,
        },
        fhir_paths=fhir_paths
    )
    if isinstance(imagingstudies_df, pd.DataFrame):
        imagingstudies_df = resolve_resource_id_reference_imagingstudy(search, imagingstudies_df)[0]

        org_name = get_organization_by_id(organization, search)["name"]
        if imagingstudies_df["rehabCenter"] != org_name:
            raise Exception(
                "Cancellazione non eseguita: risorsa di un'organizzazione diversa da quella dell'utente (403)")
    else:
        raise Exception("Cancellazione non eseguita: risorsa non trovata (404)")
    study_uid = imagingstudies_df["identifier"]
    response = requests.delete(f"{base_url}/ImagingStudy/{id}?_cascade=delete",
                               auth=(os.getenv("FHIR_USER"), os.getenv("FHIR_PASSWORD")))
    if response.status_code == 200 or response.status_code == 204:
        response = delete_study_from_orthanc(study_uid)
        if not (response.status_code == 200 or response.status_code == 204):
            logger.error(
                f"Failed to delete DICOM study in orthanc with {study_uid} and status_code {response.status_code}")
            raise Exception(response.text)
    else:
        logger.error(f"Failed to delete Observation with ID {id}")
        raise Exception(response.text)


def delete_study_from_orthanc(idStudy):
    import json
    data = {"Level": "Studies",
            "Query": {"StudyInstanceUID": idStudy}
            }
    jdata = json.dumps(data)

    response = requests.post(ORTHANC_URL + "/tools/find", data=jdata, auth=(dicom_server_user, dicom_server_psw))
    study_uid = response.json()[0]

    # Construct the URL for the DELETE request
    delete_url = f"{ORTHANC_URL}/studies/{study_uid}"
    response = requests.delete(delete_url, auth=(dicom_server_user, dicom_server_psw))
    return response

def get_all_dicom_uids(pat_id, search):
    """
    Recupera tutti gli StudyInstanceUID degli ImagingStudy associati a un paziente.

    """
    logger.debug(f"Recupero StudyInstanceUID per paziente {pat_id}")
    
    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params={"patient": pat_id},
        fhir_paths=[("identifier", "identifier.value")],
        num_pages=-1
    )

    if not isinstance(imagingstudies_df, pd.DataFrame) or imagingstudies_df.empty:
        return []

    return imagingstudies_df["identifier"].dropna().tolist()


def delete_all_dicom_uids(study_uids):
    """
    Elimina tutte le risorse DICOM su Orthanc dati gli uids

    """
    failed = []

    for uid in study_uids:
        try:
            response = delete_study_from_orthanc(uid)
            if response.status_code not in (200, 204):
                logger.error(f"Errore cancellazione studio {uid} - Status code: {response.status_code}")
                failed.append(uid)
        except Exception as e:
            logger.error(f"Eccezione durante la cancellazione dello studio {uid}: {e}")
            failed.append(uid)

    return failed



def get_sort_par(sortBy):
    # [_content, _id, _lastUpdated, _profile, _security, _source, _tag, _text, basedon, bodysite, dicom-class, encounter, endpoint, 
    # identifier, instance, interpreter, modality, patient, performer, reason, referrer, series, started, status, subject]

    # noi potremmo avere patient, date, encounter, device, value-quantity, code
    if sortBy.endswith("_id") or sortBy.endswith("date") or sortBy.endswith("patient") or sortBy.endswith("modality") \
            or sortBy.endswith("bodysite") or sortBy.endswith("identifier"):
        return sortBy

    return "_id"



def get_imagingstudy_list(search, organization):
    logger.debug("get all imagingstudy query")

    request_params = {}
    org_name = None
    
    if organization != coord_id:
        try:
            org_name = get_organization_by_id(organization, search)["name"]
        except:
            return []
        request_params["performer"] = organization
    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=request_params,
        fhir_paths=fhir_paths
    )
    if isinstance(imagingstudies_df, pd.DataFrame):
        imagingstudies_df = resolve_resource_id_reference_imagingstudy(search, imagingstudies_df, org_name)
    else:
        imagingstudies_df = []
    return imagingstudies_df


  
def get_imagingstudy_by_id(id, search, organization):
    logger.debug("get imagingstudy by id")

    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params={
            "_id": id,
        },
        fhir_paths=fhir_paths
    )
    if isinstance(imagingstudies_df, pd.DataFrame):
        imagingstudies_df = resolve_resource_id_reference_imagingstudy(search, imagingstudies_df)[0]
        if organization != coord_id:
            org_name = get_organization_by_id(organization, search)["name"]
            if imagingstudies_df["rehabCenter"] != org_name:
                return None
    else:
        imagingstudies_df = None
    return imagingstudies_df


def search_imagingstudy_hapi_fhir_nopag(input, search, organization):
    logger.debug("search imagingstudy by filter")

    tot_params = input.dict()

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

    # Aggiungo i filtri per modality e per bodysite    
    if tot_params["modality"] is not None:
        params["modality:text"] = tot_params["modality"]

    if tot_params["bodysite"] is not None:
        params["bodysite:text"] = tot_params["bodysite"]

        # Aggiungo il parametro per data di inizio e di fine
    if tot_params["date_init"] is not None:
        date_init = str(tot_params["date_init"])[:10]
        params["date"] = "ge" + date_init
    if tot_params["date_end"] is not None:
        date_end = str(tot_params["date_end"])[:10]
        if tot_params["date_init"] is not None:
            params["date"] = "ge" + date_init + "&date=lt" + date_end
        else:
            params["date"] = "lt" + date_end

    # Aggiungo il filtro per identifier del patient
    pat_identifier = None
    if tot_params["patient"] is not None:
        params["patient"] = tot_params["patient"]
        pat_identifier = get_pat_identifier(tot_params["patient"], search)

    # Aggiungo il filtro per encounter_name
    encounter_name = tot_params.get("encounter_name")
    if encounter_name:
        params["encounter:Encounter.class:text"] = encounter_name

    if tot_params["sortBy"] is not None:
        params["_sort"] = get_sort_par(tot_params["sortBy"])

    params["_count"] = 100
    imagingstudies_df = search.steal_bundles_to_dataframe(
        resource_type="ImagingStudy",
        request_params=params,
        fhir_paths=fhir_paths,
    )

    if isinstance(imagingstudies_df, pd.DataFrame):
        imagingstudies_df = resolve_resource_id_reference_imagingstudy(search, imagingstudies_df, org_name,
                                                                       pat_identifier,
                                                                       encounter_name)
    else:
        imagingstudies_df = []

    return imagingstudies_df


