import pandas as pd
import numpy as np
from app.config.logger import logger
from app.resources.mapping_patient_fields import ethnicity_mapping, lavoro_mapping, fumatore_mapping, \
    observations_mapping, conditions_mapping


# Filtra il DataFrame in base ai parametri di ricerca
def apply_filters(df, params):
    df = pd.DataFrame(df)
    for key, value in params.items():
        if key == "pz_bmi" and value and len(value) == 2:
            df = df[(df["BMI"] >= value[0]) & (df["BMI"] <= value[1])]
        elif key == "an_rem_patologie" and value:
            for condition in value:
                df = df[df[condition] == True]
        elif key in ["ric_set_attuale", "ric_lato_affetto",
                     "ev_ac_i_localizzazione", "ev_ac_i_bamford",
                     "ev_ac_i_toast", "ev_ac_i_trombectomia",
                     "ev_ac_i_fibrinolisi", "ev_ac_i_complicazioni",
                     "ev_ac_e_localizzazione", "ev_ac_e_nhc"]:
            if value is not None:
                df = df[df[key] == value]
        elif key == "pz_dominanza" and value:  # 1 destra, 2 sinistra
            key = "dominanza"
            if value == "2":
                value = "Left"
            else:
                value = "Right"
            df = df[df[key] == value]
        elif key == "pz_etnia" and value:
            key = "etnia"
            value = ethnicity_mapping[value]
            df = df[df[key] == value]
        elif key == "pz_stato_lavoro" and value:
            key = "statoLavoro"
            value = lavoro_mapping[value]
            df = df[df[key] == value]
        elif key == "paz_fumo" and value:
            key = "fumatore"
            value = fumatore_mapping[value]
            df = df[df[key] in value]
        elif key == "pz_riabilitazione" and value:  # 0 robotica, 1 tradizionale
            key = "riabilitazione"
            if value == "0":
                value = "Robotica"
            elif value == "1":
                value = "Tradizionale"
            df = df[df[key] == value]

        elif key == "ric_quadro_clinico" and value:
            for clinical_code in value:
                df = df[df[clinical_code] == "1"]

        elif key == "ev_ac_tipo" and value:
            key = "eventoAcuto"
            if value == "1":
                value = "Evento Acuto Ischemico"
            elif value == "2":
                value = "Evento Acuto Emorragico"
            df = df[df[key] == value]

    df = df.replace([np.inf, -np.inf, np.nan], None)
    response = df.to_dict("records")

    return response


def get_patient_obx(search, df, is_stratify=False, params={}, get_all=False,
                    observations_mapping=observations_mapping, conditions_mapping=conditions_mapping):
    """
    Funzione per ottenere e arricchire il DataFrame del paziente unendo le observation (ed eventuali altre risorse)
    a partire dai parametri di ricerca. La funzione esegue diversi merge sul DataFrame, utilizzando la funzione
    generica merge_resource per ridurre ripetizioni.
    """

    def merge_resource(search, df, resource_type, df_constraints, fhir_paths, request_params,
                       new_column, rename_map, with_columns=["id"], set_true=False):
        """
        Funzione generica per eseguire una ricerca con trade_rows_for_dataframe e unire i risultati al DataFrame df.
        
        Parametri:
        - search: l'istanza del client FHIR pyrate
        - df: DataFrame di partenza
        - resource_type: tipo di risorsa FHIR (es. "Observation", "Condition", "ResearchSubject")
        - df_constraints: dizionario dei vincoli sul DataFrame (es. {"subject": "id"})
        - fhir_paths: lista (o singolo valore) dei percorsi FHIR da estrarre
        - request_params: parametri di ricerca da passare
        - new_column: nome della colonna da aggiungere a df
        - rename_map: mappatura per rinominare le colonne restituite (es. {"valueQuantity.value": new_column, "valueCodeableConcept.text": new_column})
        - with_columns: colonne da mantenere nel risultato (default ["id"])
        - set_true: se True, imposta il valore della colonna a True (utile per le condizioni)
        
        Restituisce:
        df aggiornato con la nuova colonna
        """
        resource_df = search.trade_rows_for_dataframe(
            df=df,
            resource_type=resource_type,
            df_constraints=df_constraints,
            fhir_paths=fhir_paths,
            request_params=request_params,
            with_ref=False,
            with_columns=with_columns,
        )
        if isinstance(resource_df, dict):
            resource_df = pd.DataFrame(resource_df)
        if not resource_df.empty:
            resource_df = resource_df.rename(columns=rename_map)
            if set_true:
                resource_df[new_column] = True
            df = df.merge(resource_df[["id", new_column]], on="id", how="left")
        else:
            df[new_column] = None
        return df

    # Copia dell'input originale
    complete_df = df.copy()

    # Merge per Altezza e Peso (se non in modalità stratificazione)
    if not is_stratify:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("altezza", "valueQuantity.value")],
            request_params={"code:text": "Altezza"},
            new_column="altezza",
            rename_map={"valueQuantity.value": "altezza", "valueCodeableConcept.text": "altezza"}
        )
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("peso", "valueQuantity.value")],
            request_params={"code:text": "Peso"},
            new_column="peso",
            rename_map={"valueQuantity.value": "peso", "valueCodeableConcept.text": "peso"}
        )

    # Merge per BMI
    if not is_stratify or params.get("BMI"):
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("BMI", "valueQuantity.value")],
            request_params={"code:text": "BMI"},
            new_column="BMI",
            rename_map={"valueQuantity.value": "BMI", "valueCodeableConcept.text": "BMI"}
        )

    # Merge per Stato di fumatore
    if params.get("paz_fumo") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("fumatore", "valueCodeableConcept.text")],
            request_params={"code:text": "Stato di fumatore di tabacco"},
            new_column="fumatore",
            rename_map={"valueQuantity.value": "fumatore", "valueCodeableConcept.text": "fumatore"}
        )

    # Merge per Dominanza
    if params.get("pz_dominanza") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("dominanza", "valueCodeableConcept.text")],
            request_params={"code:text": "Dominance"},
            new_column="dominanza",
            rename_map={"valueQuantity.value": "dominanza", "valueCodeableConcept.text": "dominanza"}
        )

    # Merge per Etnia
    if params.get("pz_etnia") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("etnia", "valueCodeableConcept.text")],
            request_params={"code:text": "Ethnicity"},
            new_column="etnia",
            rename_map={"valueQuantity.value": "etnia", "valueCodeableConcept.text": "etnia"}
        )

    # Merge per Stato Lavoro
    if params.get("pz_stato_lavoro") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("statoLavoro", "valueCodeableConcept.text")],
            request_params={"code:text": "Work Status"},
            new_column="statoLavoro",
            rename_map={"valueQuantity.value": "statoLavoro", "valueCodeableConcept.text": "statoLavoro"}
        )

    # Merge per Riabilitazione dalla risorsa ResearchSubject
    if not is_stratify or params.get("pz_riabilitazione"):
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="ResearchSubject",
            df_constraints={"individual": "id"},
            fhir_paths=["actualArm"],
            request_params={},
            new_column="riabilitazione",
            rename_map={"actualArm": "riabilitazione"}
        )

    # Merge per condizioni (an_rem_patologie)
    an_rem_patologie = params.get("an_rem_patologie")
    if an_rem_patologie or get_all:
        # Filtra le condizioni se sono specificate nei parametri
        if an_rem_patologie:
            conditions_mapping = [cor for cor in conditions_mapping if cor["display"] in an_rem_patologie]
        for condition in conditions_mapping:
            complete_df = merge_resource(
                search,
                complete_df,
                resource_type="Condition",
                df_constraints={"subject": "id"},
                fhir_paths=["code"],
                request_params={"code": condition["code"]},
                new_column=condition["display"],
                rename_map={"code": condition["display"]},
                set_true=True
            )

    # Merge per osservazioni relative a ric_set_attuale e ric_lato_affetto
    if params.get("ric_set_attuale") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("ric_set_attuale", "valueCodeableConcept.coding.code")],
            request_params={"code": "ric_set_attuale"},
            new_column="ric_set_attuale",
            rename_map={"valueQuantity.value": "ric_set_attuale", "valueCodeableConcept.coding.code": "ric_set_attuale"}
        )
    if params.get("ric_lato_affetto") or get_all:
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Observation",
            df_constraints={"subject": "id"},
            fhir_paths=[("ric_lato_affetto", "valueCodeableConcept.coding.code")],
            request_params={"code": "ric_lato_affetto"},
            new_column="ric_lato_affetto",
            rename_map={"valueQuantity.value": "ric_lato_affetto",
                        "valueCodeableConcept.coding.code": "ric_lato_affetto"}
        )

    # Merge per Ric Quadro Clinico (usando il mapping delle observation)
    ric_quadro_clinico = params.get("ric_quadro_clinico")
    if ric_quadro_clinico or get_all:
        # Se specificato, filtra le osservazioni da considerare
        if ric_quadro_clinico:
            observations_mapping_filtered = [cor for cor in observations_mapping if cor["code"] in ric_quadro_clinico]
        else:
            observations_mapping_filtered = observations_mapping
        for observation in observations_mapping_filtered:
            complete_df = merge_resource(
                search,
                complete_df,
                resource_type="Observation",
                df_constraints={"subject": "id"},
                fhir_paths=[(observation["code"], "valueCodeableConcept.coding.code")],
                request_params={"code": observation["code"]},
                new_column=observation["code"],
                rename_map={"valueQuantity.value": observation["code"],
                            "valueCodeableConcept.coding.code": observation["code"]}
            )

    # Merge per Evento Acuto (dalla risorsa Condition)
    if not is_stratify or params.get("ev_ac_tipo"):
        complete_df = merge_resource(
            search,
            complete_df,
            resource_type="Condition",
            df_constraints={"subject": "id"},
            fhir_paths=["code.coding.display"],
            request_params={"code:text": "Evento Acuto"},
            new_column="eventoAcuto",
            rename_map={"code.coding.display": "eventoAcuto"}
        )

    # Merge per le localizzazioni e altri campi dell'evento acuto
    for field in ["ev_ac_i_localizzazione", "ev_ac_e_localizzazione", "ev_ac_i_bamford",
                  "ev_ac_i_toast", "ev_ac_i_trombectomia", "ev_ac_i_fibrinolisi",
                  "ev_ac_i_complicazioni", "ev_ac_e_nhc"]:
        if params.get(field) or get_all:
            complete_df = merge_resource(
                search,
                complete_df,
                resource_type="Observation",
                df_constraints={"subject": "id"},
                fhir_paths=[(field, "valueCodeableConcept.coding.code")],
                request_params={"code": field},
                new_column=field,
                rename_map={"valueQuantity.value": field, "valueCodeableConcept.coding.code": field}
            )

    
    # Sostituisci eventuali valori infiniti o NaN con None
    complete_df = complete_df.replace([np.inf, -np.inf, np.nan], None)
    response = complete_df.to_dict("records")
    logger.debug(f"Complete DataFrame: {response}")
    return response
