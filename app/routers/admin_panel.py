from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import is_admin_user
from app.core.security import verify_password
from app.models.models import AdminAuditLog, Category, Listing, Payment, Promotion, Report, User

router = APIRouter()
templates = Jinja2Templates(directory=Path("templates"))

SESSION_COOKIE_NAME = "admin_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 8


def _get_current_admin_from_cookie(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "admin_session":
            return None
    except JWTError:
        return None

    email = payload.get("email")
    if not email:
        return None

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    if not is_admin_user(user):
        return None

    if user.account_status != "active":
        return None

    return user


def _require_admin_or_redirect(request: Request, db: Session) -> Optional[User | RedirectResponse]:
    admin_user = _get_current_admin_from_cookie(request, db)
    if not admin_user:
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return admin_user


def _set_session_cookie(response: RedirectResponse, user: User) -> None:
    token = jwt.encode(
        {
            "email": user.email,
            "type": "admin_session",
            "exp": int(datetime.now(timezone.utc).timestamp()) + SESSION_MAX_AGE_SECONDS,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: RedirectResponse) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


def _log_action(
    db: Session,
    admin_user: User,
    action: str,
    target_type: str,
    target_id: int,
    note: Optional[str] = None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_id=admin_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            note=note,
        )
    )


@router.get("/login")
def admin_login_page(request: Request, db: Session = Depends(get_db)):
    admin_user = _get_current_admin_from_cookie(request, db)
    if admin_user:
        return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context={"request": request, "error": None},
    )


@router.post("/login")
def admin_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if (
        not user
        or not verify_password(password, user.hashed_password)
        or not is_admin_user(user)
        or user.account_status != "active"
    ):
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={"request": request, "error": "Invalid admin credentials"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session_cookie(response, user)
    return response


@router.get("/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    _clear_session_cookie(response)
    return response


@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    now = datetime.now(timezone.utc)
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.account_status == "active").scalar() or 0
    blocked_users = (
        db.query(func.count(User.id))
        .filter(User.account_status.in_(["suspended", "blocked", "deleted"]))
        .scalar()
        or 0
    )

    total_listings = db.query(func.count(Listing.id)).scalar() or 0
    pending_listings = (
        db.query(func.count(Listing.id)).filter(Listing.moderation_status == "pending").scalar() or 0
    )
    approved_listings = (
        db.query(func.count(Listing.id)).filter(Listing.moderation_status == "approved").scalar() or 0
    )
    rejected_listings = (
        db.query(func.count(Listing.id)).filter(Listing.moderation_status == "rejected").scalar() or 0
    )

    total_reports = db.query(func.count(Report.id)).scalar() or 0
    total_payments = db.query(func.count(Payment.id)).scalar() or 0
    total_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.status == "successful")
        .scalar()
        or 0.0
    )
    active_promotions = (
        db.query(func.count(Promotion.id))
        .filter(Promotion.status == "active", Promotion.ends_at > now)
        .scalar()
        or 0
    )

    context = {
        "request": request,
        "admin_user": admin,
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "total_listings": total_listings,
            "pending_listings": pending_listings,
            "approved_listings": approved_listings,
            "rejected_listings": rejected_listings,
            "total_reports": total_reports,
            "total_payments": total_payments,
            "total_revenue": total_revenue,
            "active_promotions": active_promotions,
        },
    }
    return templates.TemplateResponse(request=request, name="admin/dashboard.html", context=context)


@router.get("/users")
def admin_users(
    request: Request,
    q: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    query = db.query(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(User.full_name.ilike(like_q), User.email.ilike(like_q)))
    if status_filter:
        query = query.filter(User.account_status == status_filter)

    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": users,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "q": q or "",
            "status_filter": status_filter or "",
        },
    )


@router.get("/users/{user_id}")
def admin_user_detail(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin/users?msg=User+not+found", status_code=status.HTTP_303_SEE_OTHER)

    listings_count = db.query(func.count(Listing.id)).filter(Listing.owner_id == user.id).scalar() or 0
    payments_count = db.query(func.count(Payment.id)).filter(Payment.user_id == user.id).scalar() or 0
    reports_count = db.query(func.count(Report.id)).filter(Report.reporter_user_id == user.id).scalar() or 0

    return templates.TemplateResponse(
        request=request,
        name="admin/user_detail.html",
        context={
            "request": request,
            "admin_user": admin,
            "item": user,
            "listings_count": listings_count,
            "payments_count": payments_count,
            "reports_count": reports_count,
        },
    )


@router.post("/users/{user_id}/suspend")
def suspend_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin/users?msg=User+not+found", status_code=status.HTTP_303_SEE_OTHER)

    user.account_status = "suspended"
    _log_action(db, admin, "suspend_user", "user", user.id, "User suspended from admin panel")
    db.commit()

    return RedirectResponse(url=f"/admin/users/{user_id}?msg=User+suspended", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/users/{user_id}/unsuspend")
def unsuspend_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/admin/users?msg=User+not+found", status_code=status.HTTP_303_SEE_OTHER)

    user.account_status = "active"
    _log_action(db, admin, "unsuspend_user", "user", user.id, "User unsuspended from admin panel")
    db.commit()

    return RedirectResponse(url=f"/admin/users/{user_id}?msg=User+unsuspended", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/listings")
def admin_listings(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    category_id: Optional[int] = Query(default=None),
    city: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    query = db.query(Listing)
    if status_filter:
        query = query.filter(Listing.moderation_status == status_filter)
    if category_id:
        query = query.filter(Listing.category_id == category_id)
    if city:
        query = query.filter(Listing.city == city)

    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    items = (
        query.order_by(Listing.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    categories = db.query(Category).order_by(Category.name.asc()).all()
    cities = [row[0] for row in db.query(Listing.city).distinct().order_by(Listing.city.asc()).all() if row[0]]

    return templates.TemplateResponse(
        request=request,
        name="admin/listings.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
            "categories": categories,
            "cities": cities,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "status_filter": status_filter or "",
            "category_id": category_id,
            "city": city or "",
        },
    )


@router.get("/listings/{listing_id}")
def admin_listing_detail(request: Request, listing_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        return RedirectResponse(url="/admin/listings?msg=Listing+not+found", status_code=status.HTTP_303_SEE_OTHER)

    owner = db.query(User).filter(User.id == listing.owner_id).first()
    category = db.query(Category).filter(Category.id == listing.category_id).first()

    return templates.TemplateResponse(
        request=request,
        name="admin/listing_detail.html",
        context={
            "request": request,
            "admin_user": admin,
            "item": listing,
            "owner": owner,
            "category": category,
        },
    )


@router.post("/listings/{listing_id}/approve")
def approve_listing(request: Request, listing_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        return RedirectResponse(url="/admin/listings?msg=Listing+not+found", status_code=status.HTTP_303_SEE_OTHER)

    listing.moderation_status = "approved"
    listing.status = "published"
    if not listing.published_at:
        listing.published_at = datetime.now(timezone.utc)

    _log_action(db, admin, "approve_listing", "listing", listing.id, "Listing approved")
    db.commit()

    return RedirectResponse(url=f"/admin/listings/{listing_id}?msg=Listing+approved", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/listings/{listing_id}/reject")
def reject_listing(
    request: Request,
    listing_id: int,
    note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        return RedirectResponse(url="/admin/listings?msg=Listing+not+found", status_code=status.HTTP_303_SEE_OTHER)

    listing.moderation_status = "rejected"
    listing.status = "draft"

    rejection_note = note.strip() or "Rejected without note"
    _log_action(db, admin, "reject_listing", "listing", listing.id, rejection_note)
    db.commit()

    return RedirectResponse(url=f"/admin/listings/{listing_id}?msg=Listing+rejected", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reports")
def admin_reports(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter)

    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    items = (
        query.order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/reports.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "status_filter": status_filter or "",
        },
    )


@router.post("/reports/{report_id}/resolve")
def resolve_report(
    request: Request,
    report_id: int,
    note: str = Form(default=""),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        return RedirectResponse(url="/admin/reports?msg=Report+not+found", status_code=status.HTTP_303_SEE_OTHER)

    report.status = "resolved"
    report.reviewed_by_admin_id = admin.id
    report.reviewed_at = datetime.now(timezone.utc)
    report.resolution_note = note.strip() or "Resolved from admin panel"

    _log_action(db, admin, "resolve_report", "report", report.id, report.resolution_note)
    db.commit()

    return RedirectResponse(url="/admin/reports?msg=Report+resolved", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/payments")
def admin_payments(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    query = db.query(Payment)
    if status_filter:
        query = query.filter(Payment.status == status_filter)

    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    items = (
        query.order_by(Payment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/payments.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "status_filter": status_filter or "",
        },
    )


@router.get("/promotions")
def admin_promotions(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    now = datetime.now(timezone.utc)
    stale = db.query(Promotion).filter(Promotion.status == "active", Promotion.ends_at < now).all()
    for promotion in stale:
        promotion.status = "expired"
    if stale:
        db.commit()

    query = db.query(Promotion)
    if status_filter:
        query = query.filter(Promotion.status == status_filter)

    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    items = (
        query.order_by(Promotion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/promotions.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "status_filter": status_filter or "",
        },
    )


@router.post("/promotions/{promotion_id}/deactivate")
def deactivate_promotion(request: Request, promotion_id: int, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    promotion = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promotion:
        return RedirectResponse(url="/admin/promotions?msg=Promotion+not+found", status_code=status.HTTP_303_SEE_OTHER)

    if promotion.status == "active":
        promotion.status = "cancelled"
        active_for_listing = (
            db.query(Promotion)
            .filter(
                Promotion.listing_id == promotion.listing_id,
                Promotion.id != promotion.id,
                Promotion.status == "active",
            )
            .first()
        )
        listing = db.query(Listing).filter(Listing.id == promotion.listing_id).first()
        if listing and not active_for_listing:
            listing.promotion_status = "none"

    _log_action(db, admin, "deactivate_promotion", "promotion", promotion.id, "Promotion deactivated")
    db.commit()

    return RedirectResponse(url="/admin/promotions?msg=Promotion+deactivated", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories")
def admin_categories(request: Request, db: Session = Depends(get_db)):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    items = db.query(Category).order_by(Category.display_order.asc(), Category.name.asc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin/categories.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
        },
    )


@router.get("/audit-logs")
def admin_audit_logs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    admin = _require_admin_or_redirect(request, db)
    if isinstance(admin, RedirectResponse):
        return admin

    query = db.query(AdminAuditLog)
    total_items = query.count()
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    items = (
        query.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    admin_ids = {item.admin_id for item in items}
    admins = {}
    if admin_ids:
        for user in db.query(User).filter(User.id.in_(admin_ids)).all():
            admins[user.id] = user

    return templates.TemplateResponse(
        request=request,
        name="admin/audit_logs.html",
        context={
            "request": request,
            "admin_user": admin,
            "items": items,
            "admins": admins,
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
    )
