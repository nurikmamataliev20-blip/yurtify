from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.listing_schemas import (
    ListingCreate,
    ListingListFilters,
    ListingRead,
    ListingUpdate,
    PaginatedListings,
)
from app.services.listing_service import ListingService

router = APIRouter()


@router.post("/", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ListingService.create_listing(db, current_user, payload)


@router.get("/", response_model=PaginatedListings)
def get_public_listings(
    keyword: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    city: str | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    condition: str | None = Query(default=None),
    sort_by: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    filters = ListingListFilters(
        keyword=keyword,
        category_id=category_id,
        city=city,
        min_price=min_price,
        max_price=max_price,
        condition=condition,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return ListingService.get_public_feed(db, filters)


@router.get("/my", response_model=PaginatedListings)
def get_my_listings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ListingService.get_my_listings(db, current_user, page=page, page_size=page_size)


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    return ListingService.get_listing_detail(db, listing_id)


@router.put("/{listing_id}", response_model=ListingRead)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ListingService.update_listing(db, current_user, listing_id, payload)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ListingService.soft_delete_listing(db, current_user, listing_id)
    return None
