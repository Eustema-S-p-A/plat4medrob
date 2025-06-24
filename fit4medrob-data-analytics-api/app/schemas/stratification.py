from pydantic import BaseModel, Field
from typing import List, Optional


class StratificazionePazienti(BaseModel):
    pz_riabilitazione: Optional[str] = None
    pz_eta: List[int] = [18, 99]
    pz_sesso: Optional[str] = None
    pz_dominanza: Optional[str] = None
    pz_bmi: List[float] = [10.0, 70.0]
    pz_etnia: Optional[str] = None
    pz_stato_lavoro: Optional[str] = None
    paz_fumo: Optional[str] = None
    an_rem_patologie: List[str] = []
    ric_set_attuale: Optional[str] = None
    ric_lato_affetto: Optional[str] = None
    ric_quadro_clinico: List[str] = []
    ev_ac_tipo: Optional[str] = None
    ev_ac_i_localizzazione: Optional[str] = None
    ev_ac_i_bamford: Optional[str] = None
    ev_ac_i_toast: Optional[str] = None
    ev_ac_i_trombectomia: Optional[str] = None
    ev_ac_i_fibrinolisi: Optional[str] = None
    ev_ac_i_complicazioni: Optional[str] = None
    ev_ac_e_localizzazione: Optional[str] = None
    ev_ac_e_nhc: Optional[str] = None


class GroupFilter(BaseModel):
    title: str
    filters: dict


class AnalyticsRequest(BaseModel):
    groups: List[GroupFilter]
    output: str
    timings: List[str]


class AnalyticsMetrics(BaseModel):
    min: float  
    q1: float
    median: float
    mean: float
    q3: float
    max: float  


class AnalyticsResponse(BaseModel):
    label: str
    data: List[List[float]]  

class ObservationSearchRequest(BaseModel):
    code: str = Field(None, description="Il nome dell'obx")
    patients: List[str] = Field(None, description="Un identificatore del paziente associato all'osservazione")
    encounter_name: str = None
