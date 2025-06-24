from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import date as dt

class DictItem(BaseModel):
    x: float
    y: float

class Signal(BaseModel):
    channel: str 
    signal: List[DictItem]


class TimeRange(BaseModel):
    start: float
    end: float

class MVNXMetadata(BaseModel):
    mvn_version: Optional[str]        
    frame_rate: Optional[float]    
    n_frames: Optional[int]           
    time_range: Optional[TimeRange]   

    segments: List[str]     
    segment_blocks: List[str]  

    joints: Optional[List[str]]       
    joint_blocks: Optional[List[str]]  

    events: Optional[List[str]]      
    event_block: Optional[str]      

    global_blocks: Optional[List[str]]      



class ObservationStratificationRequest(BaseModel):
    code: Optional[str] = Field(None, description="Il code che è il nome del field di redcap della obx")
    patients: Optional[List[str]] = Field(None, description="Una lista di identificatori (id, non identifier) dei pazienti associato all'osservazione")
    encounter_name : Optional[str] = Field(None, description="Il nome dell'encounter in cui è stata prese l'obx (class:display)")
    

class ObservationSearchRequest(BaseModel):
    name: Optional[str] = Field(None, description="Il code:text che è il nome dell'obx")
    patient: Optional[str] = Field(None, description="Una lista di identificatori (id, non identifier) dei pazienti associato all'osservazione")
    encounter_name : Optional[str] = Field(None, description="Il nome dell'encounter in cui è stata prese l'obx (class:display)")
    date_init: Optional[dt] = Field(None, description="Data meno recente dell'intervallo temporale in cui filtrare le obx")
    date_end: Optional[dt] = Field(None, description="Data più recente dell'intervallo temporale in cui filtrare le obx")
    count: Optional[int] = 10
    nPage: Optional[int] = 0
    sortBy: Optional[str] = "_id"
    organization: Optional[str] = None 


class Observation(BaseModel):
    id: Optional[str] = None
    patient: Optional[str] = None
    name: Optional[str] = None
    value: Optional[float] = None
    date: Optional[str] = None
    encounter: Optional[str] = None
    rehabCenter: Optional[str] = None
    unit: Optional[str] = None
    device: Optional[str] = None
    valueCode : Optional[str] = None
    channelLabels : Optional[List[str]] = None
    identifier : Optional[str] = None
    


class ObservationSearchResult(BaseModel):
    list : List[Observation]
    total : int
    

class ObsRed(BaseModel):
    patient : str
    value : float