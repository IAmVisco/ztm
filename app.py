import logging
import os
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, jsonify, request

from components import ZTMStopClient

app = Flask(__name__)
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
api_key = os.environ.get("ZTM_API_KEY")
if not api_key:
    raise "Missing API key. Provide ZTM_API_KEY environment variable."


def _parse_lines_param(value: Optional[str]) -> List[int]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",") if p.strip()]
    lines: List[int] = []
    for p in parts:
        try:
            lines.append(int(p))
        except ValueError:
            continue
    return lines


def _fetch_departures(stop_id: int, stop_number: str, lines: List[int]):
    client = ZTMStopClient(api_key, stop_id, stop_number)
    results = client.get(lines)

    combined: list[dict] = []
    for ln in lines:
        res = results.get(ln)
        if not res or not getattr(res, 'departures', None):
            continue
        for dep in res.departures:
            try:
                combined.append({
                    "line": ln,
                    "direction": getattr(dep, 'kierunek', None),
                    "time": getattr(dep, 'czas', None)[:5],
                    "time_to_depart": getattr(dep, 'time_to_depart', None),
                })
            except Exception:
                continue

    combined.sort(key=lambda d: (d.get("time_to_depart") is None, d.get("time_to_depart", 1_000_000)))
    return combined


@app.get("/schedule/<int:stop_id>/<stop_number>")
def schedule(stop_id: int, stop_number: str):
    lines_param = request.args.get("lines")
    lines = _parse_lines_param(lines_param)
    if not lines:
        return jsonify({
            "error": "Missing or invalid 'lines' query parameter. Use e.g. ?lines=14,16,19"
        }), 422

    try:
        departures = _fetch_departures(stop_id, stop_number, lines)
    except Exception as e:
        logger.exception("Failed to fetch departures")
        return jsonify({"error": "Failed to fetch data", "details": str(e)}), 502

    now_iso = datetime.now(ZoneInfo(os.environ.get("TIMEZONE", "CET"))).isoformat()
    body = {
        "departures": departures[:5],
        "stop_id": stop_id,
        "stop_number": stop_number,
        "lines": lines,
        "updated_at": now_iso,
    }
    return jsonify(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
