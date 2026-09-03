from fastapi import APIRouter, Depends
from .schemas import ConvertRequest, ConvertResponse
from .service import process_conversion

router = APIRouter()

# validation runs automatically via Depends
@router.get("/convert", response_model=ConvertResponse)
async def convert_currency(request: ConvertRequest = Depends()):
    return await process_conversion(request)