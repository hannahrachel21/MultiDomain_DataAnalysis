from typing import Literal
import re
from .excel_reader_service import get_sheet_df

DomainType = Literal["retail", "manufacturing", "education", "unknown"]

def infer_domain_from_columns(columns) -> DomainType:
    cols_str = " ".join([c.lower() for c in columns])

    if any(k in cols_str for k in ["product_id", "sale_id", "store_id", "inventory_id"]):
        return "retail"
    if any(k in cols_str for k in ["equipment_id", "downtime_id", "parts_replaced", "techniciam_id"]):
        return "manufacturing"
    if any(k in cols_str for k in ["student_id", "module_name", "module_id", "resource_type"]):
        return "education"
    return "unknown"

def resolve_domain(session_id: str, primary_sheet_name: str) -> DomainType:
    """
    Use primary sheet columns to guess domain.
    You can call this after excel load.
    """
    df = get_sheet_df(session_id, primary_sheet_name)
    return infer_domain_from_columns(df.columns)
