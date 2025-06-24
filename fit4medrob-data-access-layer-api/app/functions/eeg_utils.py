import os
import urllib
import boto3
from mne.io import read_raw_edf
import numpy as np
import pyedflib
from botocore.config import Config
from dotenv import load_dotenv
import pandas as pd
from app.config.logger import logger
from scipy import signal as sg
from app.functions.s3_utils import download_from_s3

load_dotenv()

coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

aws_access_key_id = os.getenv("AWS_ACCESS_KEY")
aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
region_name = os.getenv("AWS_REGION")
bucket_name = os.getenv("AWS_BUCKET_NAME")
TEMP_PATH = os.getenv("TEMP_PATH")


def find_all_eeg_channels(url, new_sample_rate=1, clean_temp=True):
    '''
    Legge i segnali di tutti i canali dell'EEG utilizzando MNE e li restituisce in un dict
    '''

    local_edf_path = None
    try:
        # Leggi il file EDF
        if os.path.exists(url):
            raw = read_raw_edf(url, preload=True)
        else:
            # Salva il file EDF temporaneamente
            local_edf_path = download_from_s3(url, 'edf')

            # Leggi il file EDF utilizzando MNE
            raw = read_raw_edf(local_edf_path, preload=True)

        # Ottieni i dati originali e la frequenza di campionamento
        original_sample_rate = raw.info['sfreq']

        # Ricampiona il segnale alla nuova frequenza
        if original_sample_rate != new_sample_rate:
            raw = raw.resample(new_sample_rate)

            # Ottieni i dati e i tempi in un'unica operazione (più efficiente)
        data, times = raw.get_data(return_times=True, units='uV')
        ch_names = raw.ch_names

        # Usa list comprehension per una costruzione più efficiente
        eeg_all_channels = [
            {
                "channel": ch_name,
                "signal": [
                    {"x": float(times[j]), "y": float(np.round(data[i, j]))}
                    for j in range(len(data[i]))
                ]
            }
            for i, ch_name in enumerate(ch_names)
        ]
        return eeg_all_channels

    except Exception as e:
        raise ValueError(f"Errore nell'elaborazione del file EDF: {e}")

    finally:
        # Pulizia file temporanei se richiesto
        if clean_temp and local_edf_path and os.path.exists(local_edf_path):
            try:
                os.remove(local_edf_path)
            except:
                pass


def get_eeg_observation_by_id(id, search, organization):
    logger.debug("get all channels of the eeg observation by id")
    params = {}
    params["_id"] = id
    if organization != coord_id:
        params["performer"] = organization

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
            all_channels = find_all_eeg_channels(url)
        else:
            return []
    else:
        return []

    return all_channels

        




# Al momento non dovrebbe essere usata
def find_eeg_channel(url, channel, new_sample_rate=1):
    """
    Versione ottimizzata che legge solo il canale richiesto.
    Mantiene lo stesso formato di return della funzione originale.
    """
    channel = urllib.parse.unquote(channel)  # Decodifica il nome del canale
    temp_path = None
    edf_file = None

    s3_config = Config(
        max_pool_connections=50,
        retries={'max_attempts': 3},
        use_dualstack_endpoint=True
    )

    try:
        # Gestisco sia file locali che file S3
        if os.path.exists(url):
            # Per file locali, apro direttamente
            edf_file = pyedflib.EdfReader(url)
        else:

            # Per file S3
            client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
                config=s3_config
            )

            # Ottieni il file da S3
            response = client.get_object(Bucket=bucket_name, Key=url)
            edf_bytes = response['Body'].read()
            os.makedirs(TEMP_PATH, exist_ok=True)
            # Crea un file temporaneo univoco
            local_edf_path = TEMP_PATH + "/temp.edf"
            with open(local_edf_path, "wb") as f:
                f.write(edf_bytes)

            # Apri il file con pyedflib
            edf_file = pyedflib.EdfReader(local_edf_path)

        # Ottieni le etichette dei canali disponibili
        channel_names = edf_file.getSignalLabels()

        # Trova l'indice del canale richiesto (case insensitive)
        channel_idx = None
        for i, label in enumerate(channel_names):
            if label.lower() == channel.lower():
                channel_idx = i
                break

        if channel_idx is None:
            raise Exception(
                f"Channel {channel} not found in the EEG file. Available channels: {', '.join(channel_names)}")

        # Leggi solo il canale specifico richiesto
        original_sample_rate = edf_file.getSampleFrequency(channel_idx)
        signal = edf_file.readSignal(channel_idx)

        # Downsampling più efficiente con filtro anti-aliasing
        if new_sample_rate < original_sample_rate:
            downsample_factor = int(original_sample_rate / new_sample_rate)

            # Usa un filtro Butterworth anti-aliasing prima del downsampling
            nyquist = original_sample_rate / 2.0
            cutoff = new_sample_rate / 2.0
            b, a = sg.butter(4, cutoff / nyquist)
            filtered_signal = sg.filtfilt(b, a, signal)

            # Applica il downsampling
            downsampled_signal = filtered_signal[::downsample_factor]
        else:
            downsampled_signal = signal

        # Arrotonda il segnale risultante (identico al codice originale)
        signal = np.round(downsampled_signal, 2)
        T = int(1 / new_sample_rate)

        # Restituisce lo stesso formato della funzione originale
        return list(signal), T

    except Exception as e:
        # Riporta l'errore originale per mantenere la compatibilità
        raise Exception(f"Channel {channel} not found in the EEG file: {str(e)}")

    finally:
        # Chiudi il file e pulisci
        if edf_file is not None:
            edf_file.close()

        # # Elimina il file temporaneo se esiste
        # if local_edf_path is not None and os.path.exists(local_edf_path):
        #     os.unlink(local_edf_path)


def get_channel_eeg_observation_by_id(id, channel, search, organization):
    logger.debug("get channel eeg observation by id and channel")
    params = {}
    params["_id"] = id
    if organization != coord_id:
        params["performer"] = organization

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
            eeg_data, T = find_eeg_channel(url, channel)
        else:
            return []
    else:
        return []

    Y = [float(num) for num in eeg_data]

    X = list(np.arange(0, T * len(Y), T))[:len(Y)]
    EEG_dict = [{'x': x, 'y': y} for x, y in zip(X, Y)]
    return EEG_dict



