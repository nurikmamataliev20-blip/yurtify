from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import is_admin_user
from app.models.models import Listing, ListingImage, User


class ListingImageService:
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB

    @staticmethod
    async def upload_listing_image(
        db: Session,
        current_user: User,
        listing_id: int,
        upload_file: UploadFile,
    ) -> ListingImage:
        listing = db.query(Listing).filter(Listing.id == listing_id, Listing.deleted_at.is_(None)).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        if listing.owner_id != current_user.id and not is_admin_user(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can upload listing images",
            )

        content_type = (upload_file.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed",
            )

        file_bytes = await upload_file.read()
        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

        if len(file_bytes) > ListingImageService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is too large",
            )

        ext = Path(upload_file.filename or "").suffix.lower() or ".jpg"
        filename = f"listing_{listing_id}_{uuid4().hex}{ext}"

        upload_dir = Path("uploads") / "listings"
        upload_dir.mkdir(parents=True, exist_ok=True)
        destination = upload_dir / filename
        destination.write_bytes(file_bytes)

        existing_count = (
            db.query(ListingImage)
            .filter(ListingImage.listing_id == listing_id)
            .count()
        )

        image = ListingImage(
            listing_id=listing_id,
            file_url=f"/uploads/listings/{filename}",
            is_primary=existing_count == 0,
            order_index=existing_count,
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        return image
