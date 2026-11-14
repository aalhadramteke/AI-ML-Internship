import ast
import json
import math
import operator as op
import os
import re
import smtplib
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import csv_analyzer_tool as cat
import db_query_tool as dbt

BASE_DIR = os.path.abspath(os.getenv("TOOL_FILES_DIR", "./data"))  # files tools may touch


# ───────────────────────── Error handling core ─────────────────────────
class ToolError(Exception):
    def __init__(self, type_: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.type, self.message, self.retryable = type_, message, retryable


REGISTRY: dict = {}


def tool(name: str, description: str, parameters: dict, required: list):
    """Register a function as an LLM-callable tool with validation + error envelope."""
    def deco(fn):
        def wrapper(**kwargs):
            try:
                missing = [r for r in required if r not in kwargs]
                if missing:
                    raise ToolError("invalid_arguments", f"Missing required argument(s): {missing}")
                unknown = [k for k in kwargs if k not in parameters]
                if unknown:
                    raise ToolError("invalid_arguments", f"Unknown argument(s): {unknown}")
                return {"ok": True, "data": fn(**kwargs)}
            except ToolError as e:
                return {"ok": False, "error": {"type": e.type, "message": e.message, "retryable": e.retryable}}
            except cat.CSVAnalyzerError as e:
                return {"ok": False, "error": {"type": "analysis_error", "message": str(e), "retryable": False}}
            except dbt.DBQueryError as e:
                return {"ok": False, "error": {"type": "query_error", "message": str(e), "retryable": False}}
            except Exception as e:  # last-resort safety net
                return {"ok": False, "error": {"type": "internal_error", "message": f"{type(e).__name__}: {e}", "retryable": False}}
        REGISTRY[name] = {
            "fn": wrapper,
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": parameters, "required": required},
        }
        return wrapper
    return deco


def call_tool(name: str, arguments: dict | str | None = None) -> dict:
    """Dispatcher: this is what you run when the LLM emits a function call."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": {"type": "invalid_arguments", "message": "Arguments are not valid JSON.", "retryable": False}}
    if name not in REGISTRY:
        return {"ok": False, "error": {"type": "unknown_tool", "message": f"No tool named '{name}'. Available: {list(REGISTRY)}", "retryable": False}}
    return REGISTRY[name]["fn"](**(arguments or {}))


def openai_tools() -> list:
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in REGISTRY.values()]


def anthropic_tools() -> list:
    return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in REGISTRY.values()]


def _http_json(url: str, data: dict | None = None, retries: int = 2, timeout: int = 8) -> dict:
    """HTTP helper with timeout + retry/backoff for transient failures."""
    last = None
    for attempt in range(retries + 1):
        try:
            body = json.dumps(data).encode() if data is not None else None
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise ToolError("http_error", f"HTTP {e.code} from service.", retryable=e.code >= 500)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(0.5 * (2 ** attempt))
    raise ToolError("network_error", f"Could not reach service after {retries + 1} attempts: {last}", retryable=True)


def _safe_path(rel_path: str) -> str:
    """Resolve a path inside BASE_DIR only (blocks ../ traversal)."""
    full = os.path.abspath(os.path.join(BASE_DIR, rel_path))
    if not (full == BASE_DIR or full.startswith(BASE_DIR + os.sep)):
        raise ToolError("access_denied", "Path is outside the allowed data directory.")
    if not os.path.isfile(full):
        raise ToolError("not_found", f"File not found: {rel_path}")
    return full


# ───────────────────────── 1. Calculator ─────────────────────────
_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
        ast.USub: op.neg, ast.UAdd: op.pos}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
          "log": math.log, "log10": math.log10, "abs": abs, "round": round}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval(n):
    if isinstance(n, ast.Expression):
        return _eval(n.body)
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
        return n.value
    if isinstance(n, ast.Name) and n.id in _CONSTS:
        return _CONSTS[n.id]
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        return _OPS[type(n.op)](_eval(n.operand))
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        l, r = _eval(n.left), _eval(n.right)
        if isinstance(n.op, ast.Pow) and abs(r) > 100:
            raise ToolError("invalid_arguments", "Exponent too large.")
        return _OPS[type(n.op)](l, r)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
        return _FUNCS[n.func.id](*[_eval(a) for a in n.args])
    raise ToolError("invalid_arguments", "Unsupported expression. Use numbers, + - * / ** % //, sqrt, sin, cos, tan, log, pi, e.")


@tool("calculator", "Evaluate a math expression exactly (e.g. '12.5/100*2400', 'sqrt(144)'). Use for ANY arithmetic instead of mental math.",
      {"expression": {"type": "string", "description": "Math expression"}}, ["expression"])
def calculator(expression: str):
    try:
        result = _eval(ast.parse(expression.strip(), mode="eval"))
    except ZeroDivisionError:
        raise ToolError("math_error", "Division by zero.")
    except (SyntaxError, ValueError, OverflowError) as e:
        raise ToolError("invalid_arguments", f"Cannot evaluate expression: {e}")
    return {"expression": expression, "result": result}


# ───────────────────────── 2. Web Search ─────────────────────────
@tool("web_search", "Search the web for current or external information (news, facts, prices). Not for private/company data.",
      {"query": {"type": "string", "description": "Search query"},
       "max_results": {"type": "integer", "description": "1-10, default 3"}}, ["query"])
def web_search(query: str, max_results: int = 3):
    if not query.strip():
        raise ToolError("invalid_arguments", "Query is empty.")
    max_results = max(1, min(int(max_results), 10))
    key = os.getenv("TAVILY_API_KEY")
    if not key:  # graceful fallback so the pipeline still runs without a key
        return {"mock": True, "note": "Set TAVILY_API_KEY for real results.",
                "results": [{"title": f"Mock result for '{query}'", "url": "https://example.com", "snippet": "Placeholder snippet."}][:max_results]}
    data = _http_json("https://api.tavily.com/search", {"api_key": key, "query": query, "max_results": max_results})
    return {"mock": False, "results": [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content", "")[:300]} for r in data.get("results", [])]}


# ───────────────────────── 3. Database Tool (practical project) ─────────────────────────
@tool("database_tool", "Read-only SQL on the company SQLite database. action='schema' lists tables/columns (call first if unsure); action='query' runs a single SELECT.",
      {"action": {"type": "string", "enum": ["schema", "query"]},
       "sql": {"type": "string", "description": "SELECT statement (for action='query')"},
       "db_file": {"type": "string", "description": "DB file inside the data dir, default company.db"},
       "max_rows": {"type": "integer", "description": "Row cap, default 100"}}, ["action"])
def database_tool(action: str, sql: str = "", db_file: str = "company.db", max_rows: int = 100):
    db_path = _safe_path(db_file)
    if action == "schema":
        return dbt.get_schema(db_path)
    if action == "query":
        return dbt.run_query(db_path, sql, max_rows=max_rows)
    raise ToolError("invalid_arguments", "action must be 'schema' or 'query'.")


# ───────────────────────── 4. File Reader ─────────────────────────
@tool("file_reader", "Read a text-based file (.txt .md .csv .json .pdf) from the data directory and return its content.",
      {"path": {"type": "string", "description": "Relative file path"},
       "max_chars": {"type": "integer", "description": "Truncate output, default 5000"}}, ["path"])
def file_reader(path: str, max_chars: int = 5000):
    full = _safe_path(path)
    ext = os.path.splitext(full)[1].lower()
    if ext in (".txt", ".md", ".csv"):
        with open(full, encoding="utf-8", errors="replace") as f:
            text = f.read()
    elif ext == ".json":
        with open(full, encoding="utf-8") as f:
            text = json.dumps(json.load(f), indent=2)
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ToolError("missing_dependency", "Install pypdf: pip install pypdf")
        text = "\n".join((p.extract_text() or "") for p in PdfReader(full).pages)
    else:
        raise ToolError("unsupported_type", f"Unsupported file type '{ext}'.")
    return {"path": path, "chars": len(text), "truncated": len(text) > max_chars, "content": text[:max_chars]}


# ───────────────────────── 5. Weather Tool ─────────────────────────
@tool("weather_tool", "Get current weather for a city (temperature, humidity, wind). Uses Open-Meteo, no API key.",
      {"city": {"type": "string", "description": "City name, e.g. 'Nagpur'"}}, ["city"])
def weather_tool(city: str):
    geo = _http_json("https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": city, "count": 1}))
    if not geo.get("results"):
        raise ToolError("not_found", f"City '{city}' not found.")
    g = geo["results"][0]
    w = _http_json("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
        "latitude": g["latitude"], "longitude": g["longitude"],
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m"}))
    c = w["current"]
    return {"city": g["name"], "country": g.get("country"), "temperature_c": c["temperature_2m"],
            "humidity_pct": c["relative_humidity_2m"], "wind_kmh": c["wind_speed_10m"]}


# ───────────────────────── 6. Email Tool ─────────────────────────
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@tool("email_tool", "Send an email. Defaults to dry_run=True (preview only). Set dry_run=false only when the user clearly confirmed sending.",
      {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"},
       "dry_run": {"type": "boolean", "description": "Preview without sending (default true)"}}, ["to", "subject", "body"])
def email_tool(to: str, subject: str, body: str, dry_run: bool = True):
    if not _EMAIL_RE.match(to):
        raise ToolError("invalid_arguments", f"Invalid email address: {to}")
    if dry_run:
        return {"status": "dry_run", "to": to, "subject": subject, "body_preview": body[:200]}
    host, user, pwd = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not (host and user and pwd):
        raise ToolError("config_error", "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD env vars.")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
    except (smtplib.SMTPException, OSError) as e:
        raise ToolError("send_failed", f"Email not sent: {e}", retryable=True)
    return {"status": "sent", "to": to, "subject": subject}


# ───────────────────────── 7. Date Tool ─────────────────────────
@tool("date_tool", "Date/time operations: now, add_days, diff_days, weekday. Use for 'today', 'in 10 days', 'days until', etc.",
      {"operation": {"type": "string", "enum": ["now", "add_days", "diff_days", "weekday"]},
       "date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
       "date2": {"type": "string", "description": "Second ISO date (diff_days)"},
       "days": {"type": "integer", "description": "Days to add (add_days), can be negative"},
       "timezone": {"type": "string", "description": "IANA tz, default Asia/Kolkata"}}, ["operation"])
def date_tool(operation: str, date: str | None = None, date2: str | None = None, days: int = 0, timezone: str = "Asia/Kolkata"):
    def parse(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ToolError("invalid_arguments", f"Date must be YYYY-MM-DD, got: {s!r}")
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        raise ToolError("invalid_arguments", f"Unknown timezone: {timezone}")
    if operation == "now":
        n = datetime.now(tz)
        return {"datetime": n.isoformat(timespec="seconds"), "date": n.date().isoformat(), "weekday": n.strftime("%A")}
    if operation == "add_days":
        d = parse(date) + timedelta(days=days)
        return {"result": d.isoformat(), "weekday": d.strftime("%A")}
    if operation == "diff_days":
        return {"days": (parse(date2) - parse(date)).days}
    if operation == "weekday":
        return {"weekday": parse(date).strftime("%A")}
    raise ToolError("invalid_arguments", "Unknown operation.")


# ───────────────────────── 8. Data Analyzer ─────────────────────────
@tool("data_analyzer", "Analyze a CSV in the data directory: shape, dtypes, missing values, numeric stats, top categories. Optionally group_by + metric column.",
      {"path": {"type": "string", "description": "CSV file path"},
       "group_by": {"type": "string", "description": "Column to group by (optional)"},
       "metric": {"type": "string", "description": "Numeric column to sum/mean per group (optional)"}}, ["path"])
def data_analyzer(path: str, group_by: str | None = None, metric: str | None = None):
    try:
        import pandas as pd
    except ImportError:
        raise ToolError("missing_dependency", "Install pandas: pip install pandas")
    df = pd.read_csv(_safe_path(path))
    out = {
        "shape": list(df.shape),
        "columns": {c: str(t) for c, t in df.dtypes.items()},
        "missing": {c: int(v) for c, v in df.isna().sum().items() if v},
        "numeric_summary": df.describe().round(2).to_dict() if len(df.select_dtypes("number").columns) else {},
        "top_categories": {c: df[c].value_counts().head(3).to_dict() for c in df.select_dtypes(exclude="number").columns},
    }
    if group_by or metric:
        for col in (group_by, metric):
            if col not in df.columns:
                raise ToolError("invalid_arguments", f"Column '{col}' not found. Columns: {list(df.columns)}")
        out["grouped"] = df.groupby(group_by)[metric].agg(["sum", "mean", "count"]).round(2).to_dict("index")
    return out


# ───────────────────────── 9. CSV Analyzer (practical project) ─────────────────────────
@tool("csv_analyzer", "Deep CSV analysis. action='profile' (default): stats, missing %, outliers, quality warnings. Also: group_by (by+metric+agg), top_n (column,n), filter (column,op,value), correlation. Call profile first on an unknown file.",
      {"path": {"type": "string", "description": "CSV file path inside the data dir"},
       "action": {"type": "string", "enum": ["profile", "group_by", "top_n", "filter", "correlation"]},
       "column": {"type": "string", "description": "Column for top_n / filter"},
       "by": {"type": "string", "description": "Category column for group_by"},
       "metric": {"type": "string", "description": "Numeric column for group_by"},
       "agg": {"type": "string", "enum": ["sum", "mean", "count", "min", "max", "median"]},
       "n": {"type": "integer", "description": "Rows for top_n, default 5"},
       "op": {"type": "string", "enum": ["eq", "ne", "gt", "gte", "lt", "lte", "contains"]},
       "value": {"type": "string", "description": "Filter value"},
       "ascending": {"type": "boolean", "description": "top_n: true for bottom N"}}, ["path"])
def csv_analyzer(path: str, action: str = "profile", column: str | None = None, by: str | None = None,
                 metric: str | None = None, agg: str = "sum", n: int = 5, op: str = "eq",
                 value: str | None = None, ascending: bool = False):
    return cat.analyze(_safe_path(path), action, column, by, metric, agg, n, op, value, ascending)


# ───────────────────────── Tool chaining ─────────────────────────
def run_chain(steps: list) -> dict:
    """
    steps: [(tool_name, args_dict_or_callable(ctx))]. ctx = {tool_name: data} of earlier steps.
    Stops at the first failure and returns the partial trace (no crash, no lost work).
    """
    ctx, trace = {}, []
    for name, args in steps:
        a = args(ctx) if callable(args) else args
        res = call_tool(name, a)
        trace.append({"tool": name, "args": a, "result": res})
        if not res["ok"]:
            return {"ok": False, "failed_at": name, "trace": trace}
        ctx[name] = res["data"]
    return {"ok": True, "trace": trace}


# ───────────────────────── Demo ─────────────────────────
if __name__ == "__main__":
    os.makedirs(BASE_DIR, exist_ok=True)
    csv_path = os.path.join(BASE_DIR, "sales.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("region,product,amount\nNorth,A,1200\nNorth,B,800\nSouth,A,1500\nSouth,B,700\nWest,A,900\nWest,B,400\n")
    dbt.load_csv_to_db(csv_path, os.path.join(BASE_DIR, "company.db"), "sales")

    def show(title, res):
        print(f"\n=== {title} ===")
        print(json.dumps(res, indent=2, default=str)[:900])

    show("calculator", call_tool("calculator", {"expression": "sqrt(144) + 12.5/100*2400"}))
    show("date_tool", call_tool("date_tool", {"operation": "add_days", "date": "2026-11-14", "days": 10}))
    show("file_reader", call_tool("file_reader", {"path": "sales.csv", "max_chars": 80}))
    show("data_analyzer", call_tool("data_analyzer", {"path": "sales.csv", "group_by": "region", "metric": "amount"}))
    show("database schema", call_tool("database_tool", {"action": "schema"}))
    show("database query", call_tool("database_tool", {"action": "query", "sql": "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC"}))

    messy = os.path.join(BASE_DIR, "orders.csv")
    with open(messy, "w", encoding="utf-8") as f:
        f.write("order_id,date,customer,category,amount,rating\n"
                "1,2026-10-01,Asha,Books,250,4\n2,2026-10-02,Ravi,Books,300,5\n3,2026-10-03,Asha,Games,1200,3\n"
                "4,2026-10-04,Meera,Games,1100,\n5,2026-10-05,Ravi,Books,280,4\n6,2026-10-06,Meera,Tech,45000,5\n"
                "7,2026-10-07,Asha,Tech,900,2\n7,2026-10-07,Asha,Tech,900,2\n")
    show("csv_analyzer profile", call_tool("csv_analyzer", {"path": "orders.csv"}))
    show("csv_analyzer group_by", call_tool("csv_analyzer", {"path": "orders.csv", "action": "group_by", "by": "category", "metric": "amount", "agg": "sum"}))
    show("csv_analyzer top_n", call_tool("csv_analyzer", {"path": "orders.csv", "action": "top_n", "column": "amount", "n": 2}))
    show("csv_analyzer filter", call_tool("csv_analyzer", {"path": "orders.csv", "action": "filter", "column": "amount", "op": "gt", "value": "1000"}))
    show("csv_analyzer correlation", call_tool("csv_analyzer", {"path": "orders.csv", "action": "correlation"}))
    show("csv_analyzer bad column", call_tool("csv_analyzer", {"path": "orders.csv", "action": "group_by", "by": "city", "metric": "amount"}))
    show("csv_analyzer text metric", call_tool("csv_analyzer", {"path": "orders.csv", "action": "top_n", "column": "customer"}))
    show("web_search (mock w/o key)", call_tool("web_search", {"query": "latest Python release"}))
    show("email dry run", call_tool("email_tool", {"to": "boss@example.com", "subject": "Report", "body": "Hello"}))

    print("\n##### ERROR HANDLING #####")
    show("DROP blocked", call_tool("database_tool", {"action": "query", "sql": "DROP TABLE sales"}))
    show("path traversal blocked", call_tool("file_reader", {"path": "../../etc/passwd"}))
    show("divide by zero", call_tool("calculator", {"expression": "5/0"}))
    show("bad args (missing)", call_tool("date_tool", {}))
    show("unknown tool", call_tool("teleport", {}))
    show("weather (fails gracefully offline)", call_tool("weather_tool", {"city": "Nagpur"}))

    print("\n##### TOOL CHAIN: DB -> Calculator -> Email #####")
    chain = run_chain([
        ("database_tool", {"action": "query", "sql": "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC"}),
        ("calculator", lambda c: {"expression": f"{c['database_tool']['rows'][0][1]} / ({'+'.join(str(r[1]) for r in c['database_tool']['rows'])}) * 100"}),
        ("email_tool", lambda c: {"to": "manager@example.com", "subject": "Top region share",
                                   "body": f"Top region: {c['database_tool']['rows'][0][0]} with {c['calculator']['result']:.1f}% of total sales."}),
    ])
    print(json.dumps(chain, indent=2, default=str))
