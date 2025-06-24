from typing import Optional

from pydantic import BaseModel, Field


class OrganizationSearchRequest(BaseModel):
    identifier: Optional[str] = Field(None, description="Un identificatore unico dell'organizzazione") 
    
class Organization(BaseModel):
    identifier: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None