from datetime import datetime
import time

def time_parse(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        except Exception as e:
            raise ValueError(f"時刻の解析に失敗しました: {ts}") from e

def raw_text_parse(data):
    msg = data.decode("utf-8").strip()
    latest_data = {}
    try:
        parts = dict(item.split("=") for item in msg.split(","))
        latest_data = {
            k: float(v)
            for k, v in parts.items()
            if v.replace(".", "", 1).replace("-", "", 1).isdigit()
        }
    except Exception as e:
        print(f"[RAW] Parse error Data: {data}")
        print(f"[RAW] Parse error: {e}")
    return latest_data
