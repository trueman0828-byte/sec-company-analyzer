from datetime import date
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
ANNUAL_FORMS = {"10-K", "20-F", "40-F"}
METRICS = {
    "revenue": {"label": "매출", "tags": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax", "Revenue"], "duration": True},
    "net_income": {"label": "순이익", "tags": ["NetIncomeLoss", "ProfitLoss"], "duration": True},
    "assets": {"label": "총자산", "tags": ["Assets"], "duration": False},
    "liabilities": {"label": "총부채", "tags": ["Liabilities"], "duration": False},
    "operating_cash_flow": {"label": "영업현금흐름", "tags": ["NetCashProvidedByUsedInOperatingActivities", "CashFlowsFromUsedInOperatingActivities", "NetCashFlowsFromUsedInOperatingActivities"], "duration": True},
}

class SecRequestError(RuntimeError):
    pass


def make_session(contact_email: str):
    import requests
    email = contact_email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("SEC 요청에 사용할 유효한 연락처 이메일을 입력해 주세요.")
    session = requests.Session()
    session.headers.update({"User-Agent": f"SecCompanyAnalyzer/1.0 ({email})", "Accept-Encoding": "gzip, deflate", "Accept": "application/json"})
    return session


def get_json(session, url: str) -> dict:
    import requests
    try:
        response = session.get(url, timeout=25)
        if response.status_code == 429:
            raise SecRequestError("SEC 요청 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SecRequestError(f"SEC 데이터를 가져오지 못했습니다: {exc}") from exc


def resolve_company(query: str, directory: dict) -> dict:
    term = query.strip().casefold()
    if not term:
        raise LookupError("회사명이나 티커를 입력해 주세요.")
    companies = list(directory.values()) if isinstance(directory, dict) else directory
    for company in companies:
        ticker = str(company.get("ticker", "")).casefold()
        title = str(company.get("title", "")).casefold()
        if term == ticker or term == title:
            return {"cik": str(company["cik_str"]).zfill(10), "ticker": str(company.get("ticker", "")), "title": str(company.get("title", ""))}
    matches = [c for c in companies if term in str(c.get("title", "")).casefold()]
    if len(matches) == 1:
        c = matches[0]
        return {"cik": str(c["cik_str"]).zfill(10), "ticker": str(c.get("ticker", "")), "title": str(c.get("title", ""))}
    if matches:
        choices = ", ".join(f"{c.get('title', '')} ({c.get('ticker', '')})" for c in matches[:5])
        raise LookupError(f"여러 기업이 검색됐습니다. 티커를 입력해 주세요. 예: {choices}")
    raise LookupError("SEC 상장 기업 목록에서 찾지 못했습니다. 미국 상장 기업의 티커를 확인해 주세요.")


def _filing_link(cik: str, accession: str, primary_document: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{primary_document}"


def recent_annual_filings(submissions: dict, cik: str, limit: int = 5) -> list:
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    rows = []
    for index, form in enumerate(forms):
        if form not in ANNUAL_FORMS:
            continue
        end = recent.get("reportDate", [""] * len(forms))[index] or ""
        accession = recent.get("accessionNumber", [""] * len(forms))[index]
        primary = recent.get("primaryDocument", [""] * len(forms))[index]
        filed = recent.get("filingDate", [""] * len(forms))[index]
        if end and accession and primary:
            rows.append({"form": form, "filed": filed, "end": end, "accession": accession, "url": _filing_link(cik, accession, primary)})
    rows.sort(key=lambda row: (row["end"], row["filed"]), reverse=True)
    unique = {}
    for row in rows:
        unique.setdefault(row["end"], row)
    return list(unique.values())[:limit]


def _unit_for_metric(units: dict) -> str | None:
    for unit in ["USD", "EUR", "GBP", "CAD", "JPY", "CNY", "AUD", "CHF"]:
        if unit in units:
            return unit
    for unit in units:
        if "-per-" not in unit.casefold() and unit.casefold() not in {"shares", "pure"}:
            return unit
    return None


def _fact_value(facts: dict, tags: list, filing: dict, duration: bool):
    for taxonomy in ("us-gaap", "ifrs-full"):
        concepts = facts.get(taxonomy, {})
        for tag in tags:
            concept = concepts.get(tag)
            if not concept:
                continue
            unit = _unit_for_metric(concept.get("units", {}))
            if not unit:
                continue
            selected = []
            for item in concept["units"][unit]:
                if item.get("end") != filing["end"] or item.get("form") not in ANNUAL_FORMS or item.get("filed", "9999") > filing["filed"]:
                    continue
                start = item.get("start")
                if duration:
                    if not start:
                        continue
                    try:
                        days = (date.fromisoformat(item["end"]) - date.fromisoformat(start)).days
                    except ValueError:
                        continue
                    if not 300 <= days <= 400:
                        continue
                elif start:
                    continue
                selected.append(item)
            if selected:
                selected.sort(key=lambda item: (item.get("accn") == filing["accession"], item.get("filed", "")), reverse=True)
                try:
                    return float(selected[0]["val"]), unit
                except (KeyError, TypeError, ValueError):
                    pass
    return None, None


def build_annual_series(payload: dict, filings: list) -> tuple:
    facts = payload.get("facts", {})
    rows, currency = [], None
    for filing in sorted(filings, key=lambda item: item["end"]):
        row = {"year": filing["end"][:4], "period_end": filing["end"], "filing": filing}
        for key, definition in METRICS.items():
            value, unit = _fact_value(facts, definition["tags"], filing, definition["duration"])
            row[key], row[f"{key}_unit"] = value, unit
            if key == "revenue" and unit:
                currency = unit
        rows.append(row)
    return rows, currency


def analyze_series(rows: list) -> list:
    notes = []
    if not rows:
        return ["표시할 연간 재무 데이터가 없습니다."]
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    revenue = latest.get("revenue")
    old_revenue = previous.get("revenue") if previous else None
    if revenue is not None and old_revenue not in (None, 0):
        change = (revenue / old_revenue - 1) * 100
        notes.append(f"최근 연간 매출은 전년 대비 {abs(change):.1f}% {'증가' if change >= 0 else '감소'}했습니다.")
    elif revenue is not None:
        notes.append("최근 연간 매출은 확인됐지만 전년 비교값이 부족합니다.")
    income = latest.get("net_income")
    if revenue not in (None, 0) and income is not None:
        margin = income / revenue * 100
        notes.append(f"최근 연간 순이익률은 {margin:.1f}%입니다.")
        if margin < 0:
            notes.append("최근 연간 순손실이 보고됐습니다. 손실 원인을 공시 원문에서 확인하세요.")
    if previous and latest.get("net_income") is not None and previous.get("net_income") is not None:
        if latest["net_income"] < 0 <= previous["net_income"]:
            notes.append("전년 흑자에서 최근 연도 적자로 전환했습니다.")
        elif latest["net_income"] >= 0 > previous["net_income"]:
            notes.append("전년 적자에서 최근 연도 흑자로 전환했습니다.")
    cashflow = latest.get("operating_cash_flow")
    if cashflow is not None:
        notes.append("최근 영업현금흐름은 음수입니다. 현금 소진과 유동성 관련 공시를 확인하세요." if cashflow < 0 else "최근 영업현금흐름은 양수입니다.")
    assets, liabilities = latest.get("assets"), latest.get("liabilities")
    if assets not in (None, 0) and liabilities is not None:
        notes.append(f"최근 부채/자산 비율은 {liabilities / assets * 100:.1f}%입니다. (SEC XBRL 보고값 기준)")
    valid_revenue = [r for r in rows if r.get("revenue") is not None]
    if len(valid_revenue) >= 3 and valid_revenue[0]["revenue"] > 0 and valid_revenue[-1]["revenue"] > 0:
        periods = int(valid_revenue[-1]["period_end"][:4]) - int(valid_revenue[0]["period_end"][:4])
        if periods > 0:
            cagr = (valid_revenue[-1]["revenue"] / valid_revenue[0]["revenue"]) ** (1 / periods) - 1
            notes.append(f"확인 가능한 연간 매출의 기간 평균 성장률은 약 {cagr * 100:.1f}%입니다. (회계연도 간격 보정)")
    if not notes:
        notes.append("표준 SEC XBRL 항목에서 요약 가능한 재무 숫자를 충분히 찾지 못했습니다. 공시 원문을 확인해 주세요.")
    notes.append("규칙 기반 재무 요약이며 투자 조언이나 기업 전망이 아닙니다.")
    return notes
