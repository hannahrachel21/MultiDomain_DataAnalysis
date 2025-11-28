from typing import Dict, Any
from .excel_reader_service import get_sheet_df

def get_preview_rows(session_id: str, sheet_name: str, n_rows: int = 20) -> Dict[str, Any]:
    df = get_sheet_df(session_id, sheet_name)
    preview_df = df.head(n_rows)
    return {
        "columns": list(preview_df.columns),
        "rows": preview_df.to_dict(orient="records")
    }
