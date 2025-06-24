from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date as dt


class EncounterSearchRequest(BaseModel):
    patient: Optional[str] = Field(None, description="Un identificatore del paziente associato all'incontro")
    organization: Optional[str] = Field(None, description="L'identifier dell'organizations in cui si è svolto l'incontro")
    exam_name :  Optional[str] = Field(None, description="Il tipo di esame svolto nell'incontro")
    date_init: Optional[dt] = None 
    date_end: Optional[dt] = None
    count: Optional[int] = 10
    nPage: Optional[int] = 0
    sortBy: Optional[str] = "_id"
    

class Encounter(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    patient: Optional[str] = None
    date: Optional[str] = None
    rehabCenter: Optional[str] = None
    identifier: Optional[str] = Field(None, description="Un identificatore unico dell'incontro")
    
class EncounterSearchResult(BaseModel):
    list: List[Encounter]
    total: int