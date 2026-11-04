from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
from threading import Lock
import json
import time

import sec_analyzer as sec

CACHE_SECONDS = 3600
REQUEST_GAP_SECONDS = 0.15
_cache = {}
_cache_lock = Lock()
_request_lock = Lock()
_last_request = 0.0


def cached_sec_json(session, key, url):
    global _last_request
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and now - entry[0] < CACHE_SECONDS:
            return entry[1]
    with _request_lock:
        now = time.monotonic()
        with _cache_lock:
            entry = _cache.get(key)
            if entry and now - entry[0] < CACHE_SECONDS:
                return entry[1]
        wait = REQUEST_GAP_SECONDS - (now - _last_request)
        if wait > 0:
            time.sleep(wait)
        payload = sec.get_json(session, url)
        _last_request = time.monotonic()
        with _cache_lock:
            _cache[key] = (_last_request, payload)
        return payload


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/analyze":
            self._send_json(404, {"error": "요청한 API 경로가 없습니다."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 8192:
                self._send_json(400, {"error": "요청 크기 또는 형식이 올바르지 않습니다."})
                return
            request_data = json.loads(self.rfile.read(length).decode("utf-8"))
            query = str(request_data.get("query", "")).strip()
            email = str(request_data.get("email", "")).strip()
            if len(query) > 100:
                self._send_json(400, {"error": "회사명이나 티커를 짧게 입력해 주세요."})
                return
            session = sec.make_session(email)
            directory = cached_sec_json(session, "company-directory", sec.SEC_TICKERS_URL)
            company = sec.resolve_company(query, directory)
            submissions = cached_sec_json(session, "submissions:" + company["cik"], sec.SUBMISSIONS_URL.format(cik=company["cik"]))
            facts = cached_sec_json(session, "facts:" + company["cik"], sec.COMPANYFACTS_URL.format(cik=company["cik"]))
            filings = sec.recent_annual_filings(submissions, company["cik"], limit=5)
            rows, currency = sec.build_annual_series(facts, filings)
            safe_rows = [{
                "year": row["year"], "period_end": row["period_end"],
                "revenue": row.get("revenue"), "net_income": row.get("net_income"),
                "assets": row.get("assets"), "liabilities": row.get("liabilities"),
                "operating_cash_flow": row.get("operating_cash_flow"),
                "filing": row["filing"],
            } for row in rows]
            self._send_json(200, {
                "company": company,
                "currency": currency or "보고 통화",
                "financials": safe_rows,
                "analysis": sec.analyze_series(rows),
                "filings": filings,
                "source": "SEC EDGAR Submissions API 및 Company Facts API",
            })
        except LookupError as exc:
            self._send_json(404, {"error": str(exc)})
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except sec.SecRequestError as exc:
            message = str(exc)
            status = 429 if "한도" in message else 502
            self._send_json(status, {"error": message})
        except Exception:
            self._send_json(500, {"error": "분석 서버에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."})

    def do_GET(self):
        self._send_json(405, {"error": "POST 요청으로 분석을 실행해 주세요."})
