# SEC 기업 분석 웹앱 (Python)

미국 SEC EDGAR의 공개 API로 상장 기업의 최근 연간 공시와 재무 데이터를 조회하는 Streamlit 웹앱입니다. 별도 SEC API 키는 필요하지 않습니다.

## 이 컴퓨터에서 실행하기

Python 3.10 이상을 설치한 뒤 터미널 또는 PowerShell에서 프로젝트 폴더로 이동하고 실행합니다.

Windows PowerShell:

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    streamlit run app.py

macOS 또는 Linux:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    streamlit run app.py

브라우저에서 보통 http://localhost:8501 로 열립니다. 앱 왼쪽 설정에서 실제 연락처 이메일을 입력하고 기업 티커(예: AAPL)를 검색하세요. 이메일은 SEC 요청 User-Agent에 들어갑니다.

## 다른 기기에서 사용하기

기본 실행은 이 컴퓨터 안에서만 열립니다. 같은 Wi-Fi의 기기에서 잠시 접속하려면 앱을 실행할 때 다음 명령을 사용하고, 다른 기기에서 이 컴퓨터의 로컬 IP 주소와 8501 포트로 접속합니다.

    streamlit run app.py --server.address 0.0.0.0 --server.port 8501

예: http://192.168.x.x:8501. 이 방법은 같은 신뢰할 수 있는 네트워크에서만 사용하고, 방화벽에서 로컬 네트워크 접근을 허용해야 할 수 있습니다. 인터넷 어디서나 접속하려면 프로젝트를 인터넷에 연결된 서버/클라우드에 배포해야 합니다. Dockerfile은 컨테이너 배포용 예시입니다. Streamlit Community Cloud, Render, Railway, Azure, AWS 등 Python 웹앱을 지원하는 호스팅을 이용할 수 있습니다.

배포 후에는 호스팅 서비스의 안내에 따라 저장소를 연결하고 시작 명령을 다음 형태로 설정합니다.

    streamlit run app.py --server.address 0.0.0.0 --server.port 8501

공개 배포 전 HTTPS, 접근 제어, 개인정보 안내, 공급자 비용 및 서비스 약관을 확인하세요. 개인용으로 항상 접속 가능하게 운영하려면 서버가 계속 실행되어야 합니다.

## 데이터와 한계

- SEC company_tickers.json, submissions/CIK##########.json, api/xbrl/companyfacts/CIK##########.json 사용
- 최근 최대 5개의 10-K, 20-F, 40-F 연간 보고서 표시
- 매출, 순이익, 총자산, 총부채, 영업현금흐름 추세 분석
- 재무 금액은 SEC 원본 보고 통화로 표시하고 10억 단위로 환산합니다.
- 주가, 시가총액, PER, 분기별 실적, 투자 추천은 제공하지 않습니다.
- 회사마다 XBRL 태그가 다르므로 일부 값은 누락될 수 있습니다. 빈 값은 0을 의미하지 않습니다.
- 자동 분석은 규칙 기반입니다. 생성형 AI 분석이나 공시 본문의 위험 요인 추출은 포함되지 않습니다.
- 정보 제공용 요약이며 투자 조언이 아닙니다. 중요한 결정 전 SEC 원본 공시를 확인하세요.

## 공식 참고 자료

- SEC EDGAR API 문서: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC 데이터 접근 및 공정 이용: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

## SEC 공정 이용

요청 헤더에 서비스 식별자와 연락처를 포함하며, 사용자가 실행할 때 필요한 API만 요청합니다. SEC의 현재 지침은 초당 최대 10회입니다. 앱은 조회 결과를 캐시해 반복 요청을 줄입니다.

## 테스트

    python -m unittest discover -s tests -v
