import io, os
import uuid
from urllib.parse import urlparse
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

from app.config.logger import logger

load_dotenv()

coord_id = os.getenv("COORDINATOR_ORGANIZATION_ID")


aws_access_key_id = os.getenv("AWS_ACCESS_KEY")
aws_secret_access_key = os.getenv("AWS_SECRET_KEY")
region_name = os.getenv("AWS_REGION")
bucket_name = os.getenv("AWS_BUCKET_NAME")
TEMP_PATH = os.getenv("TEMP_PATH")


def delete_s3_file(url):
    if url.startswith("http"):
        parsed_url = urlparse(url)
        key = parsed_url.path.lstrip("/")  # rimuove la barra iniziale
    else:
        key = url  # già in formato chiave S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        logger.info(f"File del bucket eliminato da S3: {key}")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == "NoSuchKey":
            logger.warning(f"File non trovato nel bucket: {key}")
            return False
        else:
            logger.error(f"Errore durante l'eliminazione del file da S3: {str(e)}")
            return False


def delete_all_s3_urls(eeg_urls):
    not_del = []
    for url in eeg_urls:
        deleted = delete_s3_file(url)
        if not deleted:
            not_del.append(url)
    return not_del


def download_from_s3(url, file_ext):
    """
    Scarica il file da S3 con caching dei risultati per URL ripetuti
    """
    local_file_path = os.path.join(TEMP_PATH, f"temp_{uuid.uuid4().hex}.{file_ext}")
    os.makedirs(TEMP_PATH, exist_ok=True)

    client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )

    client.download_file(bucket_name, url, local_file_path)

    return local_file_path



def load_s3_file(url):
    """
    Carica un file dal bucket s3, funzione ausiliaria per il download
    """
    
    # Scarica da S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )
    file_buffer = io.BytesIO()
    try:
        s3.download_fileobj(bucket_name, url, file_buffer)
        file_buffer.seek(0)
        return file_buffer
    except NoCredentialsError:
        raise Exception("S3 credentials not found")
    except Exception as e:
        raise Exception(f"Failed to download file from S3: {e}")
        
