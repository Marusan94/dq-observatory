import datetime
import numpy as np
import pandas as pd


def to_jsonable(obj):
    if isinstance(obj, dict):
        return {str(to_jsonable(k)): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [to_jsonable(x) for x in obj.tolist()]
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)
    if isinstance(obj, float) and (pd.isna(obj)):
        return None
    try:
        import math
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
    except Exception:
        pass
    return obj
