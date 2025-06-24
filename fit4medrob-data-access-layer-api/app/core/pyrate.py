import os
#import multiprocessing
from functools import lru_cache
from fastapi import Depends
from fhir_pyrate import Ahoy, Pirate


@lru_cache()
def get_auth_pyrate() -> Ahoy:
    """
    Restituisce un singleton di autenticazione Ahoy per il client HAPI FHIR.
    Usa le credenziali da environment variables.
    """
    return Ahoy(
        auth_type="BasicAuth",
        auth_method="env"
    )



def get_pyrate_client(
    auth: Ahoy = Depends(get_auth_pyrate),
) -> Pirate:
    """quit
    Restituisce un client Pirate configurato, pronto per le query al server HAPI FHIR.
    """
    base_url = os.getenv("BASE_URL")
    num_processes = 1 #or min(5, multiprocessing.cpu_count())

    return Pirate(
        auth=auth,
        base_url=base_url,
        print_request_url=True,
        num_processes=num_processes,
        cache_folder=None,
        
    )