"""
Router per le funzionalità di analisi dati.
Fornisce endpoint per analisi statistiche e generazione di report.
Utilizza direttamente il client HTTP asincrono.
"""
from typing import List, Union, Any, Dict
import asyncio
import aiohttp
import logging
import os
from app.schemas.stratification import AnalyticsRequest

# Configurazione
logger = logging.getLogger(__name__)
DATA_ACCESS_URL = os.getenv('DATA_ACCESS_SERVICE_URL')


async def _process_analytics_request(
        request: AnalyticsRequest,
        token: str,
        session: aiohttp.ClientSession,
        csv_format: bool = False
) -> Union[List[Dict[str, Any]], Any]:
    """
    Funzione helper per elaborare le richieste di analisi.
    Utilizza direttamente aiohttp per le chiamate API.

    Args:
        request: La richiesta di analisi
        token: Il token di autenticazione
        session: La sessione HTTP per le chiamate API
        csv_format: Se True, restituisce i dati in formato CSV

    Returns:
        I risultati dell'analisi

    """
    # Recupera i gruppi di pazienti
    patient_groups = await _get_grouped_patients(session, request.groups, token)

    # Ottieni gli outcome nel formato appropriato
    if csv_format:
        return await _get_patient_outcomes_csv(
            session, patient_groups, request.timings, request.output, token
        )
    else:
        return await _get_patient_outcomes(
            session, patient_groups, request.timings, request.output, token
        )


async def _get_grouped_patients(
        session: aiohttp.ClientSession,
        group_input: List[Any],
        token: str
) -> List[Dict[str, Any]]:
    """
    Recupera i pazienti raggruppati per i filtri specificati.

    Args:
        session: Sessione HTTP
        group_input: Gruppi con filtri
        token: Token di autenticazione

    Returns:
        Gruppi di pazienti
    """
    response = []
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # Crea task per ogni gruppo
    tasks = []
    for group in group_input:
        task = asyncio.create_task(
            session.post(
                f"{DATA_ACCESS_URL}/patients/stratify-patient",
                json=group.filters,
                headers=headers
            )
        )
        tasks.append((group, task))

    # Attendi i risultati
    for group, task in tasks:
        try:
            api_response = await task
            if api_response.status != 200:
                logger.error(f"Errore API per {group.title}: {api_response.status}")
                response.append({"name": group.title, "patients": []})
                continue

            patients_data = await api_response.json()
            response.append({"name": group.title, "patients": patients_data})
        except Exception as e:
            logger.error(f"Errore nella ricerca dei pazienti per {group.title}: {str(e)}")
            response.append({"name": group.title, "patients": []})

    return response


async def _get_patient_outcomes(
        session: aiohttp.ClientSession,
        patient_groups: List[Dict[str, Any]],
        timings: List[str],
        outcome: str,
        token: str
) -> List[Dict[str, Any]]:
    """
    Recupera gli outcome dei pazienti.

    Args:
        session: Sessione HTTP
        patient_groups: Gruppi di pazienti
        timings: Lista dei timing
        outcome: Tipo di outcome
        token: Token di autenticazione

    Returns:
        Dati degli outcome
    """
    response = []
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    for group in patient_groups:
        if not group.get("patients"):
            logger.debug(f"Nessun paziente nel gruppo {group.get('name')}, saltato")
            continue

        data = []
        # Prepara le richieste per ogni timing
        tasks = []
        for time in timings:
            request_data = {
                "code": outcome,
                "patients": group.get("patients"),
                "encounter_name": time
            }

            task = asyncio.create_task(
                session.post(
                    f"{DATA_ACCESS_URL}/observations/search-observation-analytics",
                    json=request_data,
                    headers=headers
                )
            )
            tasks.append((time, task))

        # Attendi i risultati
        for time, task in tasks:
            try:
                api_response = await task
                if api_response.status != 200:
                    logger.error(f"Errore API per {group.get('name')} al timing {time}: {api_response.status}")
                    data.append([])
                    continue

                values = await api_response.json()

                # Estrai solo i valori dalle osservazioni
                extracted_values = [entry.get("value") for entry in values if "value" in entry]
                data.append(extracted_values)
            except Exception as e:
                logger.error(f"Errore nel recupero degli outcome per {group.get('name')} al timing {time}: {str(e)}")
                data.append([])

        response.append({"label": group.get("name"), "data": data})

    return response


async def _get_patient_outcomes_csv(
        session: aiohttp.ClientSession,
        patient_groups: List[Dict[str, Any]],
        timings: List[str],
        outcome: str,
        token: str
) -> List[Dict[str, Any]]:
    """
    Recupera gli outcome dei pazienti in formato CSV.

    Args:
        session: Sessione HTTP
        patient_groups: Gruppi di pazienti
        timings: Lista dei timing
        outcome: Tipo di outcome
        token: Token di autenticazione

    Returns:
        Dati in formato CSV
    """
    response = []
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    # Prepara tutte le richieste
    all_tasks = []
    for group in patient_groups:
        if not group.get("patients"):
            continue

        group_name = group.get("name")
        for time in timings:
            request_data = {
                "code": outcome,
                "patients": group.get("patients"),
                "encounter_name": time
            }

            task = asyncio.create_task(
                session.post(
                    f"{DATA_ACCESS_URL}/observations/search-observation-analytics",
                    json=request_data,
                    headers=headers
                )
            )
            all_tasks.append((group_name, time, task))

    # Attendi e processa i risultati
    for group_name, time, task in all_tasks:
        try:
            api_response = await task
            if api_response.status != 200:
                logger.error(f"Errore API per {group_name} al timing {time}: {api_response.status}")
                continue

            values = await api_response.json()

            # Aggiungi ogni valore alla risposta
            for entry in values:
                patient_id = entry.get("patient")
                outcome_value = entry.get("value")
                if patient_id and outcome_value is not None:
                    response.append({
                        "Patient_ID": patient_id,
                        "Group": group_name,
                        "Time": time,
                        outcome: outcome_value
                    })
        except Exception as e:
            logger.error(f"Errore nel recupero dei dati CSV per {group_name} al timing {time}: {str(e)}")

    return response
