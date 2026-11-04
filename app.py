import streamlit as st
import sec_analyzer as sec

st.set_page_config(page_title="SEC 기업 분석", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1120px; padding-top: 2.5rem; }
.hero { padding: 1.4rem 1.6rem; border: 1px solid #e4ebf4; border-radius: 18px; background: linear-gradient(120deg,#f5f8ff,#ffffff); margin-bottom: 1.1rem; }
.hero h1 { margin: 0 0 .35rem 0; color: #18293a; }
.hero p { color: #607083; margin: 0; }
[data-testid="stMetric"] { border: 1px solid #e5eaf0; border-radius: 14px; padding: 14px 16px; background: white; }
</style>
<div class="hero"><h1>SEC 기업 분석</h1><p>미국 상장 기업의 SEC 연간 공시와 XBRL 재무 데이터를 모아 핵심 추세를 요약합니다.</p></div>
""", unsafe_allow_html=True)
st.caption("데이터 제공: 미국 증권거래위원회(SEC) | 10-K·20-F·40-F 연간 공시 기준")
with st.sidebar:
    st.subheader("SEC 연결 설정")
    contact_email = st.text_input("연락처 이메일", placeholder="name@example.com", help="SEC API User-Agent에 연락처로 포함됩니다.")
    st.caption("SEC 자동 요청 정책에 따라 실제 연락 가능한 이메일을 입력해 주세요.")
    st.divider()
    st.caption("SEC 공개 API를 사용합니다. API 키는 필요하지 않습니다. 연락처는 SEC 요청 헤더에만 포함됩니다.")

@st.cache_data(ttl=86400, show_spinner=False)
def load_directory(email: str):
    return sec.get_json(sec.make_session(email), sec.SEC_TICKERS_URL)

@st.cache_data(ttl=3600, show_spinner=False)
def load_company(cik: str, email: str):
    session = sec.make_session(email)
    submissions = sec.get_json(session, sec.SUBMISSIONS_URL.format(cik=cik))
    facts = sec.get_json(session, sec.COMPANYFACTS_URL.format(cik=cik))
    return submissions, facts

with st.form("search_company", clear_on_submit=False):
    query = st.text_input("회사명 또는 티커", placeholder="예: AAPL 또는 Apple Inc.")
    submitted = st.form_submit_button("기업 분석", type="primary", use_container_width=True)

if submitted:
    st.session_state.pop("company_result", None)
    if not contact_email.strip():
        st.error("먼저 왼쪽에서 연락처 이메일을 입력해 주세요. SEC의 User-Agent 정책을 위한 설정입니다.")
    elif not query.strip():
        st.warning("회사명이나 티커를 입력해 주세요.")
    else:
        try:
            with st.spinner("SEC 상장 기업 목록을 확인하는 중..."):
                directory = load_directory(contact_email.strip())
                company = sec.resolve_company(query, directory)
            with st.spinner(f"{company['title']}의 공시와 재무 데이터를 가져오는 중..."):
                submissions, facts_payload = load_company(company["cik"], contact_email.strip())
                filings = sec.recent_annual_filings(submissions, company["cik"], limit=5)
                rows, currency = sec.build_annual_series(facts_payload, filings)
            st.session_state["company_result"] = {"company": company, "filings": filings, "rows": rows, "currency": currency}
        except LookupError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(str(exc))
        except sec.SecRequestError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"분석 중 예상하지 못한 오류가 발생했습니다: {exc}")

result = st.session_state.get("company_result")
if result:
    company, filings, rows = result["company"], result["filings"], result["rows"]
    currency = result.get("currency") or "보고 통화"
    st.divider()
    st.subheader(f"{company['title']} ({company['ticker']})")
    latest = rows[-1] if rows else {}
    st.caption(f"CIK {company['cik']} · 최근 연간 보고 기간: {latest.get('period_end', '데이터 없음')} · SEC 원문 수치 기준")
    if not rows:
        st.warning("최근 연간 보고서를 찾지 못했습니다. 지원 대상 SEC 공시인지 확인해 주세요.")
    else:
        metric_cols = st.columns(4)
        summary_cards = [("최근 매출", latest.get("revenue")), ("최근 순이익", latest.get("net_income")), ("영업현금흐름", latest.get("operating_cash_flow")), ("총자산", latest.get("assets"))]
        for col, (label, value) in zip(metric_cols, summary_cards):
            shown = "데이터 없음" if value is None else f"{value / 1_000_000_000:,.2f} B {currency}"
            col.metric(label, shown, help="SEC XBRL 원값을 보고 통화의 10억 단위로 표시")
        st.markdown("#### 재무 추세")
        chart_rows = [{"연도": row["year"], "매출": row["revenue"] / 1_000_000_000 if row.get("revenue") is not None else None,
                       "순이익": row["net_income"] / 1_000_000_000 if row.get("net_income") is not None else None,
                       "영업현금흐름": row["operating_cash_flow"] / 1_000_000_000 if row.get("operating_cash_flow") is not None else None} for row in rows]
        st.caption(f"세로축: 10억 {currency}. 회계연도 기준이며, 표준 XBRL 태그가 없는 항목은 비어 있을 수 있습니다.")
        st.line_chart(chart_rows, x="연도", y=["매출", "순이익", "영업현금흐름"], use_container_width=True)
        st.markdown("#### 연도별 재무 데이터")
        labels = [("revenue", "매출"), ("net_income", "순이익"), ("operating_cash_flow", "영업현금흐름"), ("assets", "총자산"), ("liabilities", "총부채")]
        table_rows = []
        for row in reversed(rows):
            item = {"회계연도 종료": row["period_end"], "공시": row["filing"]["form"]}
            for key, label in labels:
                value = row.get(key)
                item[f"{label} (십억 {currency})"] = None if value is None else round(value / 1_000_000_000, 3)
            table_rows.append(item)
        st.dataframe(table_rows, hide_index=True, use_container_width=True)
        st.markdown("#### 자동 재무 요약")
        st.caption("SEC 보고 수치에 기반한 규칙형 요약입니다. 생성형 AI가 작성한 내용은 아닙니다.")
        for note in sec.analyze_series(rows):
            st.markdown(f"- {note}")
    st.markdown("#### 최근 연간 공시")
    if filings:
        for filing in filings:
            st.link_button(f"{filing['form']} · 회계기간 {filing['end']} · 제출 {filing['filed']}", filing["url"])
    else:
        st.info("표시할 연간 공시 링크가 없습니다.")
    st.caption("원본 데이터: SEC Submissions API 및 Company Facts API. 조회 시점에 따라 수정되거나 추가될 수 있습니다.")
else:
    st.info("회사 티커를 입력하면 최근 연간 공시와 재무 추세를 확인할 수 있습니다. 예: AAPL")
    with st.expander("현재 버전에서 확인할 수 있는 항목"):
        st.markdown("""
        - 최근 최대 5개 연간 보고서(10-K, 20-F, 40-F)
        - 매출, 순이익, 총자산, 총부채, 영업현금흐름
        - 전년 대비 매출 변화, 순이익률, 부채/자산 비율 등 규칙 기반 요약
        - 각 공시 원문 링크

        SEC XBRL 태그는 회사마다 다르므로 일부 값은 비어 있을 수 있습니다. 값이 없다는 것이 0을 뜻하지는 않습니다.
        """)
