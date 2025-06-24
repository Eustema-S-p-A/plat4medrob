import aiohttp
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Classe per gestire la sessione aiohttp
class DicomWebClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth = aiohttp.BasicAuth(
            os.getenv("ORTHANC_SERVER_USER"),
            os.getenv("ORTHANC_SERVER_PSW")
        )

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(auth=self.auth)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


dicom_web_client = DicomWebClient()


async def get_dicom_client() -> aiohttp.ClientSession:
    return await dicom_web_client.get_session()
