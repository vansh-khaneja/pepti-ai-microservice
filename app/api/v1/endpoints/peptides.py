from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.services.peptide_service import PeptideService
from app.core.database import get_db
from app.models.peptide import PeptideCreate, PeptideResponse, PeptideChemicalResponse, ChemicalFieldRequest, ChemicalFieldResponse
from app.utils.helpers import log_api_call
from typing import List, Dict, Any

router = APIRouter()

@router.post("/", response_model=PeptideResponse, tags=["peptides"])
async def create_peptide(
    peptide_data: PeptideCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new peptide entry in the Qdrant vector database
    
    This endpoint:
    1. Takes peptide information (name, overview, mechanism of actions, potential research fields)
    2. Generates embeddings using OpenAI API
    3. Stores the peptide data and embeddings in Qdrant
    4. Returns the created peptide ID and confirmation
    """
    try:
        # Log the API call
        log_api_call("/peptides/", "POST")
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Create the peptide
        result = peptide_service.create_peptide(peptide_data)
        
        # Return the response
        return PeptideResponse(
            success=True,
            message="Peptide created successfully",
            data=result
        )
        
    except Exception as e:
        # Log the error
        log_api_call("/peptides/", "POST", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create peptide: {str(e)}"
        )



@router.put("/{peptide_name}", response_model=PeptideResponse, tags=["peptides"])
async def update_peptide(
    peptide_name: str,
    peptide_data: PeptideCreate,
    db: Session = Depends(get_db)
):
    """
    Update a peptide by name

    This endpoint deletes the existing peptide entry identified by `peptide_name`
    from the Qdrant vector database and creates a new one from `peptide_data`.
    """
    try:
        # Log the API call
        log_api_call(f"/peptides/{peptide_name}", "PUT")

        # Initialize peptide service
        peptide_service = PeptideService()

        # Update (delete+create) the peptide
        result = peptide_service.update_peptide(peptide_name, peptide_data)

        return PeptideResponse(
            success=True,
            message="Peptide updated successfully",
            data=result
        )
    except Exception as e:
        # Log the error
        log_api_call(f"/peptides/{peptide_name}", "PUT", error=str(e))

        # Return error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update peptide: {str(e)}"
        )

@router.delete("/{peptide_name}", tags=["peptides"])
async def delete_peptide(
    peptide_name: str,
    db: Session = Depends(get_db)
):
    """
    Delete a peptide by name
    
    This endpoint removes the peptide from the Qdrant vector database
    """
    try:
        # Log the API call
        log_api_call(f"/peptides/{peptide_name}", "DELETE")
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Delete the peptide
        success = peptide_service.delete_peptide(peptide_name)
        
        if success:
            # Return the response
            return {
                "success": True,
                "message": "Peptide deleted successfully",
                "data": {"name": peptide_name}
            }
        else:
            # Return not found response
            raise HTTPException(
                status_code=404, 
                detail=f"Peptide '{peptide_name}' not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the error
        log_api_call(f"/peptides/{peptide_name}", "DELETE", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete peptide: {str(e)}"
        )

@router.post("/ensure-index", tags=["peptides"])
async def ensure_index(
    db: Session = Depends(get_db)
):
    """
    Ensure the name index exists for efficient peptide searching
    
    This endpoint manually triggers index creation if needed
    """
    try:
        # Log the API call
        log_api_call("/peptides/ensure-index", "POST")
        
        # Initialize peptide service and ensure Qdrant is ready
        peptide_service = PeptideService()
        # Lazily create qdrant service if needed, then ensure index explicitly
        peptide_service._ensure_qdrant()
        if peptide_service.qdrant_service is None:
            raise RuntimeError("Qdrant service failed to initialize")
        peptide_service.qdrant_service.ensure_name_index()
        
        # Return the response
        return {
            "success": True,
            "message": "Name index ensured successfully",
            "data": {
                "index_type": "keyword",
                "field_name": "name"
            }
        }
        
    except Exception as e:
        # Log the error
        log_api_call("/peptides/ensure-index", "POST", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to ensure index: {str(e)}"
        )

@router.get("/recommendations/{peptide_name}", tags=["peptides"])
async def get_peptide_recommendations(
    peptide_name: str,
    top_k: int = Query(4, ge=1, le=10, description="Number of recommended peptides to return")
):
    """
    Get peptide recommendations based on vector similarity
    
    This endpoint:
    1. Searches for the given peptide name in Qdrant
    2. Gets its embeddings and finds top K similar peptides
    3. Returns recommended peptides with names and overviews
    """
    try:
        # Log the API call
        log_api_call(f"/peptides/recommendations/{peptide_name}", "GET")
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Find similar peptides
        similar_peptides = peptide_service.find_similar_peptides(peptide_name, top_k)
        
        # Return the response
        return {
            "success": True,
            "message": f"Found {len(similar_peptides)} recommended peptides",
            "data": similar_peptides,
            "query_peptide": peptide_name
        }
        
    except ValueError as e:
        # Log the error
        log_api_call(f"/peptides/recommendations/{peptide_name}", "GET", error=str(e))
        
        # Return not found error
        raise HTTPException(
            status_code=404, 
            detail=str(e)
        )
    except Exception as e:
        # Log the error
        log_api_call(f"/peptides/recommendations/{peptide_name}", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get peptide recommendations: {str(e)}"
        )

@router.get("/{peptide_name}/chemical-info", response_model=PeptideChemicalResponse, tags=["peptides"])
async def get_peptide_chemical_info(
    peptide_name: str
):
    """
    Get detailed chemical information for a specific peptide
    
    This endpoint:
    1. Takes a peptide name as input
    2. Uses OpenAI function calling to get chemical data
    3. Returns sequence, chemical formula, molecular mass, and IUPAC name
    """
    try:
        # Log the API call
        log_api_call(f"/peptides/{peptide_name}/chemical-info", "GET")
        
        # Initialize peptide service
        peptide_service = PeptideService()
        
        # Get chemical information
        chemical_info = peptide_service.get_peptide_chemical_info(peptide_name)
        
        # Return the response
        return PeptideChemicalResponse(
            success=True,
            message=f"Chemical information retrieved successfully for {peptide_name}",
            data=chemical_info
        )

    except Exception as e:
        # Log the error
        log_api_call(f"/peptides/{peptide_name}/chemical-info", "GET", error=str(e))
        
        # Return error response
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get chemical information for {peptide_name}: {str(e)}"
        )

@router.post("/chemical-field", response_model=ChemicalFieldResponse, tags=["peptides"])
async def generate_chemical_field(
    body: ChemicalFieldRequest
):
    """
    Generate exactly one requested chemical field via OpenAI only.
    Fields: sequence | chemical_formula | molecular_mass | iupac_name
    """
    try:
        # Log the API call
        log_api_call("/peptides/chemical-field", "POST")

        peptide_service = PeptideService()
        value = peptide_service.generate_chemical_field(body.peptide_name, body.field)

        return ChemicalFieldResponse(
            success=True,
            message="Field generated successfully",
            value=value or ""
        )
    except Exception as e:
        log_api_call("/peptides/chemical-field", "POST", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate field: {str(e)}")

