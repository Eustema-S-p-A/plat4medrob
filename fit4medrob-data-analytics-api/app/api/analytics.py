from app.functions.pdf_utils import PDFReportGenerator
from app.schemas.stratification import AnalyticsRequest, AnalyticsResponse
from app.core.auth import get_current_user
from app.db.dal_client import get_http_session
from app.functions.csv_utils import CSVGenerator
from app.functions.dal_utils import _process_analytics_request
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from starlette.responses import Response
from typing import List
import aiohttp
import logging
import os

# Configurazione
logger = logging.getLogger(__name__)
DATA_ACCESS_URL = os.getenv('DATA_ACCESS_SERVICE_URL')

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/stat_group_compare",
    response_model=List[AnalyticsResponse],
    summary="Confronta gruppi statistici",
    description="Genera un'analisi comparativa tra diversi gruppi di pazienti"
)
async def create_stratification(
        request: AnalyticsRequest,
        user_data=Depends(get_current_user),
        session: aiohttp.ClientSession = Depends(get_http_session)
) -> List[AnalyticsResponse]:
    """
    Endpoint per l'analisi comparativa di gruppi di pazienti.

    Args:
        request: Parametri di richiesta per l'analisi
        user_data: Dati dell'utente autenticato
        session: Sessione HTTP per le chiamate API

    Returns:
        Lista di risultati dell'analisi
    """
    try:
        cu, token = user_data
        return await _process_analytics_request(request, token, session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante l'elaborazione della richiesta: {str(e)}"
        )


@router.post(
    "/stat_group_compare_pdf",
    summary="Genera report PDF",
    description="Genera un report PDF basato sull'analisi comparativa dei gruppi di pazienti"
)
async def create_pdf_report(
        request: AnalyticsRequest,
        user_data=Depends(get_current_user),
        session: aiohttp.ClientSession = Depends(get_http_session)
) -> Response:
    """
    Endpoint per la generazione di report PDF basati sull'analisi.

    Args:
        request: Parametri di richiesta per l'analisi
        user_data: Dati dell'utente autenticato
        session: Sessione HTTP per le chiamate API

    Returns:
        Response contenente il file PDF
    """
    try:
        cu, token = user_data
        output = await _process_analytics_request(request, token, session)
        pdf_data = PDFReportGenerator.generate_report(
            content=output,
            measure=request.output,
            group_input=request.groups,
            t_label=request.timings
        )

        if not pdf_data or pdf_data.getbuffer().nbytes == 0:
            raise ValueError("PDF generation failed: Empty file")

        return Response(
            pdf_data.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=analytics_report.pdf"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante la generazione del PDF: {str(e)}"
        )


@router.post(
    "/stat_group_compare_csv",
    summary="Genera report CSV",
    description="Genera un file CSV contenente i dati dell'analisi comparativa"
)
async def create_csv_report(
        request: AnalyticsRequest,
        user_data=Depends(get_current_user),
        session: aiohttp.ClientSession = Depends(get_http_session)
) -> Response:
    """
    Endpoint per la generazione di report CSV basati sull'analisi.

    Args:
        request: Parametri di richiesta per l'analisi
        user_data: Dati dell'utente autenticato
        session: Sessione HTTP per le chiamate API

    Returns:
        Response contenente il file CSV
    """
    try:
        cu, token = user_data
        output = await _process_analytics_request(request, token, session, csv_format=True)

        # Istanziazione e utilizzo diretto della classe CSVGenerator
        csv_generator = CSVGenerator()
        csv_data = csv_generator.generate(
            data=output,
            outcome_col=request.output,
            format_type="wide"
        )

        if not csv_data:
            raise ValueError("CSV generation failed: Empty file")

        return Response(
            csv_data.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_data.csv"})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante la generazione del CSV: {str(e)}"
        )
