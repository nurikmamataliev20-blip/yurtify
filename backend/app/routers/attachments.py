from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import User
from app.schemas.messaging_schemas import AttachmentUploadResponse
from app.services.attachment_service import AttachmentService

router = APIRouter()


@router.post("/attachments/upload", response_model=AttachmentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    message_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await AttachmentService.upload_attachment(db, current_user, message_id=message_id, upload_file=file)


@router.get("/attachments/{attachment_id}", response_model=AttachmentUploadResponse)
def get_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AttachmentService.get_attachment(db, current_user, attachment_id)
