import os
import numpy as np
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import pandas as pd
from app.config.logger import logger
from app.functions.s3_utils import download_from_s3

load_dotenv()

aws_access_key_id = os.getenv("AWS_ACCESS_KEY")
aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
region_name = os.getenv("AWS_REGION")
bucket_name = os.getenv("AWS_BUCKET_NAME")
TEMP_PATH = os.getenv("TEMP_PATH")

coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")

def find_all_mvnx_segments(url, new_sample_rate=1, clean_temp=True):
    '''
    Legge i segnali di tutti i segmenti del mvnx e li restituisce in un dict
    '''
    local_path = None
    try:
        local_path = download_from_s3(url, 'mvnx')
        root = ET.parse(local_path).getroot()

        ns_uri = root.tag[root.tag.find("{")+1:root.tag.find("}")]
        ns = {'x': ns_uri}

        subject = root.find('x:subject', ns)
        # Lista dei segmenti
        segments = [seg.get('label') for seg in subject.find('x:segments', ns).findall('x:segment', ns)]
        n_seg = len(segments)

        # Tutti i frame
        frames = list(subject.find('x:frames', ns).findall('x:frame', ns))
        # Identifica blocchi dal primo frame 'normal'
        first_normal = next((fr for fr in frames if fr.get('type') == 'normal'), None)
        if first_normal is None:
            raise ValueError("Nessun frame 'normal' trovato nel file MVNX")
        blocks = [child.tag.split('}', 1)[-1] for child in first_normal if child.text and child.text.strip()]

        # Raccolta dati raw
        raw_data = {
            seg: {blk: {} for blk in blocks} for seg in segments
        }
        times = []

        for fr in frames:
            if fr.get('type') != 'normal':
                continue
            #t = float(fr.get('time'))
            t = float(fr.get('ms'))
            times.append(t)
            for child in fr:
                blk = child.tag.split('}', 1)[-1]
                if blk not in blocks or not child.text:
                    continue
                vals = np.fromstring(child.text, sep=' ')
                dim = int(len(vals) / n_seg)
                # Definizione delle componenti
                if dim == 4 and blk.lower() == 'orientation':
                    names = ['w', 'x', 'y', 'z']
                elif dim == 3:
                    names = ['X', 'Y', 'Z']
                elif dim == 1:
                    names = ['value']
                else:
                    names = [f'ch{i}' for i in range(dim)]
                # Estrazione per segmento
                for i, seg in enumerate(segments):
                    seg_vals = vals[i*dim:(i+1)*dim]
                    for j, name in enumerate(names):
                        raw_data[seg][blk].setdefault(name, []).append(float(seg_vals[j]))
       
        # Costruzione struttura finale
        segments_list = []
        for seg in segments:
            blocks_list = []
            for blk, signals in raw_data[seg].items():
                comp_names = list(signals.keys())
                signal_list = []
                for idx, t in enumerate(times):
                    y_vals = [signals[c][idx] for c in comp_names]
                    signal_list.append({'x': t, 'y': y_vals})
                    
                #tengo il blocco solo se almeno un frame ha y non vuoto
                if any(item['y'] for item in signal_list):
                    blocks_list.append({'component': blk, 'signal': signal_list})
                    
            segments_list.append({'segment': seg, 'segment_signals': blocks_list})
            
        print(segments_list)
       
        return segments_list
        
    except Exception as e:
        raise ValueError(f"Errore nell'elaborazione del file EDF: {e}")

    finally:
        # Pulizia file temporanei se richiesto
        if clean_temp and local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except:
                pass

def parse_mvnx_metadata(url, clean_temp=True):
    """
    Estrae e restituisce i metadati da un file .mvnx:
      - informazioni sul software e soggetto
      - dettagli sui frame e time range
      - quali segmenti e blocchi sono presenti
      - elenco giunti, eventi e blocchi globali
    """
    local_path = None

    local_path = download_from_s3(url, 'mvnx')
    root = ET.parse(local_path).getroot()
    # namespace
    ns_uri = root.tag[root.tag.find("{")+1:root.tag.find("}")]
    ns = {'x': ns_uri}

    # Versione MVN Studio
    mvn_tag = root.find('x:mvn', ns)
    mvn_version = mvn_tag.get('version', '') if mvn_tag is not None else ''

    # Informazioni sul soggetto
    subj = root.find('x:subject', ns)
    if subj is None:
        subj = root
    
    frame_rate = float(subj.get('frameRate', 0))
    # Estrazione dei frame "normal"
    frames = subj.find('x:frames', ns).findall('x:frame', ns)
    normal_frames = [f for f in frames if f.get('type') == 'normal']

    # Costruzione dei timestamp in secondi
    times = []
    for f in normal_frames:
        # Priorità: ms, time, index
        if f.get('ms') and f.get('ms').isdigit():
            times.append(int(f.get('ms')) / 1000.0)
        elif f.get('time') is not None:
            try:
                times.append(float(f.get('time')))
            except ValueError:
                times.append(len(times) / frame_rate)
        else:
            times.append(len(times) / frame_rate)
    # Rendiamo relativi ai primi ms se presente
    if normal_frames and normal_frames[0].get('ms') and normal_frames[0].get('ms').isdigit():
        base_ms = int(normal_frames[0].get('ms'))
        times = [(t*1000 - base_ms)/1000.0 for t in times]

    n_frames = len(times)
    time_range = {
        'start': times[0] if times else 0.0,
        'end': times[-1] if times else 0.0
    }

    # Segmenti
    segments = [s.get('label') for s in subj.find('x:segments', ns).findall('x:segment', ns)]
    n_seg = len(segments)

    # Individuazione dei blocchi dal primo frame normal
    first_frame = normal_frames[0] if normal_frames else None
    all_blocks = []
    if first_frame is not None:
        all_blocks = [c.tag.split('}', 1)[-1]
                        for c in first_frame if c.text and c.text.strip()]

    # Blocchi segment-specifici
    segment_blocks = []
    if first_frame:
        for blk in all_blocks:
            text = first_frame.find(f'x:{blk}', ns).text or ''
            vals = np.fromstring(text, sep=' ') if text.strip() else np.array([])
            if len(vals) % n_seg == 0 and len(vals) > 0:
                segment_blocks.append(blk)

    # Definizione giunti e relativi blocchi
    joint_defs = [j.get('label') for j in subj.findall('.//x:joints/x:joint', ns)]
    joint_block_keys = ['jointAngle', 'jointAngleXZY', 'jointAngleErgo', 'jointAngleErgoXZY']
    joint_blocks = [blk for blk in joint_block_keys if blk in all_blocks]

    # Definizione eventi di contatto
    events = [c.get('label') for c in subj.findall('.//x:footContactDefinition/x:contactDefinition', ns)]
    event_block = 'footContacts' if 'footContacts' in all_blocks else ''

    # Altri blocchi globali
    used = set(segment_blocks + joint_blocks + ([event_block] if event_block else []))
    global_blocks = [blk for blk in all_blocks if blk not in used]


    # Pulizia file temporanei se richiesto
    if clean_temp and local_path and os.path.exists(local_path):
        try:
            os.remove(local_path)
        except:
            pass
        
    return {
        'mvn_version': mvn_version,
        'frame_rate': frame_rate,
        'n_frames': n_frames,
        'time_range': time_range,
        'segments': segments,
        'segment_blocks': segment_blocks,
        'joints': joint_defs,
        'joint_blocks': joint_blocks,
        'events': events,
        'event_block': event_block,
        'global_blocks': global_blocks
    }




def get_mvnx_observation_by_id(id, search, organization):
    logger.debug("get all channels of the mvnx observation by id")
    params = {}
    params["_id"] = id
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
            all_segments = find_all_mvnx_segments(url)
        else:
            return []
    else:
        return []

    return  all_segments


def get_mvnx_metadata_by_id(id, search, organization):
    logger.debug("get mvnx metadata by id")
    params = {}
    params["_id"] = id
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
            mvnx_metadata = parse_mvnx_metadata(url)
        else:
            return {}
    else:
        return {}

    return  mvnx_metadata        



