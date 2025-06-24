import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Queste sono lette dal file di .env
aws_access_key_id = os.getenv("AWS_ACCESS_KEY")
aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
region_name = os.getenv("AWS_REGION")
bucket_name = os.getenv("AWS_BUCKET_NAME")
TEMP_PATH = os.getenv("TEMP_PATH")


def resolve_resource_id_reference_observation(search, df, org_name=None, pat_identifier=None, encounter_name=None,
                                              show_eeg=False, show_mvnx=False):
    def extract_id(val):
        if str(val) != "":
            return str(val).split('/')[1] if '/' in str(val) else None
        else:
            # Se non è una stringa, restituisce None 
            return None

    # Applica la funzione extract_id a ciascuna colonna pertinente
    df['Patient ID'] = df['Patient ID'].apply(extract_id)
    df['Rehab Center ID'] = df['Rehab Center ID'].apply(extract_id)
    if "Device ID" in df.columns:
        df['Device ID'] = df['Device ID'].apply(extract_id)
    else:
        df['Device ID'] = None
    if "Encounter ID" in df.columns:
        df['Encounter ID'] = df['Encounter ID'].apply(extract_id)
    else:
        df['Encounter ID'] = None
    
    # Gestisco separatamente l'eventuale colonna dei component che è presente nel caso di observation di segnali mvnx perchè altrimenti da errore sulle search
    component_col = None
    if "component" in df.columns: 
        component_col = df["component"]
        df = df.drop("component", axis=1)
    
    complete_df = df
    if pat_identifier is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Patient',
            df_constraints={"_id": "Patient ID"},
            fhir_paths=[("patient", "identifier.value")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["patient"] = pat_identifier
    

    if org_name is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Organization',
            df_constraints={"_id": "Rehab Center ID"},
            fhir_paths=[("rehabCenter", "name")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["rehabCenter"] = org_name
    complete_df = complete_df.drop("Rehab Center ID", axis=1)

    # Separa il DataFrame in due basati sulla presenza di None nella colonna Device ID
    df_with_none = complete_df[complete_df['Device ID'].isna()]
    df_without_none = complete_df[~complete_df['Device ID'].isna()]
    df_without_none = search.trade_rows_for_dataframe(
        df=df_without_none,
        resource_type='Device',
        df_constraints={"_id": "Device ID"},
        fhir_paths=[("device", "deviceName.name")],
        request_params={},
        with_ref=False,
        with_columns=list(df_without_none.keys()),
    )

    # nel df senza reference lascio None 
    df_with_none.loc[:, "device"] = df_with_none['Device ID']
    complete_df = pd.concat([pd.DataFrame(df_without_none), df_with_none])
    complete_df = complete_df.drop("Device ID", axis=1)

    if encounter_name is None:
        #Separa il DataFrame in due basati sulla presenza di None nella colonna Encounter ID
        df_with_none = complete_df[complete_df['Encounter ID'].isna()] 
        df_without_none = complete_df[~complete_df['Encounter ID'].isna()] 
        df_without_none = search.trade_rows_for_dataframe(
            df=df_without_none,
            resource_type='Encounter',
            df_constraints={"_id": "Encounter ID"},
            fhir_paths=[("encounter", "class.display")],
            request_params={},
            with_ref=False,
            with_columns=list(df_without_none.keys()),
        )
        # nel df senza reference lascio None 
        df_with_none.loc[:, "encounter"] = df_with_none['Encounter ID']

        # Unisco i dataframe e tolgo la colonna in più
        complete_df = pd.concat([pd.DataFrame(df_without_none), df_with_none])
        complete_df = complete_df.drop("Encounter ID", axis=1)
    else:
        complete_df["encounter"] = encounter_name

    if show_eeg:
        complete_df['channelLabels'] = complete_df['channelLabels'].apply(
            lambda x: x.split(";") if isinstance(x, str) else [])
    
    if show_mvnx and component_col is not None:
        complete_df["component"] = component_col.values
        complete_df['channelLabels'] = complete_df['component'].apply(
            lambda x: [el["code"]["text"] for el in x] if isinstance(x, list) else [])
        complete_df = complete_df.drop("component", axis=1)

    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")

    return response


def resolve_resource_id_reference_encounter(search, df, org_name=None, pat_identifier=None):
    def extract_id(val):
        if isinstance(val, str) and val != "":
            return val.split('/')[1] if '/' in val else ""
        else:
            # Se non è una stringa, restituisce None 
            return None

    df['Patient ID'] = df['Patient ID'].apply(extract_id)
    df['Rehab Center ID'] = df['Rehab Center ID'].apply(extract_id)

    # Separa le righe con e senza Patient ID
    df_with_patient_id = df[df['Patient ID'].notna()].copy()
    df_without_patient_id = df[df['Patient ID'].isna()].copy()

    # Risolvi Patient ID per le righe con valori validi
    if not df_with_patient_id.empty:
        if pat_identifier is None:
            df_with_patient_id = search.trade_rows_for_dataframe(
                df=df_with_patient_id,
                resource_type='Patient',
                df_constraints={"_id": "Patient ID"},
                fhir_paths=[("patient", "identifier.value")],
                request_params={},
                with_ref=False,
                with_columns=list(df_with_patient_id.keys()),
            )
        else:
            df_with_patient_id["patient"] = pat_identifier

    # Per le righe senza Patient ID, imposta patient a None
    df_without_patient_id["patient"] = None

    # Rimuovi la colonna Patient ID e unisci i DataFrame
    df_with_patient_id = df_with_patient_id.drop("Patient ID", axis=1, errors="ignore")
    df_without_patient_id = df_without_patient_id.drop("Patient ID", axis=1, errors="ignore")
    complete_df = pd.concat([df_with_patient_id, df_without_patient_id], ignore_index=True)

    if org_name is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Organization',
            df_constraints={"_id": "Rehab Center ID"},
            fhir_paths=[("rehabCenter", "name")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["rehabCenter"] = org_name
    complete_df = complete_df.drop("Rehab Center ID", axis=1)

    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")
    return response


def resolve_resource_id_reference_patient(search, df, org_name=None):
    df['Rehab Center ID'] = df['Rehab Center ID'].apply(lambda x: x.split('/')[1])
    if org_name is None:
        complete_df = search.trade_rows_for_dataframe(
            df=df,
            resource_type='Organization',
            df_constraints={"_id": "Rehab Center ID"},
            fhir_paths=[("rehabCenter", "name")],
            with_ref=False,
            with_columns=list(df.keys()),
        )
    else:
        complete_df = df
        complete_df["rehabCenter"] = org_name
    complete_df = complete_df.drop('Rehab Center ID', axis=1)
    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")
    return response


def resolve_resource_id_reference_imagingstudy(search, df, org_name=None, pat_identifier=None, encounter_name=None):
   
    def extract_id(val):
        if type(val) is list:
            val = val[0]
        if str(val) != "":
            return str(val).split('/')[1] if '/' in str(val) else None
        else:
            # Se non è una stringa, non ritorno None per evitare errori dopo con la manipolazione dei dati
            return "-"

    def concat_list(val):
        if isinstance(val, list):
            val = list(set(val))
            if "No Bodysite Available" in val:
                val.remove("No Bodysite Available")
            if "Unknown SOP Description" in val:
                val.remove("Unknown SOP Description")
            if len(val) == 1:
                return val[0]
            if len(val) == 0:
                return "-"
            return ','.join(val)
        return val

    def concat_list_series(val):
        if isinstance(val, str):
            temp = []
            temp.append(val)
            val = temp
        if isinstance(val, list):
            val = list(set(val))
            if "No Bodysite Available" in val:
                val.remove("No Bodysite Available")
            if "Unknown SOP Description" in val:
                val.remove("Unknown SOP Description")
            if len(val) == 1:
                return val[0]
            if len(val) == 0:
                return "-"
            return ','.join(val)
        return val

    def split_string(val):
        if isinstance(val, str):
            return val.split(',')
        return val

    # Applica la funzione extract_id a ciascuna colonna pertinente
    df['Patient ID'] = df['Patient ID'].apply(extract_id)
    df['Rehab Center ID'] = df['Rehab Center ID'].apply(extract_id)
    df['Endpoint ID'] = df['Endpoint ID'].apply(extract_id)
    df['Encounter ID'] = df['Encounter ID'].apply(extract_id)
    if "bodysite" in df.columns:
        df['bodysite'] = df['bodysite'].apply(concat_list)
    if "modality" in df.columns:
        df['modality'] = df['modality'].apply(concat_list)
    if "series" in df.columns:
        df['series'] = df['series'].apply(concat_list_series)

    complete_df = df

    # Risolvo il campo Patient ID per ottenere l'identifier del paziente
    if pat_identifier is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Patient',
            df_constraints={"_id": "Patient ID"},
            fhir_paths=[("patient", "identifier.value")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["patient"] = pat_identifier
    complete_df = complete_df.drop("Patient ID", axis=1)

    # Risolvo il campo Rehab Center ID per ottenere il nome dell'organization
    if org_name is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Organization',
            df_constraints={"_id": "Rehab Center ID"},
            fhir_paths=[("rehabCenter", "name")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["rehabCenter"] = org_name
    complete_df = complete_df.drop("Rehab Center ID", axis=1)

    # Risolvo il campo Encounter ID per ottenere il nome dell'encounter
    if encounter_name is None:
        complete_df = search.trade_rows_for_dataframe(
            df=complete_df,
            resource_type='Encounter',
            df_constraints={"_id": "Encounter ID"},
            fhir_paths=[("encounter", "class.display")],
            request_params={},
            with_ref=False,
            with_columns=list(complete_df.keys()),
        )
    else:
        complete_df["encounter"] = encounter_name
    complete_df = complete_df.drop("Encounter ID", axis=1)

    # Risolvo il campo Encounter ID per ottenere il full url
    complete_df = search.trade_rows_for_dataframe(
        df=complete_df,
        resource_type='Endpoint',
        df_constraints={"_id": "Endpoint ID"},
        fhir_paths=[("endpoint", "address")],
        request_params={},
        with_ref=False,
        with_columns=list(complete_df.keys()),
    )
    complete_df = complete_df.drop("Endpoint ID", axis=1)

    # Ripristino series in modo che sia una lista di stringhe
    complete_df['series'] = complete_df['series'].apply(split_string)

    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")

    return response


# DA TESTARE CON DATI TECNOBODY
def resolve_device_id_reference(search, df):
    def extract_id(val):
        if str(val) != "":
            return str(val).split('/')[1] if '/' in str(val) else None
        else:
            # Se non è una stringa, restituisce None 
            return None

    # Applica la funzione extract_id a ciascuna colonna pertinente
    if "Device ID" in df.columns:
        df['Device ID'] = df['Device ID'].apply(extract_id)
    else:
        df['Device ID'] = None
    complete_df = df

    # Separa il DataFrame in due basati sulla presenza di None nella colonna Devici ID
    df_with_none = complete_df[complete_df['Device ID'].isna()]  
    df_without_none = complete_df[~complete_df['Device ID'].isna()]  

    df_without_none = search.trade_rows_for_dataframe(
        df=df_without_none,
        resource_type='Device',
        df_constraints={"_id": "Device ID"},
        fhir_paths=[("device", "deviceName.name")],
        request_params={},
        with_ref=False,
        with_columns=list(df_without_none.keys()),
    )

    # nel df senza reference lascio None 
    df_with_none.loc[:, "device"] = df_with_none['Device ID']
    complete_df = pd.concat([pd.DataFrame(df_without_none), df_with_none])
    complete_df = complete_df.drop("Device ID", axis=1)

    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")

    return response
