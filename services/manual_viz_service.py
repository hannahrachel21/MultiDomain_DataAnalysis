from typing import List, Optional, Dict, Any, Tuple
import io
import base64
import warnings

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from concurrent.futures import ProcessPoolExecutor

from services.viz_cache import get_cached_visualizations, store_visualizations
from services.excel_reader_service import _EXCEL_CACHE, get_sheet_df
from models.common_models import VizConfig

warnings.filterwarnings("ignore", category=UserWarning)

#Covert date object datatype to string datatype
def _prepare_df_for_viz(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a copy of df with:
    - object-like date columns converted to datetime (if mostly parsable)
    """
    df = df.copy()

    for col in df.columns:
        if df[col].dtype == "object":
            # Try to parse as datetime
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                non_null = df[col].notna().sum()
                parsed_non_null = parsed.notna().sum()

                # Heuristic: at least 70% of non-null values parse to valid datetimes
                if non_null > 0 and parsed_non_null / non_null >= 0.7:
                    df[col] = parsed
            except Exception:
                # Leave as-is if parsing fails badly
                pass

    return df

def get_column_datatype(df: pd.DataFrame) ->Dict[str, str]:
    datatype = {}
    for col in df.columns:
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            datatype[col] = "numerical"
        elif np.issubdtype(df[col].dtype, np.datetime64) or any(elem in col.lower() for elem in ['date', 'time']):
            datatype[col] = "datetime"
        else:
            count = int(series.count())
            unique = int(series.nunique())
            if count == unique:
                if 'id' in col.lower():
                    datatype[col] = "primary_key"
                else:
                    datatype[col] = "distinct_categorical"
            else:
                if 'id' in col.lower():
                    datatype[col] = "foreign_key"
                else:
                    datatype[col] = "categorical"
    return datatype

def generate_manual_suggestions(df: pd.DataFrame) -> Optional[List[dict]]:
    datatype = get_column_datatype(df)
    manual_sug = []
    for col in df.columns:
        if datatype[col] == "categorical":
            manual_sug.append({
                "chart_type": "bar",
                "x": col,
                "y": None,
                "description": f"Count of {col}"
            })
        elif datatype[col] == "numerical":
            manual_sug.append({
                "chart_type": "histogram",
                "x": col,
                "y": None,
                "description": f"Distribution of {col}"
            })
    numerical, date = [], []
    for key, value in datatype.items():
        if value == "numerical":
            numerical.append(key)
        if value == "datetime":
            date.append(key)
    for i in range(len(numerical)-1):
        for j in range(i+1, len(numerical)):
            chart_sug = {
                "chart_type": "scatter",
                "x": numerical[i],
                "y": numerical[j],
                "description": f"Relationship between {numerical[i]} and {numerical[j]}"
            }
            manual_sug.append(chart_sug)
    if len(date) == 1:
        for item in numerical:
            chart_sug = {
                "chart_type": "line",
                "x": date[0],
                "y": item,
                "description": f"Trend of {item} over date"
            }
            manual_sug.append(chart_sug)
    return manual_sug

def _clean_and_validate_suggestions(df: pd.DataFrame, raw_suggestions: Optional[List[dict]]) -> List[dict]:
    if not raw_suggestions or not isinstance(raw_suggestions, list):
        return []

    cols = set(df.columns)
    seen = set()
    cleaned: List[dict] = []

    for item in raw_suggestions:
        if not isinstance(item, dict):
            continue

        chart_type = str(item.get("chart_type", "")).strip().lower()
        x = item.get("x")
        y = item.get("y", None)
        desc = item.get("description", "")

        if not chart_type or x is None:
            continue
        if x not in cols:
            continue
        if y is not None and y not in cols:
            continue

        # scatter/line require y
        if chart_type in ["scatter", "line"] and y is None:
            continue

        # Basic valid chart types
        if chart_type not in ["histogram", "scatter", "bar", "countplot", "line"]:
            continue

        key = (chart_type, x, y)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(
            {
                "chart_type": chart_type,
                "x": x,
                "y": y,
                "description": desc,
            }
        )

    return cleaned

def _get_viz_suggestions_for_df(df: pd.DataFrame) -> List[dict]:
    """
    High-level helper:
    - prepare df (datetime conversion)
    - validate & clean final list
    """
    df_prepared = _prepare_df_for_viz(df)

    raw_suggestions = generate_manual_suggestions(df_prepared)
    cleaned = _clean_and_validate_suggestions(df_prepared, raw_suggestions)
    return cleaned

def generate_chart(df: pd.DataFrame, chart_type: str, x: str, y: Optional[str] = None) -> Optional[str]:
    """
    Generate a single chart and return a base64-encoded PNG string.
    Returns None if an error occurs.
    """
    if x not in df.columns:
        print(f"CHART ERROR: x='{x}' not in columns")
        return None
    if y is not None and y not in df.columns:
        print(f"CHART ERROR: y='{y}' not in columns")
        return None

    print(f"\n=== GENERATE CHART ===")
    print("Chart type:", chart_type)
    print("X:", x)
    print("Y:", y)
    print("Column dtype:", df[x].dtype)
    print("======================\n")

    plt.figure(figsize=(8, 5))

    try:
        # histogram
        if chart_type == "histogram":
            print("Plot: histogram")
            # If x is not numeric, fall back to countplot
            if not np.issubdtype(df[x].dtype, np.number):
                print("Non-numeric for histogram; using countplot instead.")
                sns.countplot(data=df, x=x)
            else:
                sns.histplot(df[x].dropna(), kde=True)

        # scatter
        elif chart_type == "scatter":
            print("Plot: scatter")
            sns.scatterplot(data=df, x=x, y=y)

        # bar / countplot-like
        elif chart_type == "bar":
            print("Plot: bar")
            if y:
                sns.barplot(data=df, x=x, y=y)
            else:
                # SPECIAL HANDLING — datetime breaks countplot
                if np.issubdtype(df[x].dtype, np.datetime64):
                    print("Converting datetime to string for countplot")
                    temp = df.copy()
                    temp[x] = temp[x].dt.strftime("%Y-%m-%d")
                    sns.countplot(data=temp, x=x)
                else:
                    sns.countplot(data=df, x=x)

        elif chart_type == "countplot":
            print("Plot: countplot")
            sns.countplot(data=df, x=x)

        # line
        elif chart_type == "line":
            print("Plot: line")
            sns.lineplot(data=df, x=x, y=y)

        else:
            print("UNKNOWN CHART TYPE")
            return None

        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format="png")
        plt.close()
        buffer.seek(0)

        data = buffer.read()
        print("PNG bytes length:", len(data))
        return base64.b64encode(data).decode("utf-8")

    except Exception as e:
        print("CHART ERROR:", e)
        plt.close()
        return None

def _render_chart_process(task: Tuple[str, pd.DataFrame, str, str, Optional[str], str]):
    """
    Executed in separate processes.
    task = (sheet_name, df, chart_type, x, y, description)
    Returns (sheet_name, chart_type, x, y, description, image_base64)
    """
    sheet_name, df, chart_type, x, y, desc = task
    img = generate_chart(df, chart_type, x, y)
    return sheet_name, chart_type, x, y, desc, img



def suggest_visualizations_for_all_sheets(
    session_id: str, user_filters: Optional[Dict[str, List[str]]] = None
) -> Dict[str, List[VizConfig]]:
    """
    Generate visualizations for ALL sheets in a session, with:
    - caching
    - multiprocessing chart rendering
    - optional user-selected chart type filters

    Returns:
        { sheet_name: [VizConfig, VizConfig, ...], ... }
    """

    # 1. Check cache
    cached = get_cached_visualizations(session_id, mode="manual")
    if cached:
        return cached

    sheet_dfs = _EXCEL_CACHE.get(session_id)
    if not sheet_dfs:
        raise KeyError("Sheets not loaded.")

    tasks: List[Tuple[str, pd.DataFrame, str, str, Optional[str], str]] = []

    # 2. Build tasks for all sheets
    for sheet_name, df_raw in sheet_dfs.items():
        df = _prepare_df_for_viz(df_raw)
        suggestions = _get_viz_suggestions_for_df(df)

        # If user provided allowed chart types per sheet, filter here
        if user_filters and sheet_name in user_filters:
            allowed_types = set(user_filters[sheet_name])
            suggestions = [s for s in suggestions if s.get("chart_type") in allowed_types]

        for s in suggestions:
            chart_type = s.get("chart_type")
            x = s.get("x")
            y = s.get("y")
            desc = s.get("description", "")

            tasks.append((sheet_name, df, chart_type, x, y, desc))

    # If no tasks at all, return empty
    if not tasks:
        store_visualizations(session_id, {})
        return {}

    # 3. Run chart rendering in parallel
    final_result: Dict[str, List[VizConfig]] = {}

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(_render_chart_process, tasks))

    # 4. Collect results into VizConfig objects
    for sheet_name, chart_type, x, y, desc, img in results:
        if sheet_name not in final_result:
            final_result[sheet_name] = []

        final_result[sheet_name].append(
            VizConfig(
                chart_type=chart_type,
                x=x,
                y=y,
                description=desc,
                image_base64=img,
            )
        )

    # 5. Cache & return
    store_visualizations(session_id, final_result, mode="manual")
    return final_result
