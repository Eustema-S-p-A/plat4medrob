# Dependency per la sessione HTTP
import aiohttp


async def get_http_session():
    """
    Dependency per la sessione HTTP.
    Garantisce la creazione e chiusura automatica della sessione aiohttp.

    Yields:
        Una sessione HTTP asincrona
    """
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()
