from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.listing_schemas import ListingImageRead
from app.services.listing_image_service import ListingImageService

router = APIRouter()


@router.post(
    "/listing-images/upload",
    response_model=ListingImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_listing_image(
    listing_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ListingImageService.upload_listing_image(
        db,
        current_user,
        listing_id=listing_id,
        upload_file=file,
    )
