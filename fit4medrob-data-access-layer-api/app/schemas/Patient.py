from datetime import date
from typing import Optional,List

from pydantic import BaseModel, Field


class PatientSearchRequest(BaseModel):
    identifier: Optional[str] = Field(None, description="Un identificatore unico del paziente")
    pz_riabilitazione: Optional[str] = Field(None, description="Tipo di riabilitazione")
    pz_eta: Optional[List[int]] = Field(None, description="Età del paziente, range predefinito 18-99")
    pz_sesso: Optional[str] = Field(None, description="Sesso del paziente")
    pz_dominanza: Optional[str] = Field(None, description="Dominanza del paziente")
    pz_bmi: Optional[List[float]] = Field(None, description="BMI del paziente (10.0-70.0)")
    pz_etnia: Optional[str] = Field(None, description="Etnia del paziente")
    pz_stato_lavoro: Optional[str] = Field(None, description="Stato lavorativo del paziente")
    paz_fumo: Optional[str] = Field(None, description="Abitudine al fumo")
    an_rem_patologie: Optional[List[str]] = Field(None, description="Patologie remote del paziente")
    ric_set_attuale: Optional[str] = Field(None, description="Settling riabilitativo attuale")
    ric_lato_affetto: Optional[str] = Field(None, description="Lato affetto")
    ric_quadro_clinico: Optional[List[str]] = Field(None, description="Quadro clinico del paziente")
    ev_ac_tipo: Optional[str] = Field(None, description="Tipo di evento acuto (ictus)")
    ev_ac_i_localizzazione: Optional[str] = Field(None, description="Localizzazione evento ischemico")
    ev_ac_i_bamford: Optional[str] = Field(None, description="Sede Bamford")
    ev_ac_i_toast: Optional[str] = Field(None, description="Classificazione TOAST")
    ev_ac_i_trombectomia: Optional[str] = Field(None, description="Trombectomia effettuata")
    ev_ac_i_fibrinolisi: Optional[str] = Field(None, description="Fibrinolisi sistemica effettuata")
    ev_ac_i_complicazioni: Optional[str] = Field(None, description="Complicazioni evento ischemico")
    ev_ac_e_localizzazione: Optional[str] = Field(None, description="Localizzazione evento emorragico")
    ev_ac_e_nhc: Optional[str] = Field(None, description="Evacuazione NHC")
    
    count: Optional[int] = 10
    nPage: Optional[int] = 0
    sortBy: Optional[str] = "_id"
    
    organization: Optional[str] = None 

class Patient(BaseModel):
    id: Optional[str] = None
    identifier: Optional[str] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    rehabCenter: Optional[str] = None
    dominanza: Optional[str] = None 
    altezza: Optional[int] = None
    peso: Optional[int] = None
    BMI: Optional[float] = None
    etnia: Optional[str] = None
    linguaMadre: Optional[str] = None
    fumatore: Optional[str] = None
    statoLavoro: Optional[str] = None
    riabilitazione: Optional[str] = None
    eventoAcuto : Optional[str] = None
    ric_set_attuale: Optional[str] = Field(None, description="Settling riabilitativo attuale")
    ric_lato_affetto: Optional[str] = Field(None, description="Lato affetto")
    ev_ac_i_localizzazione: Optional[str] = Field(None, description="Localizzazione evento ischemico")
    ev_ac_i_bamford: Optional[str] = Field(None, description="Sede Bamford")
    ev_ac_i_toast: Optional[str] = Field(None, description="Classificazione TOAST")
    ev_ac_i_trombectomia: Optional[str] = Field(None, description="Trombectomia effettuata")
    ev_ac_i_fibrinolisi: Optional[str] = Field(None, description="Fibrinolisi sistemica effettuata")
    ev_ac_i_complicazioni: Optional[str] = Field(None, description="Complicazioni evento ischemico")
    ev_ac_e_localizzazione: Optional[str] = Field(None, description="Localizzazione evento emorragico")
    ev_ac_e_nhc: Optional[str] = Field(None, description="Evacuazione NHC")
    an_rem_patologie: Optional[List[str]] = Field(None, description="Patologie remote del paziente")
    
    
        
class PatientSearchResult(BaseModel):
    list : List[Patient]
    total : int
    


    
    