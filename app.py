import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인 (CSS)
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 디자인 시스템 (토스증권/영웅문 스타일)
st.markdown("""
<style>
    /* 전체 다크 모드 배경 */
    .stApp { background-color: #0E1117; }
    
    /* [평일] 종목 카드 */
    .stock-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* [주말] 뉴스 카드 */
    .news-card {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #FF4B4B;
        margin-bottom: 12px;
        transition: transform 0.2s;
    }
    .news-card:hover { transform: scale(1.01); }
    
    /* 텍스트 스타일 */
    .price-up { color: #FF4B4B; font-weight: bold; font-size: 1.2rem; }
    .price-down { color: #4B91FF; font-weight: bold; font-size: 1.2rem; }
    .news-title { font-size: 1.1rem; font-weight: bold; color: #eee; text-decoration: none; display: block; margin-bottom: 5px;}
    .news-meta { font-size: 0.8rem; color: #888; }
    
    /* 뱃지 */
    .badge-s { background-color: #FFD700; color: black; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; margin-right: 5px; }
    .badge-new { background-color: #FF4B4B; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8rem; margin-right: 5px; }
    .badge-theme { background-color: #333; color: #4B91FF; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-right: 5px; }
    
    /* 상세 정보 텍스트 */
    .flow-txt { font-size: 0.95rem; font-weight: bold; color: #eee; margin-bottom: 3px; }
    .supply-txt { font-size: 0.85rem; color: #ccc; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 분석 엔진 (함수 모음)
# ==========================================

# ------------------------------------------------
# [주말용] 네이버 테마 100개 긁어오기 (동적 사전)
# ------------------------------------------------
@st.cache_data(ttl=600)
def get_all_naver_themes():
    theme_list = []
    try:
        # 1페이지부터 4페이지까지 스캔 (약 80~100개 테마)
        for page in range(1, 5): 
            url = f"https://finance.naver.com/sise/theme.naver?&page={page}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')
            themes = soup.select('.col_type1 a')
            for t in themes:
                # "2차전지(장비)" -> "2차전지"로 핵심만 추출
                clean_name = t.text.strip().split('(')[0]
                theme_list.append(clean_name)
    except: 
        return ['반도체', '2차전지', 'AI', '로봇', '바이오', '방산', '비트코인']
    
    # 중복 제거 및 긴 단어 우선 정렬 (매칭 정확도 위해)
    return sorted(list(set(theme_list)), key=len, reverse=True)

# ------------------------------------------------
# [주말용] 뉴스 크롤링 & 테마 자동 매칭
# ------------------------------------------------
@st.cache_data(ttl=600)
def get_weekend_issues_auto():
    issues = []
    # 1. 최신 테마 사전 구축
    dynamic_keywords = get_all_naver_themes()
    
    try:
        # 2. 많이 본 뉴스 긁어오기
        url = "https://finance.naver.com/news/news_list.naver?mode=RANK&date=" + datetime.now().strftime("%Y%m%d")
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_list = soup.select('.newsList li')
        
        for item in news_list[:25]: # 상위 25개
            title_tag = item.select_one('a')
            if not title_tag: continue
            
            title = title_tag.text.strip()
            link = "https://finance.naver.com" + title_tag['href']
            provider = item.select_one('.press').text.strip() if item.select_one('.press') else "뉴스"
            
            # 3. 테마 자동 매칭
            detected_theme = "기타/개별이슈"
            for key in dynamic_keywords:
                if key in title:
                    detected_theme = key
                    break # 매칭되면 중단
            
            # 4. 관련주 (유명 종목만 단순 체크)
            famous_stocks = ['삼성전자', 'SK하이닉스', '에코프로', '한미반도체', '현대차', 'LG에너지솔루션', 'POSCO홀딩스', '카카오', '네이버', '두산로보틱스', '신성델타테크', '제주반도체', 'HLB']
            related_stocks = [s for s in famous_stocks if s in title]
            
            issues.append({'제목': title, '링크': link, '언론사': provider, '테마': detected_theme, '관련주': related_stocks})
    except: pass
    return issues, dynamic_keywords

# ------------------------------------------------
# [평일용] API 관련 함수들 (기존 기능)
# ------------------------------------------------
@st.cache_data(ttl=600)
def get_live_hot_themes_weekday():
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        return [t.text.strip() for t in soup.select('.col_type1 a')][:35]
    except: return []

def get_theme_auto(code, hot_themes):
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
            elif gap > -5: return f"🚀신고가임박"
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
    f_list, i_list = [], []
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
                i_val = int(cols[5].text.replace(',', '')) // 1000
                f_list.append(f"+{f_val}" if f_val > 0 else f"{f_val}")
                i_list.append(f"+{i_val}" if i_val > 0 else f"{i_val}")
                cnt += 1
    except: pass
    return f_list, i_list

# ==========================================
# 🖥️ 3. 메인 화면 및 실행 로직
# ==========================================
st.title("📈 마켓 리더 Pro")

with st.sidebar:
    st.header("⚙️ 모드 설정")
    
    # 🔥 평일/주말 모드 선택
    mode_selection = st.radio("분석 모드", ["평일 (실전 투자)", "주말 (이슈 분석)"], index=1)
    st.markdown("---")
    
    APP_KEY, APP_SECRET = "", ""
    URL_BASE = "https://openapi.koreainvestment.com:9443"
    
    if mode_selection == "평일 (실전 투자)":
        st.caption("✅ 실전투자 API 키가 필요합니다.")
        try:
            APP_KEY = st.secrets["APP_KEY"]
            APP_SECRET = st.secrets["APP_SECRET"]
            st.success("인증키 로드 완료")
        except:
            st.warning("키 설정 필요 (Secrets 미등록)")
            APP_KEY = st.text_input("APP Key", type="password")
            APP_SECRET = st.text_input("APP Secret", type="password")
        
        run_btn = st.button("🚀 실시간 데이터 분석 시작", type="primary", use_container_width=True)
        st.caption("※ 장 운영시간 (09:00~15:30)에만 정상 작동")
        
    else:
        st.caption("☕ API 키 없이 뉴스 트렌드만 분석합니다.")
        run_btn = st.button("📰 주말 핫 이슈 분석", type="primary", use_container_width=True)

# ----------------------------------------
# 🚀 실행
# ----------------------------------------
if run_btn:
    
    # 🅰️ 주말 모드 실행 (자동 테마)
    if mode_selection == "주말 (이슈 분석)":
        st.subheader("📰 주말 핫 이슈 & 자동 테마 분류")
        
        with st.spinner("네이버 테마 리스트와 뉴스를 대조 중입니다..."):
            issues, keywords = get_weekend_issues_auto()
            
            if not issues:
                st.error("뉴스를 가져오지 못했습니다.")
            else:
                st.info(f"💡 현재 네이버에 등록된 {len(keywords)}개의 테마 키워드로 자동 분류했습니다.")
                
                for row in issues:
                    # 테마 뱃지 색상 (매칭되면 강조, 안되면 회색)
                    if row['테마'] != "기타/개별이슈":
                        theme_badge = f"<span class='badge-theme'>#{row['테마']}</span>"
                    else:
                        theme_badge = "<span style='color:#666; font-size:0.8rem; margin-right:5px;'>#개별이슈</span>"
                    
                    st.markdown(f"""
                    <div class="news-card">
                        <div style="margin-bottom:5px;">
                            {theme_badge}
                            <span class="news-meta">{row['언론사']}</span>
                        </div>
                        <a href="{row['링크']}" target="_blank" class="news-title">{row['제목']}</a>
                    </div>
                    """, unsafe_allow_html=True)

    # 🅱️ 평일 모드 실행 (기존 V13 기능)
    else:
        if not APP_KEY or not APP_SECRET:
            st.error("⚠️ API 키가 없습니다. 사이드바 설정을 확인하세요.")
        else:
            status_text = st.empty()
            status_text.info("📡 장중 데이터 분석 중... (API 연결)")
            progress_bar = st.progress(0)
            
            try:
                # 1. 토큰 발급
                body = {"grant_type":"client_credentials", "appkey":APP_KEY, "appsecret":APP_SECRET}
                res_token = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, json=body)
                
                if res_token.status_code != 200:
                    st.error("❌ 로그인 실패 (서버 점검 중이거나 키 오류)")
                    st.stop()
                    
                token = res_token.json()['access_token']
                
                # 2. 데이터 요청
                headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
                params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
                
                res_data = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
                raw_data = res_data.json()['output'][:25]
                
                analyzed_data = []
                hot_themes = get_live_hot_themes_weekday() # 평일용 테마 수집
                
                # 3. 분석 루프
                for i, item in enumerate(raw_data):
                    code = item['mksc_shrn_iscd']
                    name = item['hts_kor_isnm']
                    price = int(item['stck_prpr'])
                    open_p = int(item['stck_oprc'])
                    high_p = int(item['stck_hgpr'])
                    low_p = int(item['stck_lwpr'])
                    rate = float(item['prdy_ctrt'])
                    vol = int(item['acml_tr_pbmn']) // 100000000
                    total_vol = int(item['acml_vol'])
                    avg_price = (int(item['acml_tr_pbmn']) / total_vol) if total_vol > 0 else price
                    
                    theme, news = get_theme_auto(code, hot_themes)
                    ath_status = check_ath_status(price, token, code, APP_KEY, APP_SECRET, URL_BASE)
                    flow_txt, flow_score = analyze_program_flow(price, open_p, high_p, low_p, avg_price)
                    f_list, i_list = get_supply_detail_5days(code)
                    
                    score = 0
                    if "매수" in flow_txt: score += 30
                    if "신고가" in ath_status: score += 30
                    if vol >= 1000: score += 20
                    if price > open_p: score += 20
                    
                    analyzed_data.append({'테마': theme, '종목': name, '등락': rate, '점수': score, '현재가': price, '신고가': ath_status, '흐름': flow_txt, '흐름점수': flow_score, '외인5': f_list, '기관5': i_list, '뉴스': news})
                    progress_bar.progress((i + 1) / len(raw_data))
                
                status_text.empty()
                progress_bar.empty()
                
                # 4. 결과 출력
                df = pd.DataFrame(analyzed_data)
                grouped = df.groupby('테마')
                theme_order = grouped['점수'].mean().sort_values(ascending=False).index
                
                for theme_name in theme_order:
                    group_df = grouped.get_group(theme_name)
                    if group_df['점수'].max() < 40: continue
                    
                    st.markdown(f"#### 📦 {theme_name}")
                    for idx, row in group_df.head(3).iterrows():
                        price_class = "price-up" if row['등락'] > 0 else "price-down"
                        icon = "🔥" if row['등락'] > 10 else ("🔺" if row['등락'] > 0 else "🔹")
                        badges = ""
                        if row['점수'] >= 90: badges += "<span class='badge-s'>S급</span>"
                        if row['신고가']: badges += f"<span class='badge-new'>{row['신고가']}</span>"
                        
                        with st.container():
                            st.markdown(f"""
                            <div class="stock-card">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <div><span style="font-size:1.1rem; font-weight:bold; color:white;">{row['종목']}</span> {badges}</div>
                                    <div class="{price_class}">{icon} {row['등락']}% <span style="font-size:0.9rem; color:#aaa;">({row['현재가']:,}원)</span></div>
                                </div>
                                <hr style="margin: 10px 0; border-color: #444;">
                                <div style="display:flex; justify-content:space-between;">
                                    <div style="width:55%;">
                                        <div class="flow-txt">🤖 {row['흐름']}</div>
                                        <div class="supply-txt">👽외인: {', '.join(row['외인5'])}</div>
                                        <div class="supply-txt">🏦기관: {', '.join(row['기관5'])}</div>
                                    </div>
                                    <div style="width:40%; text-align:right;">
                                        <div style="color:#888; font-size:0.8rem;">뉴스</div>
                                        <div style="color:#ddd; font-size:0.85rem;">{row['뉴스'][:15]}...</div>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.progress(row['흐름점수'])

            except Exception as e:
                st.error(f"오류 발생: {e}")
