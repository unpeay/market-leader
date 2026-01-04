import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime
import json

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인 (KT 멤버십 스타일)
# ==========================================
st.set_page_config(
    page_title="Market Leader Pro",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>
    .stApp { background-color: #f4f6f9; font-family: 'Pretendard', sans-serif; }
    
    /* 메인 타이틀 */
    .main-title {
        font-size: 1.8rem; font-weight: 800; color: #222;
        margin-bottom: 1rem; padding-left: 10px;
        border-left: 5px solid #e74c3c;
    }
    
    /* 테마 박스 */
    .theme-box {
        background-color: #ffffff; border-radius: 16px; padding: 20px;
        margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .theme-header {
        font-size: 1.3rem; font-weight: 700; color: #333;
        margin-bottom: 15px; display: flex; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom:10px;
    }
    
    /* 종목 카드 */
    .stock-card {
        background-color: #fdfdfd; border: 1px solid #e0e0e0;
        border-radius: 12px; padding: 15px; margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .stock-card:hover { border-color: #e74c3c; transform: translateY(-2px); }
    
    /* 카드 내용 */
    .card-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .stock-name { font-size: 1.1rem; font-weight: 700; color:#222; }
    .rate-up { color: #e74c3c; font-weight:700; }
    .rate-down { color: #3498db; font-weight:700; }
    
    /* 뱃지 */
    .badge { padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; margin-right: 5px; }
    .badge-rank { background:#333; color:white; }
    .badge-grade { background:#e74c3c; color:white; }
    
    /* 상세 텍스트 */
    .sub-info { font-size: 0.9rem; color: #555; line-height: 1.6; margin-top: 8px; border-top: 1px dashed #eee; padding-top:8px;}
    .info-label { font-weight: 600; color: #333; }
    .news-link { text-decoration: none; color: #444; }
    .news-link:hover { color: #e74c3c; text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 한투 API 연동 모듈 (실제 시세 조회)
# ==========================================
class KIS_API:
    def __init__(self, app_key, app_secret):
        self.key = app_key
        self.secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443" # 실전투자
        self.token = None

    def auth(self):
        """토큰 발급"""
        try:
            headers = {"content-type": "application/json"}
            body = {"grant_type": "client_credentials", "appkey": self.key, "appsecret": self.secret}
            res = requests.post(f"{self.base_url}/oauth2/tokenP", headers=headers, json=body)
            if res.status_code == 200:
                self.token = res.json()["access_token"]
                return True
            return False
        except: return False

    def get_price(self, code):
        """현재가 조회"""
        if not self.token: return None
        try:
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.token}",
                "appkey": self.key, "appsecret": self.secret,
                "tr_id": "FHKST01010100"
            }
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
            res = requests.get(f"{self.base_url}/uapi/domestic-stock/v1/quotation/inquire-price", headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()['output']
                return {
                    'price': int(data['stck_prpr']), # 현재가
                    'rate': float(data['prdy_ctrt']), # 등락률
                    'vol': int(data['acml_vol']),     # 거래량
                    'high': int(data['stck_hgpr']),   # 고가
                    'low': int(data['stck_lwpr'])     # 저가
                }
        except: pass
        return None

# ==========================================
# 🧠 3. 네이버 뉴스/테마 크롤링 (종목 발굴용)
# ==========================================
@st.cache_data(ttl=600)
def get_naver_themes():
    # 한투 API는 '테마' 데이터가 없으므로 네이버에서 긁어와야 함
    themes = []
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 상위 5개 테마만 (API 호출 횟수 제한 고려)
        for t_link in soup.select('.col_type1 a')[:5]: 
            t_name = t_link.text.strip()
            link = "https://finance.naver.com" + t_link['href']
            
            sub_res = requests.get(link, headers={'User-Agent': 'Mozilla/5.0'})
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            
            stocks = []
            # 테마 내 상위 3개 종목 코드 추출
            for row in sub_soup.select('.type_5 tbody tr'):
                try:
                    cols = row.select('td')
                    if len(cols) < 2: continue
                    name = cols[0].text.strip()
                    code = cols[0].select_one('a')['href'].split('code=')[1]
                    
                    # 뉴스 제목 하나 가져오기
                    news_title = "관련 뉴스 없음"
                    try:
                        n_url = f"https://finance.naver.com/item/news_news.naver?code={code}"
                        n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'})
                        n_soup = BeautifulSoup(n_res.text, 'html.parser')
                        news_tag = n_soup.select_one('.type5 tbody tr .title a')
                        if news_tag: news_title = news_tag.text.strip()
                    except: pass
                    
                    stocks.append({'name': name, 'code': code, 'news': news_title})
                    if len(stocks) >= 3: break
                except: continue
                
            themes.append({'theme': t_name, 'stocks': stocks})
    except: pass
    return themes

# ==========================================
# 🖥️ 4. 메인 화면 로직
# ==========================================

# 사이드바: 한투 API 키 입력
with st.sidebar:
    st.header("🔑 한투 API 설정")
    # st.secrets를 쓰거나 직접 입력
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        st.success("API 키가 로드되었습니다!")
    except:
        APP_KEY = st.text_input("APP Key", type="password")
        APP_SECRET = st.text_input("APP Secret", type="password")
        st.caption("키가 없으면 네이버 데이터로 대체됩니다.")

# 메인 타이틀
st.markdown('<div class="main-title">📈 오늘의 종가베팅 (한투 API 연동)</div>', unsafe_allow_html=True)

if st.button("🚀 실시간 데이터 불러오기", type="primary"):
    
    # 1. API 로그인 시도
    kis = KIS_API(APP_KEY, APP_SECRET)
    is_logged_in = kis.auth()
    
    if is_logged_in:
        st.toast("✅ 한투 API 로그인 성공! 실시간 시세를 가져옵니다.", icon="💳")
    else:
        st.toast("⚠️ API 키가 없거나 틀렸습니다. 네이버 데이터를 사용합니다.", icon="☁️")

    # 2. 테마 데이터 수집 (네이버)
    with st.spinner("테마 및 종목 발굴 중..."):
        theme_data = get_naver_themes()
    
    # 3. 화면 출력
    for theme in theme_data:
        # 테마 박스 시작
        st.markdown(f"""
        <div class="theme-box">
            <div class="theme-header">
                📦 [{theme['theme']}] 섹터
            </div>
        """, unsafe_allow_html=True)
        
        # 종목별 카드 렌더링
        for idx, s in enumerate(theme['stocks']):
            
            # 데이터 채우기 (한투 API 우선, 실패시 네이버 크롤링 값 등 사용)
            price_data = None
            if is_logged_in:
                # 📡 한투 API로 실시간 가격 조회
                price_data = kis.get_price(s['code'])
                time.sleep(0.1) # 초당 조회 제한 방지
            
            # API 데이터가 있으면 쓰고, 없으면 기본값
            if price_data:
                current_price = f"{price_data['price']:,}원"
                rate = price_data['rate']
                vol = f"{price_data['vol']:,}"
            else:
                current_price = "API 연결 필요"
                rate = 0.0
                vol = "-"

            # 등락률 스타일
            rate_color = "rate-up" if rate > 0 else ("rate-down" if rate < 0 else "")
            rate_icon = "🔥" if rate > 10 else ("🔺" if rate > 0 else "🔹")
            rank_icon = ["🥇대장", "🥈2등", "🥉3등"][idx] if idx < 3 else ""
            
            # 흐름 분석 (단순 로직 예시)
            flow = "매수 우위 ↗️" if rate > 0 else "매도 우위 ↘️"
            
            # HTML 출력
            st.markdown(f"""
            <div class="stock-card">
                <div class="card-top-row">
                    <div>
                        <span class="badge badge-rank">{rank_icon}</span>
                        <span class="stock-name">{s['name']}</span>
                        <span style="font-size:0.8rem; color:#888;">({s['code']})</span>
                    </div>
                    <div>
                        <span class="{rate_color}">{rate_icon} {rate}%</span>
                        <span style="font-size:0.9rem; font-weight:bold; margin-left:10px;">{current_price}</span>
                    </div>
                </div>
                
                <div class="sub-info">
                    <span class="info-label">🤖 흐름:</span> {flow} (거래량: {vol}) <br>
                    <span class="info-label">📰 뉴스:</span> <a href="#" class="news-link">{s['news']}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True) # 테마 박스 닫기
