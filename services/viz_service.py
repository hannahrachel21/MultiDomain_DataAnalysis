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

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from concurrent.futures import ProcessPoolExecutor

from services.viz_cache import get_cached_visualizations, store_visualizations
from services.excel_reader_service import _EXCEL_CACHE, get_sheet_df
from models.common_models import VizConfig

warnings.filterwarnings("ignore", category=UserWarning)

# Groq client (optional: if key not set, we fall back to rule-based)
client: Optional[Groq] = None
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)


# Helpers: DF preparation & LLM suggestion generation
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


def ask_llm_for_visualizations(df: pd.DataFrame) -> Optional[List[dict]]:
    """
    Ask Groq LLM for visualization suggestions based on schema.
    Returns a list of JSON-like dicts, or None if anything fails.
    """

    if client is None:
        # No API key or client, skip LLM
        return None

    schema = {col: str(df[col].dtype) for col in df.columns}

    prompt = f"""
You are a data visualization expert.

Given this dataset schema, suggest maximum 5 POSSIBLE but MOST MEANINGFUL visualizations in STRICT JSON.

Do not suggest charts for ID-like columns or where the number of unique values in the column might be equal to the count of that column.

Each JSON object must have:
- chart_type: one of ["histogram", "scatter", "bar", "countplot", "line"]
- x: column name
- y: column name or null
- description: short description

Schema:
{schema}

Return ONLY a JSON list. Do NOT include explanation.
"""

    # ---------- GROQ CALL ----------
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except Exception as e:
        print("Groq API Error:", e)
        return None

    raw = response.choices[0].message.content
    print("\n--- RAW LLM RESPONSE ---")
    print(raw)
    print("------------------------\n")

    # ---------- JSON PARSING ----------
    import json

    # First try straightforward load
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try to extract only the JSON part: find list [ ... ]
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1:
        try:
            cleaned = raw[start : end + 1]
            return json.loads(cleaned)
        except Exception:
            pass

    # Try single object { ... }
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            one_obj = json.loads(raw[start : end + 1])
            return [one_obj]
        except Exception:
            pass

    print("Failed to parse LLM JSON completely.")
    return None


def _fallback_suggestions(df: pd.DataFrame) -> List[dict]:
    suggestions: List[dict] = []

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    date_cols = df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()

    # Prefer time-series if possible
    if date_cols and numeric_cols:
        suggestions.append(
            {
                "chart_type": "line",
                "x": date_cols[0],
                "y": numeric_cols[0],
                "description": f"Trend of '{numeric_cols[0]}' over time by '{date_cols[0]}'.",
            }
        )
    elif numeric_cols:
        suggestions.append(
            {
                "chart_type": "histogram",
                "x": numeric_cols[0],
                "y": None,
                "description": f"Distribution of numeric column '{numeric_cols[0]}'.",
            }
        )

    if cat_cols:
        suggestions.append(
            {
                "chart_type": "countplot",
                "x": cat_cols[0],
                "y": None,
                "description": f"Category counts for '{cat_cols[0]}'.",
            }
        )

    return suggestions


def _clean_and_validate_suggestions(
    df: pd.DataFrame, raw_suggestions: Optional[List[dict]], max_per_sheet: int = 12
) -> List[dict]:
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

        if len(cleaned) >= max_per_sheet:
            break

    return cleaned


def _get_viz_suggestions_for_df(df: pd.DataFrame) -> List[dict]:
    df_prepared = _prepare_df_for_viz(df)

    raw_suggestions = ask_llm_for_visualizations(df_prepared)
    if not raw_suggestions:
        raw_suggestions = _fallback_suggestions(df_prepared)

    cleaned = _clean_and_validate_suggestions(df_prepared, raw_suggestions)
    if not cleaned:
        # If LLM gave nonsense and fallback also empty somehow, last resort:
        cleaned = _fallback_suggestions(df_prepared)

    return cleaned

# Chart rendering
def generate_chart(df: pd.DataFrame, chart_type: str, x: str, y: Optional[str] = None) -> Optional[str]:
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


# -------------------------------------------------------------------
# Public: Single-sheet visualizations (used by /data/visualizations)
# -------------------------------------------------------------------
def suggest_visualizations(session_id: str, sheet_name: str) -> List[VizConfig]:
    """
    Generate visualizations (metadata + images) for a SINGLE sheet.
    This is used by the existing /data/visualizations endpoint.
    """
    df_raw = get_sheet_df(session_id, sheet_name)
    df = _prepare_df_for_viz(df_raw)
    suggestions = _get_viz_suggestions_for_df(df)

    viz_results: List[VizConfig] = []

    for item in suggestions:
        chart_type = item.get("chart_type")
        x = item.get("x")
        y = item.get("y")
        desc = item.get("description", "")

        img_base64 = generate_chart(df=df, chart_type=chart_type, x=x, y=y)

        viz_results.append(
            VizConfig(
                chart_type=chart_type,
                x=x,
                y=y,
                description=desc,
                image_base64=img_base64,
            )
        )

    return viz_results


# Multiprocessing helper for all-sheets visualization
def _render_chart_process(task: Tuple[str, pd.DataFrame, str, str, Optional[str], str]):
    sheet_name, df, chart_type, x, y, desc = task
    img = generate_chart(df, chart_type, x, y)
    return sheet_name, chart_type, x, y, desc, img


# Public: ALL-sheets visualizations (used by /data/visualizations/all)
def suggest_visualizations_for_all_sheets(
    session_id: str, user_filters: Optional[Dict[str, List[str]]] = None
) -> Dict[str, List[VizConfig]]:
    # 1. Check cache
    cached = get_cached_visualizations(session_id, mode="ai")
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
    store_visualizations(session_id, final_result, mode="ai")
    return final_result
