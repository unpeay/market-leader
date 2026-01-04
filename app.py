import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import json
import os

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인 (KT Corporate Style)
# ==========================================
st.set_page_config(
    page_title="Market Leader Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>
    .stApp { background-color: #f4f6f9; font-family: 'Pretendard', sans-serif; }
    
    .main-title {
        font-size: 1.8rem; font-weight: 800; color: #1A237E;
        margin-bottom: 0.5rem; padding-left: 10px;
        border-left: 5px solid #e74c3c; letter-spacing: -0.5px;
    }
    .sub-title { font-size: 0.95rem; color: #666; margin-bottom: 2rem; padding-left: 15px; }
    
    .theme-box {
        background-color: #ffffff; border-radius: 16px; padding: 25px;
        margin-bottom: 25px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        border: 1px solid #e0e0e0;
    }
    .theme-header {
        font-size: 1.4rem; font-weight: 800; color: #333;
        margin-bottom: 20px; display: flex; align-items: center; 
        border-bottom: 2px solid #333; padding-bottom:12px;
    }
    .theme-stat { font-size: 0.9rem; color: #e74c3c; margin-left: auto; font-weight: 700; }
    
    .stock-card {
        background-color: #f8f9fa; border: 1px solid #e9ecef;
        border-radius: 12px; padding: 18px; margin-bottom: 12px;
        transition: all 0.2s ease-in-out;
    }
    .stock-card:hover { 
        border-color: #1A237E; 
        background-color: #fff;
        transform: translateY(-3px); 
        box-shadow: 0 5px 15px rgba(26, 35, 126, 0.1);
    }
    
    .card-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .stock-name { font-size: 1.15rem; font-weight: 800; color:#222; }
    .rate-up { color: #d32f2f; font-weight:800; font-size: 1.1rem; }
    .rate-down { color: #1976d2; font-weight:800; font-size: 1.1rem; }
    
    .badge { padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; margin-right: 6px; vertical-align: middle; }
    .badge-rank { background:#333; color:white; }
    
    .expert-box {
        margin-top: 10px; padding: 10px; border-radius: 8px;
        background-color: #fff; border: 1px dashed #ced4da;
    }
    .expert-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: #495057; margin-bottom: 4px; }
    .expert-label { font-weight: 700; color: #1A237E; }
    .expert-val { font-family: monospace; font-weight: 600; }
    
    .news-section { margin-top: 8px; font-size: 0.85rem; color: #888; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
    .news-link { text-decoration: none; color: #666; font-weight: 500; }
    .news-link:hover { color: #e74c3c; text-decoration: underline; }
    
    .prob-bar-bg { width: 100%; height: 6px; background-color: #e9ecef; border-radius: 3px; margin-top: 5px; overflow: hidden; }
    .prob-bar-fill { height: 100%; background: linear-gradient(90deg, #ffc107, #ff5722); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 데이터 엔진
# ==========================================

class KIS_API:
    def __init__(self, app_key, app_secret):
        self.key = app_key
        self.secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.token = None
        self.token_file = "kis_token_save.json"

    def auth(self):
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                expire_dt = datetime.strptime(data['expired'], "%Y-%m-%d %H:%M:%S")
                if datetime.now() < expire_dt:
                    self.token = data['token']
                    return True
            except: pass

        try:
            headers = {"content-type": "application/json"}
            body = {"grant_type": "client_credentials", "appkey": self.key, "appsecret": self.secret}
            res = requests.post(f"{self.base_url}/oauth2/tokenP", headers=headers, json=body)
            if res.status_code == 200:
                res_json = res.json()
                self.token = res_json["access_token"]
                expires_in = int(res_json.get("expires_in", 86400))
                expire_dt = datetime.now() + timedelta(seconds=expires_in - 600)
                with open(self.token_file, 'w') as f:
                    json.dump({"token": self.token, "expired": expire_dt.strftime("%Y-%m-%d %H:%M:%S")}, f)
                return True
            return False
        except: return False

    def get_price_detail(self, code):
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
                d = res.json()['output']
                return {
                    'price': int(d['stck_prpr']), 'rate': float(d['prdy_ctrt']),
                    'high': int(d['stck_hgpr']), 'low': int(d['stck_lwpr']),
                    'vol': int(d['acml_vol'])
                }
            elif res.status_code in [401, 403]:
                if os.path.exists(self.token_file): os.remove(self.token_file)
        except: pass
        return None

def get_naver_detail_backup(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        no_today = soup.select_one('.no_today .blind')
        price = int(no_today.text.replace(',', '')) if no_today else 0
        return {'price': price, 'rate': 0.0, 'high': price, 'low': price, 'vol': 0}
    except:
        return {'price': 0, 'rate': 0.0, 'high': 0, 'low': 0, 'vol': 0}

def get_smart_money_flow(code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('.type2 tr')
        
        f_trend = []
        i_trend = []
        cnt = 0
        for row in rows:
            cols = row.select('td')
            if len(cols) > 6 and cols[0].text.strip() != "":
                i_val = int(cols[5].text.replace(',', '')) // 1000
                i_trend.append(i_val)
                f_val = int(cols[6].text.replace(',', '')) // 1000
                f_trend.append(f_val)
                cnt += 1
                if cnt >= 3: break
        
        prog_msg = "관망세"
        if f_trend and f_trend[0] > 0:
            if f_trend[0] > 50: prog_msg = "🔥프로그램 대량 매수"
            else: prog_msg = "↗️매수세 유입 중"
        elif f_trend and f_trend[0] < 0:
            if f_trend[0] < -50: prog_msg = "☔프로그램 매도(주의)"
            else: prog_msg = "↘️매도 우위"
            
        return f_trend, i_trend, prog_msg
    except:
        return [], [], "분석불가"

def calc_power_close(price, high, low):
    if high == low: return 50
    position = (price - low) / (high - low) * 100
    return int(position)

def get_full_analysis(code, name, kis_instance):
    data = kis_instance.get_price_detail(code)
    source = "API"
    if not data:
        data = get_naver_detail_backup(code)
        source = "Web"
    
    f_trend, i_trend, prog_msg = get_smart_money_flow(code)
    power_score = calc_power_close(data['price'], data['high'], data['low'])
    
    news = "관련 뉴스 없음"
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={code}"
        r = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=1)
        s = BeautifulSoup(r.text, 'html.parser')
        t = s.select_one('.type5 tbody tr .title a')
        if t: news = t.text.strip()
    except: pass
    
    return {
        'price': data['price'], 'rate': data['rate'], 'vol': data['vol'],
        'source': source, 'f_trend': f_trend, 'i_trend': i_trend,
        'prog_msg': prog_msg, 'power_score': power_score, 'news': news
    }

@st.cache_data(ttl=600)
def get_themes():
    themes = []
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent':'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        for t in soup.select('.col_type1 a')[:5]:
            link = "https://finance.naver.com" + t['href']
            sub_res = requests.get(link, headers={'User-Agent':'Mozilla/5.0'})
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            stocks = []
            for row in sub_soup.select('.type_5 tbody tr'):
                cols = row.select('td')
                if len(cols) > 1:
                    stocks.append({'name': cols[0].text.strip(), 'code': cols[0].select_one('a')['href'].split('=')[1]})
                    if len(stocks)>=3: break
            themes.append({'theme': t.text.strip(), 'stocks': stocks})
    except: pass
    return themes

# ==========================================
# 🖥️ 4. 메인 화면 출력
# ==========================================

with st.sidebar:
    st.header("🔑 전문가 설정")
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        st.success("✅ API Key Ready")
    except:
        APP_KEY = st.text_input("APP Key", type="password")
        APP_SECRET = st.text_input("APP Secret", type="password")

st.markdown('<div class="main-title">Market Leader Pro <span style="font-size:1rem; color:#888;">Expert Edition</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">고수들의 관점: <b>프로그램 수급</b>과 <b>종가 마감 강도</b>를 실시간으로 분석합니다.</div>', unsafe_allow_html=True)

if st.button("🚀 실시간 딥 다이브(Deep Dive) 분석 시작", type="primary"):
    
    kis = KIS_API(APP_KEY, APP_SECRET)
    if kis.auth(): 
        if os.path.exists("kis_token_save.json"):
            st.toast("저장된 토큰 사용 ⚡", icon="💾")
        else:
            st.toast("새로운 토큰 발급 완료!", icon="🔑")
    else: 
        st.toast("API 연결 실패. 웹 데이터로 대체합니다.", icon="⚠️")
    
    with st.spinner("시장 주도 테마 및 수급 분석 중..."):
        themes = get_themes()
        
    if not themes: st.error("데이터 수신 실패")
    
    for theme in themes:
        # [수정 1] 종목 없는 빈 테마 박스 삭제
        if not theme['stocks']: continue

        # [수정 2] HTML 줄바꿈(.replace('\n', '')) 제거하여 깨짐 방지
        html_header = f"""
        <div class="theme-box">
            <div class="theme-header">
                📦 [{theme['theme']}] 섹터
                <span class="theme-stat">🔥 주도주 Top 3</span>
            </div>
        """.replace('\n', '')
        
        st.markdown(html_header, unsafe_allow_html=True)
        
        for idx, s in enumerate(theme['stocks']):
            d = get_full_analysis(s['code'], s['name'], kis)
            
            p_fmt = f"{d['price']:,}원"
            rate_cls = "rate-up" if d['rate'] > 0 else "rate-down"
            rate_icon = "🔥" if d['rate'] >= 10 else ("🔺" if d['rate'] > 0 else "🔹")
            rank_icon = ["🥇대장", "🥈2등", "🥉3등"][idx]
            
            power_bar_width = d['power_score']
            power_ment = "일반 마감"
            if power_bar_width > 80: power_ment = "👑 최고가 마감 임박"
            elif power_bar_width > 50: power_ment = "양호한 흐름"
            elif power_bar_width < 20: power_ment = "윗꼬리 발생 (주의)"
            
            f_str = str(d['f_trend']).replace('[','').replace(']','') if d['f_trend'] else "-"
            i_str = str(d['i_trend']).replace('[','').replace(']','') if d['i_trend'] else "-"
            
            # [수정 2] HTML 줄바꿈 제거 적용
            card_html = f"""
            <div class="stock-card">
                <div class="card-top-row">
                    <div>
                        <span class="badge badge-rank">{rank_icon}</span>
                        <span class="stock-name">{s['name']}</span>
                        <span style="font-size:0.7rem; color:#bbb; margin-left:4px;">{d['source']}</span>
                    </div>
                    <div>
                        <span class="{rate_cls}">{rate_icon} {d['rate']}%</span>
                        <span style="font-size:0.95rem; font-weight:700; color:#333; margin-left:8px;">{p_fmt}</span>
                    </div>
                </div>
                
                <div class="expert-box">
                    <div class="expert-row">
                        <span class="expert-label">🤖 프로그램 추정</span>
                        <span class="expert-val" style="color:#1A237E;">{d['prog_msg']}</span>
                    </div>
                    <div class="expert-row">
                        <span class="expert-label">👽 외인(3일)</span>
                        <span class="expert-val">{f_str}</span>
                    </div>
                    <div class="expert-row">
                        <span class="expert-label">🏦 기관(3일)</span>
                        <span class="expert-val">{i_str}</span>
                    </div>
                    
                    <div style="margin-top:8px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#666; font-weight:bold;">
                            <span>⚡ 마감 강도(Power Close)</span>
                            <span>{power_ment} ({d['power_score']}%)</span>
                        </div>
                        <div class="prob-bar-bg">
                            <div class="prob-bar-fill" style="width: {power_bar_width}%;"></div>
                        </div>
                    </div>
                </div>

                <div class="news-section">
                    📰 <a href="#" class="news-link">{d['news']}</a>
                </div>
            </div>
            """.replace('\n', '') # 핵심: 여기서 줄바꿈을 다 없앰
            
            st.markdown(card_html, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
