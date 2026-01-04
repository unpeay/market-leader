import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인 (Mobile First)
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Mobile",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎨 디자인 시스템 (다크모드 + 카드 UI + 테마 그룹핑)
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #121212; }
    
    /* 테마 헤더 (섹션 구분) */
    .theme-header {
        font-size: 1.3rem;
        font-weight: 900;
        color: #FFD700;
        margin-top: 25px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #333;
    }
    
    /* 카드 디자인 */
    .stock-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* 종목명 & 가격 */
    .stock-title { font-size: 1.15rem; font-weight: bold; color: white; }
    .price-up { color: #FF4B4B; font-weight: bold; float: right; font-size: 1.1rem; }
    .price-down { color: #4B91FF; font-weight: bold; float: right; font-size: 1.1rem; }
    
    /* 뉴스 링크 */
    .news-item {
        display: block;
        padding: 10px;
        margin-top: 8px;
        background-color: #252525;
        border-radius: 8px;
        color: #ccc;
        text-decoration: none;
        font-size: 0.9rem;
        border-left: 3px solid #444;
    }
    .news-item:hover { background-color: #333; color: white; border-left: 3px solid #FF4B4B; }
    .news-meta { font-size: 0.75rem; color: #777; margin-top: 4px; }
    
    /* 뱃지 */
    .badge-s { background-color: #FFD700; color: black; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight:bold; margin-left:5px;}
    .badge-new { background-color: #FF4B4B; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight:bold; margin-left:5px;}
    
    /* 상세 정보 텍스트 */
    .info-txt { font-size: 0.85rem; color: #aaa; margin-top: 5px; }
    .flow-txt { font-size: 0.9rem; font-weight: bold; color: #eee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 주말 모드 엔진 (하이브리드)
# ==========================================
@st.cache_data(ttl=600)
def build_theme_map_hybrid():
    # [안전장치] 수동 데이터 (크롤링 실패 시 작동)
    stock_to_theme = {
        '삼성전자': '반도체', 'SK하이닉스': '반도체', '한미반도체': '반도체/HBM',
        '에코프로': '2차전지', '에코프로비엠': '2차전지', 'LG에너지솔루션': '2차전지', 'POSCO홀딩스': '2차전지',
        '현대차': '자동차', '기아': '자동차',
        '신성델타테크': '초전도체', '서남': '초전도체', '덕성': '초전도체',
        '우리기술투자': '비트코인', '한화투자증권': '비트코인', '위지트': '비트코인',
        '한화에어로스페이스': '방산', 'LIG넥스원': '방산', '빅텍': '방산',
        '두산로보틱스': '로봇', '레인보우로보틱스': '로봇',
        'HLB': '바이오', '알테오젠': '바이오', '셀트리온': '바이오',
        'NAVER': '플랫폼', '카카오': '플랫폼',
        '제주반도체': '온디바이스AI', '가온칩스': '온디바이스AI'
    }
    
    # [자동 학습] 네이버 테마 랭킹 긁어오기
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = soup.select('.col_type1 a')
        
        for t in themes[:15]: # 상위 15개 테마 학습
            t_name = t.text.strip()
            t_link = "https://finance.naver.com" + t['href']
            
            sub_res = requests.get(t_link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            stocks = sub_soup.select('.name_area .name a')
            
            for s in stocks[:5]: # 각 테마 대장주 5개
                stock_to_theme[s.text.strip()] = t_name
    except: pass
    
    return stock_to_theme

def get_news_hybrid(stock_map):
    grouped_data = []
    try:
        url = "https://finance.naver.com/news/news_list.naver?mode=RANK&date=" + datetime.now().strftime("%Y%m%d")
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = soup.select('.newsList li')
        
        for item in news_list[:40]:
            title_tag = item.select_one('a')
            if not title_tag: continue
            
            title = title_tag.text.strip()
            link = "https://finance.naver.com" + title_tag['href']
            press = item.select_one('.press').text.strip() if item.select_one('.press') else "뉴스"
            
            # 매칭 로직
            found = False
            # 1. 종목명 매칭
            for s_name, t_name in stock_map.items():
                if s_name in title:
                    grouped_data.append({'테마': t_name, '종목': s_name, '제목': title, '링크': link, '언론사': press})
                    found = True
                    break
            # 2. 테마명 매칭
            if not found:
                unique_themes = list(set(stock_map.values()))
                for t_name in unique_themes:
                    if t_name in title:
                        grouped_data.append({'테마': t_name, '종목': '섹터 종합', '제목': title, '링크': link, '언론사': press})
                        break
    except: pass
    return pd.DataFrame(grouped_data)

# ==========================================
# 🧠 3. 평일 모드 엔진 (API + 분석)
# ==========================================
@st.cache_data(ttl=600)
def get_live_hot_themes_weekday():
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        return [t.text.strip() for t in soup.select('.col_type1 a')][:35]
    except: return []

def get_theme_auto_api(code, hot_themes):
    my_theme = "기타/개별"
    news_title = "-"
    try:
        res = requests.get(f"https://finance.naver.com/item/news_news.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        t_tag = soup.select_one('.type5 tbody tr .title a')
        if t_tag: news_title = t_tag.text.strip()
        for ht in hot_themes:
            if ht in news_title: 
                my_theme = ht
                break
        if my_theme == "기타/개별":
            res_m = requests.get(f"https://finance.naver.com/item/main.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            th_tag = BeautifulSoup(res_m.text, 'html.parser').select_one('.section.trade_compare > h4 > em')
            if th_tag: my_theme = th_tag.text.strip()
    except: pass
    return my_theme, news_title

def check_ath_status(price, token, code, APP_KEY, APP_SECRET, URL_BASE):
    try:
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"}
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/inquire-price", headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()['output']
            highest_price = int(data['hst_prc'])
            gap = (price - highest_price) / highest_price * 100
            if gap > -1: return "👑신고가"
            elif gap > -5: return f"🚀임박"
    except: pass
    return ""

def analyze_program_flow(price, open_p, high_p, low_p, avg_price):
    if high_p != low_p: wick_ratio = (high_p - price) / (high_p - low_p) * 100
    else: wick_ratio = 0
    if price > avg_price:
        if wick_ratio < 20: return "매수지속 ↗️", 100
        elif wick_ratio > 50: return "차익실현 ↘️", 50
        else: return "매수유입 ⬆️", 80
    else:
        if wick_ratio > 50: return "설거지주의 ☔", 20
        else: return "매도우위 ⬇️", 30

def get_supply_detail_5days(code):
    f_list = []
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select_one('.type2').select('tr')
        cnt = 0
        for row in rows:
            cols = row.select('td')
            if len(cols) > 3 and cols[0].text.strip() != "":
                if cnt >= 5: break
                f_val = int(cols[6].text.replace(',', '')) // 1000 
                f_str = f"+{f_val}" if f_val > 0 else f"{f_val}"
                f_list.append(f_str)
                cnt += 1
    except: pass
    return f_list

# ==========================================
# 🖥️ 4. 메인 화면 & 실행 로직
# ==========================================
st.title("📈 마켓 리더 Mobile")

with st.sidebar:
    st.header("⚙️ 설정")
    # 모드 선택 라디오 버튼
    mode = st.radio("모드 선택", ["평일(API)", "주말(뉴스)"], index=1)
    
    if mode == "평일(API)":
        try:
            APP_KEY = st.secrets["APP_KEY"]
            APP_SECRET = st.secrets["APP_SECRET"]
            st.success("✅ 키 로드 완료")
        except:
            APP_KEY = st.text_input("Key", type="password")
            APP_SECRET = st.text_input("Secret", type="password")
        URL_BASE = "https://openapi.koreainvestment.com:9443"

# ----------------------------------------
# A. 주말 모드 실행 (하이브리드)
# ----------------------------------------
if mode == "주말(뉴스)":
    st.info("📰 주말 이슈 스캔: 네이버 실시간 뉴스 + 자동 테마 분류")
    
    if st.button("🚀 주말 분석 시작", use_container_width=True, type="primary"):
        status = st.status("데이터 분석 중...", expanded=True)
        
        status.write("📡 1. 시장 주도 테마 학습 중...")
        stock_map = build_theme_map_hybrid()
        
        status.write("📰 2. 뉴스 크롤링 및 매칭 중...")
        df = get_news_hybrid(stock_map)
        
        status.update(label="분석 완료!", state="complete", expanded=False)
        
        if df.empty:
            st.warning("매칭된 뉴스가 없습니다. (시장 이슈가 없거나 크롤링 차단)")
        else:
            # 테마별 그룹핑 출력
            theme_groups = df.groupby('테마')
            sorted_themes = sorted(theme_groups.groups.keys(), key=lambda x: len(theme_groups.get_group(x)), reverse=True)
            
            for theme in sorted_themes:
                t_group = theme_groups.get_group(theme)
                
                # [테마 헤더]
                st.markdown(f"<div class='theme-header'>📦 {theme} ({len(t_group)})</div>", unsafe_allow_html=True)
                
                # [종목별 그룹핑]
                stock_groups = t_group.groupby('종목')
                
                for stock_name, s_group in stock_groups:
                    with st.container():
                        st.markdown(f"""
                        <div class="stock-card">
                            <div class="stock-title">{stock_name}</div>
                        """, unsafe_allow_html=True)
                        
                        for idx, row in s_group.iterrows():
                            st.markdown(f"""
                            <a href="{row['링크']}" target="_blank" class="news-item">
                                {row['제목']} <div class="news-meta">{row['언론사']}</div>
                            </a>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------
# B. 평일 모드 실행 (API Full Version)
# ----------------------------------------
else:
    if st.button("🚀 실시간 분석 시작", use_container_width=True, type="primary"):
        if not APP_KEY:
            st.error("⚠️ 설정에서 키를 입력하세요.")
        else:
            status = st.empty()
            status.info("📡 장중 데이터 수신 중...")
            progress = st.progress(0)
            
            try:
                # 1. 로그인
                body = {"grant_type":"client_credentials", "appkey":APP_KEY, "appsecret":APP_SECRET}
                res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, json=body)
                if res.status_code != 200:
                    st.error("로그인 실패 (서버 점검중 or 키 오류)")
                    st.stop()
                token = res.json()['access_token']
                
                # 2. 데이터 조회
                headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
                params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
                
                res_data = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
                raw_data = res_data.json()['output'][:25]
                
                analyzed_data = []
                hot_themes = get_live_hot_themes_weekday()
                
                for i, item in enumerate(raw_data):
                    code = item['mksc_shrn_iscd']
                    name = item['hts_kor_isnm']
                    price = int(item['stck_prpr'])
                    rate = float(item['prdy_ctrt'])
                    
                    # 지표 계산
                    open_p = int(item['stck_oprc'])
                    high_p = int(item['stck_hgpr'])
                    low_p = int(item['stck_lwpr'])
                    vol = int(item['acml_tr_pbmn']) // 100000000
                    total_vol = int(item['acml_vol'])
                    avg_price = (int(item['acml_tr_pbmn']) / total_vol) if total_vol > 0 else price
                    
                    theme, news = get_theme_auto_api(code, hot_themes)
                    ath = check_ath_status(price, token, code, APP_KEY, APP_SECRET, URL_BASE)
                    flow, f_score = analyze_program_flow(price, open_p, high_p, low_p, avg_price)
                    f_list = get_supply_detail_5days(code)
                    
                    score = 0
                    if "매수" in flow: score += 30
                    if "신고가" in ath: score += 30
                    if vol >= 1000: score += 20
                    if price > open_p: score += 20
                    
                    analyzed_data.append({'테마':theme, '종목':name, '등락':rate, '점수':score, '현재가':price, '신고가':ath, '흐름':flow, '외인':f_list, '뉴스':news})
                    progress.progress((i+1)/len(raw_data))
                
                status.empty()
                progress.empty()
                
                # 3. 화면 출력 (테마 그룹핑)
                df = pd.DataFrame(analyzed_data)
                grouped = df.groupby('테마')
                theme_order = grouped['점수'].mean().sort_values(ascending=False).index
                
                for theme in theme_order:
                    group_df = grouped.get_group(theme)
                    if group_df['점수'].max() < 40: continue # 점수 낮은 테마 생략
                    
                    st.markdown(f"<div class='theme-header'>📦 {theme}</div>", unsafe_allow_html=True)
                    
                    for idx, row in group_df.head(5).iterrows():
                        price_cls = "price-up" if row['등락'] > 0 else "price-down"
                        icon = "🔥" if row['등락'] > 10 else ("🔺" if row['등락'] > 0 else "🔹")
                        
                        badges = ""
                        if row['점수'] >= 90: badges += "<span class='badge-s'>S급</span>"
                        if row['신고가']: badges += f"<span class='badge-new'>{row['신고가']}</span>"
                        
                        with st.container():
                            st.markdown(f"""
                            <div class="stock-card">
                                <div>
                                    <span class="stock-title">{row['종목']}</span> {badges} 
                                    <span class="{price_cls}">{icon} {row['등락']}%</span>
                                </div>
                                <div style="margin-top:5px; font-size:0.9rem; color:#ddd;">현재가: {row['현재가']:,}원</div>
                                <hr style="border-color:#333; margin:10px 0;">
                                <div class="info-txt">
                                    <div class="flow-txt">🤖 {row['흐름']}</div>
                                    <div style="margin-top:4px;">👽 외인(5일): {', '.join(row['외인'])}</div>
                                </div>
                                <a href="#" class="news-item">📰 {row['뉴스'][:30]}...</a>
                            </div>
                            """, unsafe_allow_html=True)
                            
            except Exception as e:
                st.error(f"오류: {e}")
