from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PeptideCreate(BaseModel):
    """Model for creating a new peptide entry"""
    name: str = Field(..., description="Name of the peptide")
    overview: str = Field(..., description="Overview/description of the peptide")
    mechanism_of_actions: str = Field(..., description="Mechanism of actions of the peptide")
    potential_research_fields: str = Field(..., description="Potential research fields for the peptide")

class PeptidePayload(BaseModel):
    """Model for the payload that will be stored in Qdrant"""
    name: str
    overview: str
    mechanism_of_actions: str
    potential_research_fields: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_text(self) -> str:
        """Convert to text format for vectorization"""
        return f"name: {self.name} overview: {self.overview} mechanism of actions: {self.mechanism_of_actions} potential research fields: {self.potential_research_fields}"

class PeptideResponse(BaseModel):
    """Response model for peptide operations"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PeptideChemicalInfo(BaseModel):
    """Model for peptide chemical information"""
    peptide_name: str = Field(..., description="Name of the peptide")
    sequence: Optional[str] = Field(None, description="Amino acid sequence")
    chemical_formula: Optional[str] = Field(None, description="Chemical formula")
    molecular_mass: Optional[str] = Field(None, description="Molecular mass with units")
    iupac_name: Optional[str] = Field(None, description="IUPAC name")

class PeptideChemicalResponse(BaseModel):
    """Response model for peptide chemical information"""
    success: bool = True
    message: str = "Chemical information retrieved successfully"
    data: PeptideChemicalInfo
    timestamp: datetime = Field(default_factory=datetime.utcnow)