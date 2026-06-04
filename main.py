import os
import requests
import datetime

# --- 환경 변수 로드 ---
DART_API_KEY = os.environ.get('DART_API_KEY')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OWNER_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 감시할 핵심 고위험 키워드 목록
TARGET_KEYWORDS = ['주주배정', '반대매매', '대표이사변경', '횡령', '배임', '부정거래', '추가상장']

USERS_FILE = "users.txt"
HISTORY_FILE = "history.txt"


def load_users():
    """저장된 수신자 명단을 파일에서 읽어옴 (기본적으로 관리자 ID 포함)"""
    users = set()
    if OWNER_CHAT_ID:
        users.add(OWNER_CHAT_ID)
        
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            for line in f.read().splitlines():
                if line.strip():
                    users.add(line.strip())
    return users


def update_new_users(current_users):
    """봇에게 /start를 누른 새로운 사용자를 감지하여 등록"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    new_users_detected = False
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for update in data.get('result', []):
                message = update.get('message', {})
                chat_id = str(message.get('chat', {}).get('id', ''))
                text = message.get('text', '')
                
                # 사용자가 봇방에서 /start를 눌렀고 기존 명단에 없다면 추가
                if chat_id and text.startswith('/start') and chat_id not in current_users:
                    current_users.add(chat_id)
                    new_users_detected = True
                    # 가입 환영 메시지 발송
                    welcome_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    requests.post(welcome_url, json={'chat_id': chat_id, 'text': "🔔 DART 실시간 공시 알림 시스템에 정상 등록되었습니다. 지정 키워드 공시 발생 시 알림이 전송됩니다."}, timeout=5)
                    
        if new_users_detected:
            with open(USERS_FILE, "w") as f:
                for u in sorted(current_users):
                    f.write(u + "\n")
                    
    except Exception as e:
        print(f"사용자 갱신 오류: {e}")
        
    return current_users


def send_telegram_to_all(users, message):
    """등록된 모든 사용자에게 메시지 순차 발송"""
    for chat_id in users:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            print(f"전송 실패 (Chat ID: {chat_id}): {e}")


def check_dart_api(users):
    """DART Open API 목록 조회 및 매칭 검사"""
    today = datetime.datetime.now().strftime('%Y%m%d')
    url = f"https://opendart.fss.or.kr/api/list.json?crtfc_key={DART_API_KEY}&bgn_de={today}&page_count=100"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return
        data = response.json()
        if data.get('status') != '000': return

        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                sent_reports = set(f.read().splitlines())
        else:
            sent_reports = set()

        new_reports = []
        
        for report in data.get('list', []):
            rcept_no = report.get('rcept_no')
            report_nm = report.get('report_nm')
            corp_nm = report.get('corp_nm')
            
            if rcept_no in sent_reports:
                continue
            
            new_reports.append(rcept_no)

            for keyword in TARGET_KEYWORDS:
                if keyword in report_nm:
                    safe_title = report_nm.replace('[', '\[').replace(']', '\]')
                    safe_corp = corp_nm.replace('[', '\[').replace(']', '\]')
                    msg = f"🚨 *DART API 위험 키워드 감지*\n\n🏢 *회사명:* {safe_corp}\n📄 *공시명:* {safe_title}\n🔗 *링크:* https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                    
                    send_telegram_to_all(users, msg)
                    break
        
        with open(HISTORY_FILE, "a") as f:
            for r_no in new_reports:
                f.write(r_no + "\n")

    except Exception as e:
        print(f"DART 조회 오류 발생: {e}")


if __name__ == "__main__":
    # 1. 기존 명단 로드
    registered_users = load_users()
    # 2. 신규 대화 참가자 수집 및 명단 업데이트
    registered_users = update_new_users(registered_users)
    # 3. 공시 체크 및 발송
    check_dart_api(registered_users)
