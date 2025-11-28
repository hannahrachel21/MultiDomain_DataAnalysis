from typing import Dict, Any

# Two separate caches:
_VIZ_CACHE_MANUAL: Dict[str, Dict[str, Any]] = {}
_VIZ_CACHE_AI: Dict[str, Dict[str, Any]] = {}

def get_cached_visualizations(session_id: str, mode: str):
    if mode == "manual":
        return _VIZ_CACHE_MANUAL.get(session_id)
    elif mode == "ai":
        return _VIZ_CACHE_AI.get(session_id)

def store_visualizations(session_id: str, data: Dict[str, Any], mode: str):
    if mode == "manual":
        _VIZ_CACHE_MANUAL[session_id] = data
    elif mode == "ai":
        _VIZ_CACHE_AI[session_id] = data

