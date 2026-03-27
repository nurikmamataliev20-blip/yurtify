from math import ceil

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import PromotionPackage
from app.schemas.promotion_package_schemas import PaginatedPromotionPackages


class PromotionPackageService:
    @staticmethod
    def list_active_packages(db: Session, page: int = 1, page_size: int = 20) -> PaginatedPromotionPackages:
        query = db.query(PromotionPackage).filter(PromotionPackage.is_active.is_(True))

        total_items = query.count()
        total_pages = ceil(total_items / page_size) if total_items > 0 else 1
        offset = (page - 1) * page_size

        items = query.order_by(PromotionPackage.created_at.desc()).offset(offset).limit(page_size).all()

        return PaginatedPromotionPackages(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            items=items,
        )

    @staticmethod
    def get_package(db: Session, package_id: int) -> PromotionPackage:
        package = (
            db.query(PromotionPackage)
            .filter(PromotionPackage.id == package_id, PromotionPackage.is_active.is_(True))
            .first()
        )
        if not package:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promotion package not found")
        return package
