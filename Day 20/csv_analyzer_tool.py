"""
CSV Analyzer Tool (Practical Project)
-------------------------------------
LLM-callable CSV analysis with data-quality checks.

Actions:
  profile      -> shape, per-column stats, missing %, outliers, quality warnings (default)
  group_by     -> aggregate a metric per category (sum/mean/count/min/max/median)
  top_n        -> top/bottom N rows by a numeric column
  filter       -> rows matching a condition (eq, ne, gt, gte, lt, lte, contains)
  correlation  -> strongest numeric correlations

Robustness: encoding fallback, delimiter sniffing, empty-file / bad-column
handling, row caps. All outputs are JSON-safe and LLM-sized.
"""
import csv
import json
import os
import warnings

import numpy as np
import pandas as pd


class CSVAnalyzerError(Exception):
    """Validation / parsing problem with an LLM-friendly message."""


AGGS = ("sum", "mean", "count", "min", "max", "median")
OPS = ("eq", "ne", "gt", "gte", "lt", "lte", "contains")


def _clean(o):
    """Make pandas/numpy results JSON-safe (NaN -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if o is None or isinstance(o, (str, int, bool)):
        return o
    if o is pd.NaT:
        return None
    return str(o)


def load_csv(path: str, max_rows: int = 200_000) -> pd.DataFrame:
    if not os.path.isfile(path):
        raise CSVAnalyzerError(f"File not found: {os.path.basename(path)}")
    if os.path.getsize(path) == 0:
        raise CSVAnalyzerError("File is empty.")
    df = None
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                sample = f.read(4096)
            try:
                sep = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            except csv.Error:
                sep = ","
            df = pd.read_csv(path, sep=sep, encoding=enc, nrows=max_rows)
            break
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError:
            raise CSVAnalyzerError("File has no data.")
        except pd.errors.ParserError as e:
            raise CSVAnalyzerError(f"Could not parse CSV: {e}")
    if df is None:
        raise CSVAnalyzerError("Could not decode file (tried utf-8 and latin-1).")
    df.columns = [str(c).strip() for c in df.columns]
    if df.empty:
        raise CSVAnalyzerError("CSV has headers but no rows.")
    return df


def _numeric_cols(df):
    return list(df.select_dtypes(include="number").columns)


def _need_col(df, col, label="column"):
    if col is None:
        raise CSVAnalyzerError(f"'{label}' is required for this action.")
    if col not in df.columns:
        raise CSVAnalyzerError(f"Column '{col}' not found. Available: {list(df.columns)}")
    return col


def _need_numeric(df, col):
    _need_col(df, col, "metric/column")
    if not pd.api.types.is_numeric_dtype(df[col]):
        raise CSVAnalyzerError(f"Column '{col}' is not numeric (dtype {df[col].dtype}).")


# ───────────────────────── actions ─────────────────────────
def profile(df: pd.DataFrame) -> dict:
    n = len(df)
    warns, cols = [], {}
    for c in df.columns:
        s = df[c]
        info = {"dtype": str(s.dtype), "missing": int(s.isna().sum()),
                "missing_pct": round(float(s.isna().mean()) * 100, 1), "unique": int(s.nunique())}
        if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
            d = s.dropna()
            if len(d):
                q1, q3 = d.quantile(0.25), d.quantile(0.75)
                iqr = q3 - q1
                out = int(((d < q1 - 1.5 * iqr) | (d > q3 + 1.5 * iqr)).sum()) if iqr > 0 else 0
                info.update(min=d.min(), max=d.max(), mean=round(float(d.mean()), 2),
                            median=float(d.median()), std=round(float(d.std()), 2) if len(d) > 1 else 0.0,
                            outliers_iqr=out)
                if out:
                    warns.append(f"'{c}' has {out} outlier(s) (IQR rule).")
        else:
            info["top_values"] = s.value_counts().head(3).to_dict()
            nums = pd.to_numeric(s, errors="coerce")
            if s.notna().any() and nums.notna().sum() / max(s.notna().sum(), 1) >= 0.9:
                warns.append(f"'{c}' looks numeric but is stored as text - clean it before analysis.")
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    dts = pd.to_datetime(s.dropna().head(50), errors="coerce")
                if len(dts) and dts.notna().mean() >= 0.9 and s.nunique() > 1:
                    info["looks_like_date"] = True
        if info["missing_pct"] >= 30:
            warns.append(f"'{c}' is {info['missing_pct']}% missing.")
        if info["unique"] <= 1 and n > 1:
            warns.append(f"'{c}' is constant (no information).")
        cols[c] = info
    dup = int(df.duplicated().sum())
    if dup:
        warns.append(f"{dup} duplicate row(s) found.")
    return {"rows": n, "columns_count": df.shape[1], "duplicate_rows": dup,
            "columns": cols, "warnings": warns}


def group_by(df, by, metric, agg="sum", top=20) -> dict:
    _need_col(df, by, "by")
    if agg not in AGGS:
        raise CSVAnalyzerError(f"agg must be one of {AGGS}.")
    if agg != "count":
        _need_numeric(df, metric)
    else:
        _need_col(df, metric, "metric")
    res = df.groupby(by)[metric].agg(agg).sort_values(ascending=False).head(top)
    return {"by": by, "metric": metric, "agg": agg, "groups": res.round(2).to_dict()}


def top_n(df, column, n=5, ascending=False) -> dict:
    _need_numeric(df, column)
    n = max(1, min(int(n), 50))
    rows = df.sort_values(column, ascending=ascending).head(n)
    return {"column": column, "ascending": ascending, "rows": rows.to_dict("records")}


def filter_rows(df, column, op="eq", value=None, limit=20) -> dict:
    _need_col(df, column)
    if op not in OPS:
        raise CSVAnalyzerError(f"op must be one of {OPS}.")
    if value is None:
        raise CSVAnalyzerError("'value' is required for filter.")
    s = df[column]
    if op == "contains":
        mask = s.astype(str).str.contains(str(value), case=False, na=False)
    else:
        if pd.api.types.is_numeric_dtype(s):
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise CSVAnalyzerError(f"Column '{column}' is numeric; value must be a number.")
        mask = {"eq": s == value, "ne": s != value, "gt": s > value,
                "gte": s >= value, "lt": s < value, "lte": s <= value}[op]
    hit = df[mask]
    limit = max(1, min(int(limit), 100))
    return {"matches": int(len(hit)), "returned": min(len(hit), limit), "rows": hit.head(limit).to_dict("records")}


def correlation(df, top=5) -> dict:
    nums = _numeric_cols(df)
    if len(nums) < 2:
        raise CSVAnalyzerError("Need at least 2 numeric columns for correlation.")
    corr = df[nums].corr()
    pairs = [(a, b, corr.loc[a, b]) for i, a in enumerate(nums) for b in nums[i + 1:] if pd.notna(corr.loc[a, b])]
    pairs.sort(key=lambda t: abs(t[2]), reverse=True)
    return {"top_pairs": [{"a": a, "b": b, "r": round(float(r), 3)} for a, b, r in pairs[:top]]}


# ───────────────────────── single entry point ─────────────────────────
def analyze(path: str, action: str = "profile", column=None, by=None, metric=None,
            agg="sum", n=5, op="eq", value=None, ascending=False) -> dict:
    df = load_csv("C:\\Users\\Aalhad Ramteke\\Downloads\\heart.csv")
    if action == "profile":
        out = profile(df)
    elif action == "group_by":
        out = group_by(df, by, metric, agg)
    elif action == "top_n":
        out = top_n(df, column, n, ascending)
    elif action == "filter":
        out = filter_rows(df, column, op, value)
    elif action == "correlation":
        out = correlation(df)
    else:
        raise CSVAnalyzerError("action must be one of: profile, group_by, top_n, filter, correlation.")
    return _clean(out)
