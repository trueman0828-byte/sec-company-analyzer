# SEC 기업 분석 웹앱 (Python)

SEC EDGAR 공개 API를 조회하는 두 가지 실행 화면이 들어 있습니다.

- 로컬 화면: Streamlit 기반 Python 웹앱, app.py
- 공개 웹 화면: 반응형 브라우저 UI, index.html, 그리고 Vercel Python API, api/analyze.py

## 로컬 PC에서 실행

Python 3.10 이상을 설치한 뒤 프로젝트 폴더에서 실행합니다.

Windows PowerShell:

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements-local.txt
    streamlit run app.py

macOS 또는 Linux:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements-local.txt
    streamlit run app.py

브라우저에서 http://localhost:8501 로 엽니다. 왼쪽 설정의 연락처 이메일은 SEC 요청 User-Agent에 사용됩니다.

## 공개 URL에 배포하는 방법

저장소는 trueman0828-byte/sec-company-analyzer 입니다. Vercel에서 New Project를 선택하고 이 GitHub 저장소를 가져오면 됩니다. 프로젝트 루트의 index.html이 웹 화면이고 api/analyze.py가 Python API 함수입니다. Vercel은 /api 아래 Python 함수를 주소 경로에 연결하고 requirements.txt의 Python 의존성을 설치합니다.

배포 후 Vercel이 발급한 https://...vercel.app 주소로 접속합니다. 공개 URL은 다른 사람이 열 수 있으므로 SEC 데이터 외에 비밀정보를 넣지 마세요. 접근 제어를 추가하지 않은 공개 API이므로 계정 사용량과 호스팅 플랜의 한도를 확인하세요.

Dockerfile은 로컬 Streamlit 앱 실행용입니다.

## 앱의 동작 방식

1. 브라우저에서 회사 티커와 연락처 이메일을 입력합니다.
2. 같은 사이트의 Python API가 SEC에 회사 목록, 제출 공시, XBRL Company Facts를 요청합니다.
3. Python 코드가 연간 보고 기간을 맞추고 최근 최대 5개 회계연도의 매출, 순이익, 자산, 부채, 영업현금흐름을 정리합니다.
4. 성장률·순이익률·부채/자산 비율을 계산하고 차트와 공시 원문 링크를 웹 화면에 돌려줍니다.

SEC 데이터 호출은 서버에서 처리합니다. SEC API는 CORS를 지원하지 않기 때문에 브라우저가 SEC에 직접 호출하지 않습니다. 반복 응답은 서버 메모리에 1시간 캐시하고 SEC 요청 간격을 둡니다.

## 데이터와 한계

- SEC company_tickers.json, submissions/CIK##########.json, api/xbrl/companyfacts/CIK##########.json을 사용합니다.
- 최근 최대 5개의 10-K, 20-F, 40-F 연간 보고서를 보여줍니다.
- 재무 숫자는 회사의 SEC 원본 보고 통화로 표시하며 10억 단위로 환산합니다.
- 주가, 시가총액, PER, 분기별 실적은 제공하지 않습니다.
- 표준 XBRL 태그에 맞지 않는 일부 회사 항목은 비어 있을 수 있습니다. 빈 값은 0이 아닙니다.
- 자동 분석은 규칙 기반 계산이며 생성형 AI 분석이나 투자 추천은 아닙니다.
- 정보 제공용이며 투자 조언이 아닙니다. 중요한 판단 전 SEC 원문을 확인하세요.

## SEC 공정 이용

API 키는 필요하지 않습니다. 요청 헤더에 서비스 식별자와 연락처를 넣고 SEC 공개 이용 지침에 맞춰 필요한 자료만 요청합니다. SEC는 현재 초당 최대 10회 요청을 안내합니다.

공식 참고 자료:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- Vercel Python Functions: https://vercel.com/docs/functions/runtimes/python/api-directory

## 테스트

    python -m unittest discover -s tests -v
