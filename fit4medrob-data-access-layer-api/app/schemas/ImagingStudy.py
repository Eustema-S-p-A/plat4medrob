from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import date as dt


class ImagingStudySearchRequest(BaseModel):
    patient: Optional[str] = Field(None, description="l'ID del paziente associato all'osservazione")
    organization: Optional[str] = Field(None, description="Un identificatore dell'organizzazione in cui si è svolta l'obx")
    modality: Optional[str] = None
    bodysite: Optional[str] = None
    date_init: Optional[dt] = None
    date_end: Optional[dt] = None
    count: Optional[int] = 10
    nPage: Optional[int] = 0
    sortBy: Optional[str] = "_id"
    encounter_name: Optional[str] = None


class ImagingStudy(BaseModel):
    id: Optional[str] = None
    identifier: Optional[str] = None
    patient: Optional[str] = None
    date: Optional[str] = None 
    rehabCenter: Optional[str] = None 
    modality: Optional[str] = None 
    bodysite: Optional[str] = None
    endpoint: Optional[str] = None  
    numberOfSeries: Optional[int] = None 	
    numberOfInstances: Optional[int] = None 
    series: Optional[Any] = []	
    encounter: Optional[str] = None


class ImagingStudySearchResult(BaseModel):
    list : List[ImagingStudy]
    total : int