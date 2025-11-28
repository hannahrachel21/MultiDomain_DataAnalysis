from typing import Dict, List
import pandas as pd
from models.common_models import SheetInfo

# In-memory cache of loaded Excel files per session
_EXCEL_CACHE: Dict[str, Dict[str, pd.DataFrame]] = {}

def load_excel_for_session(session_id: str, file_path: str) -> List[SheetInfo]:
    """
    Read Excel file and store per-session sheet dataframes in cache.
    Returns metadata for all sheets.
    """
    xls = pd.ExcelFile(file_path)
    sheet_infos: List[SheetInfo] = []
    sheet_dfs: Dict[str, pd.DataFrame] = {}

    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name)
        sheet_dfs[sheet_name] = df
        sheet_infos.append(
            SheetInfo(
                sheet_name=sheet_name,
                n_rows=int(df.shape[0]),
                n_cols=int(df.shape[1])
            )
        )

    _EXCEL_CACHE[session_id] = sheet_dfs
    return sheet_infos

def get_sheet_df(session_id: str, sheet_name: str) -> pd.DataFrame:
    if session_id not in _EXCEL_CACHE:
        raise KeyError("Excel data not loaded for this session.")
    sheets = _EXCEL_CACHE[session_id]
    if sheet_name not in sheets:
        raise KeyError(f"Sheet '{sheet_name}' not found for this session.")
    return sheets[sheet_name]
