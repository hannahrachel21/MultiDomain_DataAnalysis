from typing import Dict, Any
import numpy as np
import pandas as pd
from .excel_reader_service import get_sheet_df

def get_statistical_summary(session_id: str, sheet_name: str) -> Dict[str, Any]:
    df = get_sheet_df(session_id, sheet_name)

    summary = {}

    for col in df.columns:
        series = df[col]

        # -------------- NUMERICAL ----------------
        if pd.api.types.is_numeric_dtype(series):
            summary[col] = {
                "type": "numerical",
                "count": int(series.count()),
                "mean": float(series.mean()) if series.count() > 0 else None,
                "min": float(series.min()) if series.count() > 0 else None,
                "max": float(series.max()) if series.count() > 0 else None,
            }

        # -------------- CATEGORICAL / OBJECT ----------------
        else:
            count = int(series.count())
            unique = int(series.nunique())

            # PRIMARY KEY CASE
            if count == unique:
                if 'id' in col.lower():
                    summary[col] = {
                        "type": "primary_key",
                        "count": count
                    }
                else:
                    summary[col] = {
                        "type": "distinct_categorical",
                        "count": count
                    }
            else:
                freq_val = series.value_counts().idxmax()
                freq_num = int(series.value_counts().max())
                if 'id' in col.lower():
                    cat = "foreign_key"
                elif 'date' in col.lower() or 'time' in col.lower():
                    cat = "datetime"
                else:
                    cat = "categorical"

                summary[col] = {
                    "type": cat,
                    "count": count,
                    "unique": unique,
                    "freq": str(freq_val),
                    "freq_num": freq_num
                }

    missing_counts = df.isna().sum().to_dict()
    missing_pct = (df.isna().mean() * 100).round(2).to_dict()

    return {
        "summary": summary,
        "missing_values": {
            "count": missing_counts,
            "percent": missing_pct
        },
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1])
    }
 