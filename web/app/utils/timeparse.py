from datetime import datetime

def parse_iso(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        try:
            return datetime.strptime(ts, "%Y-%m-%dT%H:%M")
        except Exception as e:
            raise ValueError(f"時刻の解析に失敗しました: {ts}") from e
