import os
import requests
import xml.etree.ElementTree as ET

# GitHub Secrets에서 환경변수 로드
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 감시 키워드 설정
TARGET_KEYWORDS = ['주주배정', '반대매매', '대표이사변경', '횡령', '배임', '부정거래', '추가상장']

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, json=payload)

def check_dart_rss():
    # DART 최신공시 RSS 주소 (IP 제한 없음)
    rss_url = "https://dart.fss.or.kr/api/todayRSS.xml"
    
    try:
        response = requests.get(rss_url, timeout=10)
        if response.status_code != 200:
            return

        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 파일에서 이미 확인한 공시 ID(link) 목록 불러오기 (중복 알림 방지)
        history_file = "history.txt"
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                sent_links = set(f.read().splitlines())
        else:
            sent_links = set()

        new_links = []
        
        # RSS 내부 item(공시)들 탐색
        for item in root.findall('.//item'):
            title = item.find('title').text # [회사명]공시제목 형식
            link = item.find('link').text # 공시 상세페이지 주소
            
            # 이미 처리한 공시는 생략
            if link in sent_links:
                continue
            
            new_links.append(link)

            # 키워드 매칭
            for keyword in TARGET_KEYWORDS:
                if keyword in title:
                    # 알림 전송 생성
                    msg = f"🚨 *DART 위험 키워드 감지*\n\n📄 내용: {title}\n🔗 링크: {link}"
                    send_telegram(msg)
                    break # 한 공시에 키워드가 여러 개 있어도 알림은 1번만
        
        # 새로 확인한 공시들을 히스토리 파일에 업데이트하여 저장소에 기록 유지
        with open(history_file, "a") as f:
            for l in new_links:
                f.write(l + "\n")

    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    check_dart_rss()
