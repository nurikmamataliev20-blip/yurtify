from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import Category, Listing, PromotionPackage, User


DEFAULT_PACKAGES = [
    {
        "name": "Basic Boost",
        "price": 299,
        "currency": "KGS",
        "duration_days": 7,
        "promotion_type": "boosted",
        "description": "Boost listing visibility for 7 days.",
    },
    {
        "name": "Featured Listing",
        "price": 599,
        "currency": "KGS",
        "duration_days": 14,
        "promotion_type": "featured",
        "description": "Show listing as featured for 14 days.",
    },
    {
        "name": "City Target",
        "price": 499,
        "currency": "KGS",
        "duration_days": 10,
        "promotion_type": "city_targeted",
        "description": "Promote listing to users in a selected city.",
    },
    {
        "name": "Top Placement",
        "price": 899,
        "currency": "KGS",
        "duration_days": 30,
        "promotion_type": "top_placement",
        "description": "Top placement in feed for 30 days.",
    },
]

DEFAULT_CATEGORIES = [
    {"name": "Apartments", "slug": "apartments", "display_order": 1},
    {"name": "Houses", "slug": "houses", "display_order": 2},
    {"name": "Commercial", "slug": "commercial", "display_order": 3},
]

DEFAULT_USERS = [
    {
        "full_name": "Demo Seller One",
        "email": "demo.seller1@yurtify.local",
        "phone": "+996700100001",
        "city": "Bishkek",
    },
    {
        "full_name": "Demo Seller Two",
        "email": "demo.seller2@yurtify.local",
        "phone": "+996700100002",
        "city": "Osh",
    },
]


def seed_categories(db: Session) -> list[Category]:
    categories: list[Category] = []
    for item in DEFAULT_CATEGORIES:
        category = db.query(Category).filter(Category.slug == item["slug"]).first()
        if not category:
            category = Category(
                name=item["name"],
                slug=item["slug"],
                display_order=item["display_order"],
                is_active=True,
            )
            db.add(category)
            db.flush()
        categories.append(category)
    return categories


def seed_promotion_packages(db: Session) -> None:
    for item in DEFAULT_PACKAGES:
        exists = db.query(PromotionPackage).filter(PromotionPackage.name == item["name"]).first()
        if exists:
            continue

        db.add(
            PromotionPackage(
                name=item["name"],
                price=item["price"],
                currency=item["currency"],
                duration_days=item["duration_days"],
                promotion_type=item["promotion_type"],
                description=item["description"],
                is_active=True,
            )
        )


def seed_users(db: Session) -> list[User]:
    users: list[User] = []
    hashed_password = get_password_hash("Passw0rd!123")

    for item in DEFAULT_USERS:
        user = db.query(User).filter(User.email == item["email"]).first()
        if not user:
            user = User(
                full_name=item["full_name"],
                email=item["email"],
                phone=item["phone"],
                hashed_password=hashed_password,
                city=item["city"],
                preferred_language="en",
                account_status="active",
                role="user",
            )
            db.add(user)
            db.flush()
        users.append(user)

    return users


def seed_listings(db: Session, users: list[User], categories: list[Category]) -> None:
    desired_count = 5

    existing_count = db.query(Listing).filter(Listing.deleted_at.is_(None)).count()
    if existing_count >= desired_count:
        return

    now = datetime.now(timezone.utc)
    base_index = existing_count + 1

    for i in range(base_index, desired_count + 1):
        owner = users[(i - 1) % len(users)]
        category = categories[(i - 1) % len(categories)]

        listing = Listing(
            owner_id=owner.id,
            category_id=category.id,
            title=f"Demo Listing #{i}",
            description=f"Seeded demo listing number {i}.",
            price=50000 + i * 2500,
            currency="KGS",
            city=owner.city,
            status="published",
            condition="used",
            latitude=None,
            longitude=None,
            is_negotiable=True,
            view_count=0,
            moderation_status="approved",
            promotion_status="none",
            published_at=now,
            expires_at=None,
            deleted_at=None,
        )
        db.add(listing)


def main() -> None:
    db = SessionLocal()
    try:
        categories = seed_categories(db)
        users = seed_users(db)
        seed_listings(db, users, categories)
        seed_promotion_packages(db)
        db.commit()
        print("Seed completed successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
