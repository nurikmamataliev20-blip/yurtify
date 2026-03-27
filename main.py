from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routers import (
	admin_panel_router,
	attachments_router,
	auth_router,
	categories_router,
	favorites_router,
	listings_router,
	messaging_router,
	notifications_router,
	payments_router,
	promotion_packages_router,
	promotions_router,
	public_users_router,
	reports_router,
	users_router,
)
import traceback

app = FastAPI(
	title="Real Estate Marketplace API",
	description="Backend API for Yurtify built with FastAPI + MySQL",
	version="1.0.0",
)

uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
	traceback.print_exc()
	return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/")
async def root():
	return {"message": "Welcome to Real Estate Marketplace API"}


@app.get("/health")
async def health_check():
	return {"status": "healthy"}


app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(listings_router, prefix="/listings", tags=["listings"])
app.include_router(categories_router, tags=["categories"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(favorites_router, tags=["favorites"])
app.include_router(messaging_router, tags=["messaging"])
app.include_router(attachments_router, tags=["attachments"])
app.include_router(notifications_router, tags=["notifications"])
app.include_router(reports_router, tags=["reports"])
app.include_router(payments_router, tags=["payments"])
app.include_router(promotion_packages_router, tags=["promotion-packages"])
app.include_router(promotions_router, tags=["promotions"])
app.include_router(public_users_router, prefix="/public/users", tags=["public-users"])
app.include_router(admin_panel_router, prefix="/admin", tags=["admin"])


if __name__ == "__main__":
	import uvicorn

	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)