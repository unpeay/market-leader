import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Mobile",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #121212; }
    
    /* 테마 헤더 */
    .theme-header {
        font-size: 1.3rem;
        font-weight: 900;
        color: #FFD700;
        margin-top: 25px;
        margin-bottom: 10px;
        padding-bottom: 5px;
        border-bottom: 1px solid #333;
    }
    
    /* 종목 카드 */
    .stock-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        margin-bottom: 10px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* 종목명 */
    .stock-title { font-size: 1.1rem; font-weight: bold; color: white; }
    
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
    
    /* 로딩 바 스타일 */
    .stProgress > div > div > div > div { background-color: #FF4B4B; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. [핵심] 완전 자동화 분석 엔진
# ==========================================

# 1단계: 네이버 '테마 상위 랭킹'과 '구성 종목'을 실시간으로 긁어옴 (Dynamic Learning)
@st.cache_data(ttl=1800) # 30분마다 갱신
def build_dynamic_theme_map():
    stock_to_theme = {} # { '삼성전자': '반도체', '에코프로': '2차전지' ... }
    
    try:
        # 네이버 테마별 시세 1페이지 (상위 40개 테마)
        url = "https://finance.naver.com/sise/theme.naver"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 테마 목록 가져오기
        themes = soup.select('.col_type1 a')
        
        # 상위 15개 핫한 테마만 상세 조회 (속도 최적화)
        progress_text = st.empty()
        bar = st.progress(0)
        
        target_themes = themes[:15] 
        
        for idx, t in enumerate(target_themes):
            theme_name = t.text.strip()
            theme_link = "https://finance.naver.com" + t['href']
            
            # 진행상황 표시
            progress_text.caption(f"📡 테마 학습 중... [{theme_name}] 분석")
            bar.progress((idx + 1) / len(target_themes))
            
            # 해당 테마 페이지 접속 -> 종목 긁어오기
            try:
                sub_res = requests.get(theme_link, headers=headers, timeout=3)
                sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
                
                # 그 테마에 속한 종목들 (상위 5개 대장주만)
                stocks = sub_soup.select('.name_area .name a')
                for s in stocks[:5]: 
                    s_name = s.text.strip()
                    # 이미 등록된 종목이면 (다른 테마에도 속할 경우) 더 상위 테마 우선
                    if s_name not in stock_to_theme:
                        stock_to_theme[s_name] = theme_name
            except: continue
            
        progress_text.empty()
        bar.empty()
        
    except Exception as e:
        print(e)
        
    return stock_to_theme

# 2단계: 뉴스 크롤링 & 위에서 만든 맵으로 자동 분류
def get_news_and_classify(stock_map):
    grouped_data = [] # 결과 담을 리스트
    
    try:
        # 많이 본 뉴스
        url = "https://finance.naver.com/news/news_list.naver?mode=RANK&date=" + datetime.now().strftime("%Y%m%d")
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = soup.select('.newsList li')
        
        for item in news_list[:40]: # 뉴스 40개 분석
            title_tag = item.select_one('a')
            if not title_tag: continue
            
            title = title_tag.text.strip()
            link = "https://finance.naver.com" + title_tag['href']
            press = item.select_one('.press').text.strip() if item.select_one('.press') else "뉴스"
            
            # 🕵️‍♂️ 자동 분류 로직
            found_stock = None
            found_theme = "기타 이슈"
            
            # 우리가 학습한 종목 리스트(stock_map)에 있는 종목이 뉴스 제목에 있는지 확인
            for stock_name, theme_name in stock_map.items():
                if stock_name in title:
                    found_stock = stock_name
                    found_theme = theme_name
                    break # 찾으면 중단
            
            # 종목을 못 찾았지만 뉴스 가치가 있다면? -> '기타'로 분류하거나 제외
            if found_stock:
                grouped_data.append({
                    '테마': found_theme,
                    '종목': found_stock,
                    '제목': title,
                    '링크': link,
                    '언론사': press
                })
            else:
                # 종목명은 없지만 테마명(예: 반도체, 2차전지)이 제목에 직접 있는 경우 처리
                for stock_name, theme_name in stock_map.items():
                    if theme_name in title: # 뉴스 제목에 '반도체'가 있으면
                        grouped_data.append({
                            '테마': theme_name,
                            '종목': "섹터 종합",
                            '제목': title,
                            '링크': link,
                            '언론사': press
                        })
                        break
                        
    except: pass
    
    return pd.DataFrame(grouped_data)

# [평일용 API 함수들] (기존 유지)
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
# 🖥️ 3. 메인 화면
# ==========================================
st.title("📈 마켓 리더 AI")

with st.sidebar:
    st.header("⚙️ 설정")
    mode = st.radio("모드 선택", ["평일(API)", "주말(뉴스)"], index=1)
    
    if mode == "평일(API)":
        try:
            APP_KEY = st.secrets["APP_KEY"]
            APP_SECRET = st.secrets["APP_SECRET"]
            st.success("키 로드 완료")
        except:
            APP_KEY = st.text_input("Key", type="password")
            APP_SECRET = st.text_input("Secret", type="password")
        URL_BASE = "https://openapi.koreainvestment.com:9443"

# ----------------------------------------
# A. 주말 모드 (AI 자동 분류)
# ----------------------------------------
if mode == "주말(뉴스)":
    st.info("📰 네이버 금융을 실시간으로 학습하여 뉴스를 자동 분류합니다.")
    
    if st.button("🚀 AI 주말 이슈 분석 시작", use_container_width=True, type="primary"):
        
        # 1. 동적 테마맵 구축
        with st.spinner("1단계: 현재 시장 주도 테마와 대장주를 학습 중입니다..."):
            stock_map = build_dynamic_theme_map()
            
        # 2. 뉴스 분류
        with st.spinner("2단계: 뉴스를 읽고 학습된 정보로 분류 중입니다..."):
            df = get_news_and_classify(stock_map)
            
        if df.empty:
            st.warning("분석된 관련 뉴스가 없습니다. (뉴스 제목에 학습된 종목명이 없을 수 있음)")
        else:
            st.success(f"✅ 분석 완료! 총 {len(df)}건의 핵심 이슈를 찾았습니다.")
            
            # 3. 테마별 -> 종목별 그룹핑 출력
            theme_groups = df.groupby('테마')
            
            # 테마 정렬 (뉴스 많은 순서대로)
            sorted_themes = sorted(theme_groups.groups.keys(), key=lambda x: len(theme_groups.get_group(x)), reverse=True)
            
            for theme in sorted_themes:
                t_group = theme_groups.get_group(theme)
                
                # 📦 테마 헤더
                st.markdown(f"<div class='theme-header'>📦 {theme} ({len(t_group)}건)</div>", unsafe_allow_html=True)
                
                # 종목별 그룹핑
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
                                {row['제목']}
                                <div class="news-meta">{row['언론사']}</div>
                            </a>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------
# B. 평일 모드 (기존 유지)
# ----------------------------------------
else:
    if st.button("🚀 실시간 분석 시작", use_container_width=True, type="primary"):
        if not APP_KEY:
            st.error("설정에서 키를 입력하세요.")
        else:
            status = st.empty()
            progress = st.progress(0)
            
            try:
                # 로그인
                body = {"grant_type":"client_credentials", "appkey":APP_KEY, "appsecret":APP_SECRET}
                res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, json=body)
                token = res.json()['access_token']
                
                # 데이터 요청
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
                
                # 출력
                df = pd.DataFrame(analyzed_data)
                grouped = df.groupby('테마')
                theme_order = grouped['점수'].mean().sort_values(ascending=False).index
                
                for theme in theme_order:
                    group_df = grouped.get_group(theme)
                    if group_df['점수'].max() < 40: continue
                    
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
                                <div><span class="stock-title">{row['종목']}</span> {badges} <span class="{price_cls}">{icon} {row['등락']}%</span></div>
                                <div style="margin-top:10px; font-size:0.9rem; color:#ccc;">
                                    <div>🤖 {row['흐름']}</div>
                                    <div>👽 외인(5일): {', '.join(row['외인'])}</div>
                                </div>
                                <a href="#" class="news-item">📰 {row['뉴스'][:30]}...</a>
                            </div>
                            """, unsafe_allow_html=True)
                            
            except Exception as e:
                st.error(f"오류: {e}")
