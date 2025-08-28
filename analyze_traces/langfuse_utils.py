from __future__ import annotations

import os, re, json, csv, math, itertools, statistics
import requests
from typing import Any, Dict, List, Iterable, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import numpy as np

LIMIT = 100

def iso_utc_plus(dt):  # ISO-8601 with explicit offset, no 'Z'
    return dt.astimezone(timezone.utc).isoformat()  # e.g., 2025-07-25T14:30:00+00:00


def _to_utc(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ZoneInfo("UTC"))
    except Exception:
        return None


def _to_ct(ts_utc):
    try:
        return ts_utc.astimezone(CT) if ts_utc else None
    except Exception:
        return None


def _msg_text(content):
    """Langfuse message content may be a string or a list of {type:'text', text:'...'}"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for c in content:
            if isinstance(c, dict):
                if "text" in c and isinstance(c["text"], str):
                    out.append(c["text"])
                elif "content" in c and isinstance(c["content"], str):
                    out.append(c["content"])
        return "\n".join(out)
    return ""


def _first_human_prompt(row):
    msgs = (((row.get("input") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "human":
            t = _msg_text(m.get("content"))
            if t and t.strip():
                return t.strip()
    return ""


def _final_ai_message(row):
    msgs = (((row.get("output") or {}).get("messages")) or [])
    # take the last AI message with non-empty content
    for m in reversed(msgs):
        if m.get("type") == "ai":
            t = _msg_text(m.get("content"))
            if t and t.strip():
                return t.strip(), (m.get("response_metadata") or {})
    return "", {}


def _collect_tool_names(row):
    names = set()
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "ai":
            for tc in (m.get("tool_calls") or []):
                n = tc.get("name")
                if n: names.add(str(n))
        elif m.get("type") == "tool":
            n = m.get("name")
            if n: names.add(str(n))
    return sorted(names)


def _any_tool_failure(row):
    """Detect failure from tool message text or explicit non-success status."""
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "tool":
            status = (m.get("status") or "").lower()
            text   = (_msg_text(m.get("content")) or "").lower()
            if status and status not in ("success","succeeded","ok"):
                return True
            if "fail" in text or "error" in text or "exception" in text:
                return True
    return False


def _pull_data_args(row):
    """Extract aoi_name, dataset_name, start_date, end_date from pull-data tool_calls."""
    aoi = ds = sd = ed = None
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "ai":
            for tc in (m.get("tool_calls") or []):
                if tc.get("name") == "pull-data":
                    args = tc.get("args") or {}
                    aoi = aoi or args.get("aoi_name")
                    ds  = ds  or args.get("dataset_name")
                    sd  = sd  or args.get("start_date")
                    ed  = ed  or args.get("end_date")
    return aoi, ds, sd, ed


def _from_pick_aoi(row):
    """Parse Selected AOI: <name> from tool messages."""
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "tool" and m.get("name") == "pick-aoi":
            text = _msg_text(m.get("content")) or ""
            # e.g., "Selected AOI: Odisha, India, type: state-province"
            mobj = re.search(r"Selected AOI:\s*(.*?)(?:,|\n|$)", text, flags=re.I)
            if mobj:
                val = mobj.group(1).strip()
                if val:
                    return val
    return None


def _from_pick_dataset(row):
    """Parse Selected dataset and Context layer from pick-dataset content."""
    sel = ctx = None
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in msgs:
        if m.get("type") == "tool" and m.get("name") == "pick-dataset":
            text = _msg_text(m.get("content")) or ""
            m1 = re.search(r"Selected dataset:\s*(.+)", text, flags=re.I)
            if m1:
                sel = (m1.group(1).splitlines()[0] or "").strip()
            m2 = re.search(r"Context layer:\s*(.+)", text, flags=re.I)
            if m2:
                ctx = (m2.group(1).splitlines()[0] or "").strip()
    return sel, ctx


def _apology_like(s):
    s = (s or "").lower()
    return any(x in s for x in ["sorry", "apolog", "unable to", "can’t", "can't", "cannot", "failed to", "error"])


def _duration_seconds(row):
    # Prefer explicit latency seconds; else derive from ms; else None
    for key in ("latency",):
        v = row.get(key)
        if isinstance(v, (int,float)): return float(v)
        try:
            return float(v)
        except Exception:
            pass
    for key in ("latencyMs","durationMs","duration"):
        v = row.get(key)
        if v is not None:
            try:
                return float(v)/1000.0
            except Exception:
                continue
    # As a last resort, try updatedAt - createdAt
    c = _to_utc(row.get("createdAt")) if row.get("createdAt") else None
    u = _to_utc(row.get("updatedAt")) if row.get("updatedAt") else None
    if c and u:
        dt = (u - c).total_seconds()
        if dt >= 0:
            return dt
    return None


def _duration_bucket(d):
    if d is None: return None
    bins = [0.5,1,2,5,10]
    labels = ["≤0.5s","0.5–1s","1–2s","2–5s","5–10s",">10s"]
    for thr, lab in zip(bins, labels):
        if d <= thr: return lab
    return labels[-1]


def _final_ai_tokens_out(row):
    msgs = (((row.get("output") or {}).get("messages")) or [])
    for m in reversed(msgs):
        if m.get("type") == "ai":
            meta = (m.get("response_metadata") or {})
            usage = meta.get("usage") or {}
            if "output_tokens" in usage:
                return usage.get("output_tokens")
    return None


def _outcome_status(row, tool_names, has_tool_failure, final_ai_text, aoi_name, dataset_name):
    if not tool_names:
        # No tools at all
        return "NO_TOOLS"
    # Any explicit failure or apology → ERROR
    if has_tool_failure or _apology_like(final_ai_text):
        return "ERROR"
    # Strong success: pull-data present and both AOI + dataset identified
    if "pull-data" in tool_names and (aoi_name or dataset_name) and (aoi_name and dataset_name):
        return "SUCCESS"
    # Tools ran but we don't have full info → PARTIAL
    return "PARTIAL"


def summarize(row):
    # timestamps
    ts_utc = _to_utc(row.get("timestamp")) if row.get("timestamp") else None
    created_utc = _to_utc(row.get("createdAt")) if row.get("createdAt") else None
    ts_ct = _to_ct(ts_utc) if ts_utc else None

    # prompts
    user_full = _first_human_prompt(row)
    user_trunc = (user_full[:160] + "…") if len(user_full) > 160 else user_full
    final_ai_text, _meta = _final_ai_message(row)
    ai_trunc = (final_ai_text[:300] + "…") if len(final_ai_text) > 300 else final_ai_text

    # tools & args
    tool_names = _collect_tool_names(row)
    tool_count = len(tool_names)
    has_tool_failure = _any_tool_failure(row)
    aoi_from_pick = _from_pick_aoi(row)
    ds_from_pick, ctx_from_pick = _from_pick_dataset(row)
    aoi_pd, ds_pd, sd_pd, ed_pd = _pull_data_args(row)

    selected_aoi = aoi_pd or aoi_from_pick
    selected_dataset = ds_pd or ds_from_pick
    dataset_context_layer = ctx_from_pick

    # performance/cost
    duration_s = _duration_seconds(row)
    duration_bucket = _duration_bucket(duration_s)
    tokens_out = _final_ai_tokens_out(row)
    has_output = bool(final_ai_text and final_ai_text.strip())
    total_cost = row.get("totalCost")

    # outcome
    outcome = _outcome_status(row, tool_names, has_tool_failure, final_ai_text, selected_aoi, selected_dataset)

    return {
        # identity
        "id": row.get("id"),
        "name": row.get("name"),
        "environment": row.get("environment"),

        # time
        "timestamp_utc": ts_utc.isoformat().replace("+00:00","Z") if ts_utc else None,
        "timestamp_ct": ts_ct.isoformat() if ts_ct else None,
        "createdAt_utc": created_utc.isoformat().replace("+00:00","Z") if created_utc else None,

        # performance
        "duration_s": round(duration_s, 3) if isinstance(duration_s, (int,float)) else None,
        "duration_bucket": duration_bucket,

        # outcome
        "outcome_status": outcome,
        "tool_names": "|".join(tool_names) if tool_names else "",
        "tool_count": tool_count,
        "has_tool_failure": has_tool_failure,
        "has_output": has_output,
        "final_ai_tokens_out": tokens_out,

        # cost
        "totalCost": total_cost,

        # prompts (as requested)
        "user_prompt_full": user_full,
        "user_prompt_trunc": user_trunc,
        "ai_output_trunc": ai_trunc,

        # AOI / dataset
        "selected_aoi": selected_aoi,
        "selected_dataset": selected_dataset,
        "dataset_context_layer": dataset_context_layer,
        "start_date": sd_pd,
        "end_date": ed_pd,
    }


def ct_window_iso(ct_str, minutes=60):
    ct = ZoneInfo("America/Chicago")
    start = datetime.strptime(ct_str, "%Y-%m-%d %H:%M").replace(tzinfo=ct)
    end = start + timedelta(minutes=minutes)
    # explicit +00:00 (not 'Z')
    return start.astimezone(ZoneInfo("UTC")).isoformat(), end.astimezone(ZoneInfo("UTC")).isoformat()


def fetch_window(from_iso, to_iso, base_url, headers, limit=LIMIT):
    url = f"{base_url.rstrip('/')}/api/public/traces"
    rows, next_page = [], None
    while True:
        params = {"fromTimestamp": from_iso, "toTimestamp": to_iso, "limit": limit}
        if next_page: params["page"] = next_page
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        batch = data.get("data") if isinstance(data, dict) else data
        if not batch: break
        rows.extend(batch)
        next_page = data.get("nextPage") if isinstance(data, dict) else None
        if not next_page or len(batch) < limit: break
        time.sleep(0.05)
    return rows


def save_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items: f.write(json.dumps(it, ensure_ascii=False) + "\n")


def save_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows: open(path, "w").close(); return
    fields = sorted({k for r in rows for k in r.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def safe_read_csv(p):
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(p, dtype=str)  # keep raw, coerce later
    for col in ["duration_ms"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["timestamp"]:
        if col in df:
            # tolerate both UTC with offset and naive strings
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
    # normalize status
    if "status" in df:
        df["status"] = df["status"].astype(str).str.upper().str.strip()
    # normalize tags
    if "tags" in df:
        df["tags"] = df["tags"].fillna("").astype(str)
    return df


def read_jsonl(p):
    if not p.exists() or p.stat().st_size == 0:
        return []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def p95(x):
    x = pd.to_numeric(x, errors="coerce"); x = x[~x.isna()]
    return np.nan if x.empty else np.percentile(x, 95)


def explode_tools(df):
    tmp = df.copy()
    tmp["tool_names_list"] = tmp["tool_names"].fillna("").apply(lambda s: [t for t in s.split("|") if t])
    return tmp.explode("tool_names_list")


def split_tags(s):
    if pd.isna(s) or not s:
        return []
    return [t.strip() for t in str(s).split(",") if t.strip()]


def show_trace(interview, trace_id):
    rec = jsonl_index.get(interview, {}).get(trace_id)
    if not rec:
        print("Not found.")
        return
    # print a few useful fields; edit as needed
    keys = ["id","timestamp","name","status","userId","projectId","environment","tags","durationMs"]
    for k in keys:
        print(f"{k}: {rec.get(k)}")
    # Show input/output if present
    if "input" in rec:
        print("\ninput:")
        print(json.dumps(rec["input"], ensure_ascii=False)[:2000])
    if "output" in rec:
        print("\noutput:")
        print(json.dumps(rec["output"], ensure_ascii=False)[:2000])
