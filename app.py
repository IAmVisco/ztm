import logging
import os
import json
import sys

import redis
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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

logger.handlers = []
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)

api_key = os.environ.get("ZTM_API_KEY")
if not api_key:
    raise RuntimeError("Missing API key. Provide ZTM_API_KEY environment variable.")

app_auth_token = os.environ.get("APP_AUTH_TOKEN")
if not app_auth_token:
    logger.warning("APP_AUTH_TOKEN is not set – /schedule will be unprotected.")

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
try:
    cache = redis.from_url(redis_url)
    cache.ping()
    logger.info(f"Connected to Redis at {redis_url}")
except Exception as e:
    logger.error(f"Could not connect to Redis: {e}")
    cache = None


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
    if app_auth_token:
        header_token = request.headers.get("X-Auth-Token")
        if not header_token or header_token != app_auth_token:
            return jsonify({"error": "Unauthorized"}), 401

    lines_param = request.args.get("lines")
    lines = _parse_lines_param(lines_param)
    if not lines:
        return jsonify({
            "error": "Missing or invalid 'lines' query parameter. Use e.g. ?lines=14,16,19"
        }), 422

    # We sort lines to ensure ?lines=14,16 and ?lines=16,14 hit the same cache key
    sorted_lines_str = ",".join(str(x) for x in sorted(lines))
    cache_key = f"schedule:{stop_id}:{stop_number}:{sorted_lines_str}"

    if cache:
        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for {cache_key}")
                return jsonify(json.loads(cached_data))
        except Exception as err:
            logger.error(f"Redis read error: {err}")

    try:
        departures = _fetch_departures(stop_id, stop_number, lines)
    except Exception as err:
        logger.exception("Failed to fetch departures")
        return jsonify({"error": "Failed to fetch data", "details": str(err)}), 502

    now_iso = datetime.now(ZoneInfo(os.environ.get("TIMEZONE", "CET"))).isoformat()
    body = {
        "departures": departures[:5],
        "updated_at": now_iso,
    }

    if cache:
        try:
            cache.set(cache_key, json.dumps(body), ex=60)
            logger.info(f"Cached data for {cache_key} (TTL 60s)")
        except Exception as err:
            logger.error(f"Redis write error: {err}")

    return jsonify(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)