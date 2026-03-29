from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Category
from app.schemas.category_schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    @staticmethod
    def list_active_categories(db: Session) -> list[Category]:
        return (
            db.query(Category)
            .filter(Category.is_active.is_(True))
            .order_by(Category.display_order.asc(), Category.name.asc())
            .all()
        )

    @staticmethod
    def get_category(db: Session, category_id: int) -> Category:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        return category

    @staticmethod
    def create_category(db: Session, category_in: CategoryCreate) -> Category:
        existing_slug = db.query(Category).filter(Category.slug == category_in.slug).first()
        if existing_slug:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")

        if category_in.parent_category_id is not None:
            parent = db.query(Category).filter(Category.id == category_in.parent_category_id).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")

        category = Category(**category_in.model_dump())
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def update_category(db: Session, category_id: int, category_in: CategoryUpdate) -> Category:
        category = CategoryService.get_category(db, category_id)
        update_data = category_in.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"] != category.slug:
            slug_exists = db.query(Category).filter(Category.slug == update_data["slug"]).first()
            if slug_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")

        if "parent_category_id" in update_data and update_data["parent_category_id"] is not None:
            if update_data["parent_category_id"] == category.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category cannot be parent of itself")
            parent = db.query(Category).filter(Category.id == update_data["parent_category_id"]).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")

        for key, value in update_data.items():
            setattr(category, key, value)

        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def disable_category(db: Session, category_id: int) -> None:
        category = CategoryService.get_category(db, category_id)
        category.is_active = False
        db.commit()
