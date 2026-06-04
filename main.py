import os
import requests
import datetime

# GitHub Secrets에서 환경변수 안전하게 로드
DART_API_KEY = os.environ.get('DART_API_KEY')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 감시할 핵심 고위험 키워드 목록
TARGET_KEYWORDS = ['주주배정', '반대매매', '대표이사변경', '횡령', '배임', '부정거래', '추가상장']

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def check_dart_api():
    # 오늘 날짜 확인 (YYYYMMDD)
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    # DART 당일 공시 목록조회 API (당일 데이터 최대 100건 수집)
    url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={DART_API_KEY}&bgn_de={today}&page_count=100"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"DART API 서버 응답 에러: {response.status_code}")
            return
            
        data = response.json()
        
        # DART 결과 상태 코드 검증 ('000'이 정상 조회)
        if data.get('status') != '000':
            print(f"DART 서비스 상태 메시지: {data.get('message')}")
            return

        # 기알림 내역 중복 제거 파일(history.txt) 로드
        history_file = "history.txt"
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                sent_reports = set(f.read().splitlines())
        else:
            sent_reports = set()

        new_reports = []
        
        # 공시 리스트 순회 검사
        for report in data.get('list', []):
            rcept_no = report.get('rcept_no')   # 공시 고유번호
            report_nm = report.get('report_nm') # 공시 제목
            corp_nm = report.get('corp_nm')     # 회사명
            
            # 이미 이전 루프에서 알림 보낸 공시는 생략
            if rcept_no in sent_reports:
                continue
            
            new_reports.append(rcept_no)

            # 제목 내 키워드 포함 확인
            for keyword in TARGET_KEYWORDS:
                if keyword in report_nm:
                    # 마크다운 문법 특수문자 회피 처리
                    safe_title = report_nm.replace('[', '\[').replace(']', '\]')
                    safe_corp = corp_nm.replace('[', '\[').replace(']', '\]')
                    
                    # 텔레그램 발송 메시지 구성
                    msg = f"🚨 *DART API 위험 키워드 감지*\n\n🏢 *회사명:* {safe_corp}\n📄 *공시명:* {safe_title}\n🔗 *링크:* https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                    send_telegram(msg)
                    break
        
        # 신규 처리된 공시 고유번호 히스토리에 누적 저장
        with open(history_file, "a") as f:
            for r_no in new_reports:
                f.write(r_no + "\n")

    except Exception as e:
        print(f"시스템 오류 발생: {e}")

if __name__ == "__main__":
    check_dart_api()
