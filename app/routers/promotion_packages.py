from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.promotion_package_schemas import PaginatedPromotionPackages, PromotionPackageRead
from app.services.promotion_package_service import PromotionPackageService

router = APIRouter()


@router.get("/promotion-packages", response_model=PaginatedPromotionPackages)
def list_promotion_packages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return PromotionPackageService.list_active_packages(db, page=page, page_size=page_size)


@router.get("/promotion-packages/{package_id}", response_model=PromotionPackageRead)
def get_promotion_package(package_id: int, db: Session = Depends(get_db)):
    return PromotionPackageService.get_package(db, package_id)
