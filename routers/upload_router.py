import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

from services.file_upload_service import save_uploaded_file
from services.excel_reader_service import load_excel_for_session
from services.domain_logic_service import resolve_domain
from services.session_service import create_session

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    # Save or reuse file
    file_path = save_uploaded_file(file)

    session_id = uuid.uuid4().hex

    sheet_infos = load_excel_for_session(session_id, file_path)
    if not sheet_infos:
        raise HTTPException(status_code=400, detail="Uploaded Excel has no sheets.")

    primary_sheet = sheet_infos[0].sheet_name
    domain = resolve_domain(session_id, primary_sheet)

    # Create a NEW session every time (even if file reused)
    create_session(
        session_id=session_id,
        file_path=file_path,
        file_name=file.filename,
        domain=domain,
    )

    return {
        "session_id": session_id,
        "file_name": file.filename,
        "domain": domain,
        "sheets": [s.dict() for s in sheet_infos],
    }
