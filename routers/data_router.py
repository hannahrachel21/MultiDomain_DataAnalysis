from fastapi import APIRouter, HTTPException
from models.common_models import PreviewRequest, StatsRequest, VizRequest
from services.session_service import get_session
from services.preview_service import get_preview_rows
from services.stats_service import get_statistical_summary
from services.viz_service import suggest_visualizations

router = APIRouter(prefix="/data", tags=["data"])

@router.post("/preview")
async def preview_data(req: PreviewRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    preview = get_preview_rows(req.session_id, req.sheet_name, req.n_rows)
    return preview

@router.post("/stats")
async def stats_data(req: StatsRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    stats = get_statistical_summary(req.session_id, req.sheet_name)
    return stats

@router.post("/visualizations")
async def visualizations(req: VizRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    viz_configs = suggest_visualizations(req.session_id, req.sheet_name)
    return [v.dict() for v in viz_configs]

@router.post("/visualizations/all")
async def visualizations_all(req: VizRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    from services.manual_viz_service import suggest_visualizations_for_all_sheets

    result = suggest_visualizations_for_all_sheets(req.session_id)

    # Convert Pydantic objects to dict
    return {
        sheet: [v.dict() for v in viz_list]
        for sheet, viz_list in result.items()
    }

@router.post("/visualizations/ai")
async def visualizations_ai(req: VizRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    from services.viz_service import suggest_visualizations_for_all_sheets

    result = suggest_visualizations_for_all_sheets(req.session_id)

    # Convert Pydantic objects to dict
    return {
        sheet: [v.dict() for v in viz_list]
        for sheet, viz_list in result.items()
    }