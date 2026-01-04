import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime

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
    
    .main-title {
        font-size: 1.8rem; font-weight: 800; color: #222;
        margin-bottom: 1rem; padding-left: 10px;
        border-left: 5px solid #e74c3c;
    }
    
    .theme-box {
        background-color: #ffffff; border-radius: 16px; padding: 20px;
        margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .theme-header {
        font-size: 1.3rem; font-weight: 700; color: #333;
        margin-bottom: 15px; display: flex; align-items: center; border-bottom: 2px solid #f0f0f0; padding-bottom:10px;
    }
    
    .stock-card {
        background-color: #fdfdfd; border: 1px solid #e0e0e0;
        border-radius: 12px; padding: 15px; margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .stock-card:hover { border-color: #e74c3c; transform: translateY(-2px); }
    
    .card-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .stock-name { font-size: 1.1rem; font-weight: 700; color:#222; }
    .rate-up { color: #e74c3c; font-weight:700; }
    .rate-down { color: #3498db; font-weight:700; }
    
    .badge { padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; margin-right: 5px; }
    .badge-rank { background:#333; color:white; }
    
    .sub-info { font-size: 0.9rem; color: #555; line-height: 1.6; margin-top: 8px; border-top: 1px dashed #eee; padding-top:8px;}
    .info-label { font-weight: 600; color: #333; }
    .news-link { text-decoration: none; color: #444; }
    .news-link:hover { color: #e74c3c; text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 엔진 (하이브리드)
# ==========================================

class KIS_API:
    def __init__(self, app_key, app_secret):
        self.key = app_key
        self.secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.token = None

    def auth(self):
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
                    'price': int(data['stck_prpr']),
                    'rate': float(data['prdy_ctrt']),
                    'vol': int(data['acml_vol'])
                }
        except: pass
        return None

def get_stock_data_hybrid(code, name, kis_instance):
    data = kis_instance.get_price(code)
    source = "API"
    
    if not data:
        source = "Web"
        try:
            url = f"https://finance.naver.com/item/sise.naver?code={code}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')
            
            price = int(soup.select_one('.tah.p11').text.strip().replace(',', ''))
            
            rate_txt = soup.select_one('.tah.p11.red01')
            if not rate_txt: rate_txt = soup.select_one('.tah.p11.nv01')
            
            rate = 0.0
            if rate_txt:
                rate_raw = rate_txt.text.strip().replace('%', '')
                rate = float(rate_raw)
                if 'nv01' in str(rate_txt): rate = -rate
            
            vol = 0
            try:
                vol_txt = soup.select('.tah.p11')[3].text.strip().replace(',', '')
                vol = int(vol_txt)
            except: pass

            data = {'price': price, 'rate': rate, 'vol': vol}
        except:
            data = {'price': 0, 'rate': 0.0, 'vol': 0}

    news_title = "관련된 최근 뉴스가 없습니다."
    try:
        n_url = f"https://finance.naver.com/item/news_news.naver?code={code}"
        n_res = requests.get(n_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=1)
        n_soup = BeautifulSoup(n_res.text, 'html.parser')
        n_tag = n_soup.select_one('.type5 tbody tr .title a')
        if n_tag: news_title = n_tag.text.strip()
    except: pass
    
    return data, news_title, source

@st.cache_data(ttl=600)
def get_themes_and_stocks():
    themes_list = []
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for t_link in soup.select('.col_type1 a')[:5]:
            t_name = t_link.text.strip()
            link = "https://finance.naver.com" + t_link['href']
            
            sub_res = requests.get(link, headers={'User-Agent': 'Mozilla/5.0'})
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            
            stocks = []
            for row in sub_soup.select('.type_5 tbody tr'):
                try:
                    cols = row.select('td')
                    if len(cols) < 2: continue
                    name = cols[0].text.strip()
                    code = cols[0].select_one('a')['href'].split('code=')[1]
                    stocks.append({'name': name, 'code': code})
                    if len(stocks) >= 3: break
                except: continue
            themes_list.append({'theme': t_name, 'stocks': stocks})
    except: pass
    return themes_list

# ==========================================
# 🖥️ 4. 메인 화면
# ==========================================

with st.sidebar:
    st.header("🔑 API 설정")
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        st.success("✅ 키 자동 로드 완료")
    except:
        APP_KEY = st.text_input("APP Key", type="password")
        APP_SECRET = st.text_input("APP Secret", type="password")
        st.info("키가 없으면 네이버 크롤링 모드로 작동합니다.")

st.markdown('<div class="main-title">📈 오늘의 종가베팅 (Final Ver.)</div>', unsafe_allow_html=True)

if st.button("🚀 데이터 분석 시작", type="primary"):
    
    kis = KIS_API(APP_KEY, APP_SECRET)
    is_api_ok = kis.auth()
    
    if is_api_ok:
        st.toast("한투 API 연결 성공!", icon="⚡")
    else:
        st.toast("네이버 크롤링 모드로 전환합니다.", icon="🐢")
    
    with st.spinner("테마 분석 중..."):
        all_themes = get_themes_and_stocks()
        
    if not all_themes:
        st.error("데이터 수집 실패. 잠시 후 다시 시도해주세요.")
    
    for theme in all_themes:
        st.markdown(f"""<div class="theme-box"><div class="theme-header">📦 [{theme['theme']}] 섹터</div>""", unsafe_allow_html=True)
        
        for idx, s in enumerate(theme['stocks']):
            data, news, source = get_stock_data_hybrid(s['code'], s['name'], kis)
            
            price = f"{data['price']:,}원"
            rate = data['rate']
            vol = f"{data['vol']:,}"
            
            rate_cls = "rate-up" if rate > 0 else ("rate-down" if rate < 0 else "")
            rate_icon = "🔥" if rate >= 10 else ("🔺" if rate > 0 else "🔹")
            rank_icon = ["🥇대장", "🥈2등", "🥉3등"][idx] if idx < 3 else ""
            
            if rate > 5: ai_flow = "강력 매수 구간 🔥"
            elif rate > 0: ai_flow = "매수 우위 ↗️"
            elif rate > -2: ai_flow = "관망/보합 ➡️"
            else: ai_flow = "매도 우위 (주의) ↘️"

            src_mark = "⚡" if source == "API" else "🐢"

            # 🚨 [중요] HTML 코드를 변수에 담을 때, 들여쓰기를 완전히 없애야 합니다.
            card_html = f"""
<div class="stock-card">
    <div class="card-top-row">
        <div>
            <span class="badge badge-rank">{rank_icon}</span>
            <span class="stock-name">{s['name']}</span>
            <span style="font-size:0.7rem; color:#aaa; margin-left:5px;">{src_mark}</span>
        </div>
        <div>
            <span class="{rate_cls}">{rate_icon} {rate}%</span>
            <span style="font-size:0.9rem; font-weight:bold; margin-left:10px;">{price}</span>
        </div>
    </div>
    <div class="sub-info">
        <span class="info-label">🤖 흐름:</span> {ai_flow} (거래량: {vol}) <br>
        <span class="info-label">📰 뉴스:</span> <a href="#" class="news-link">{news}</a>
    </div>
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
