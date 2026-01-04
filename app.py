import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import time

# ==========================================
# ⚙️ 1. 앱 설정 & 애니메이션 CSS
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Mobile",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎨 디자인 시스템 (애니메이션 + 토스트 + 로딩바 커스텀)
st.markdown("""
<style>
    /* 전체 배경: 깊은 다크 그레이 */
    .stApp { background-color: #121212; }
    
    /* 1. 로딩바 커스텀 (빨간색 -> 그라데이션) */
    .stProgress > div > div > div > div {
        background: linear-gradient(to right, #FF4B4B, #FFD700);
        border-radius: 10px;
    }
    
    /* 2. 카드 애니메이션 (아래에서 위로 부드럽게 등장) */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translate3d(0, 20px, 0); }
        to { opacity: 1; transform: translate3d(0, 0, 0); }
    }
    .stock-card {
        background-color: #1E1E1E;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 12px;
        border: 1px solid #333;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        animation: fadeInUp 0.5s ease-out; /* 애니메이션 적용 */
    }
    
    /* 3. 테마 헤더 스타일 */
    .theme-header {
        font-size: 1.2rem;
        font-weight: 800;
        color: #FFD700;
        margin-top: 30px;
        margin-bottom: 10px;
        padding-left: 5px;
        border-left: 4px solid #FF4B4B;
        animation: fadeInUp 0.5s ease-out;
    }
    
    /* 4. 텍스트 & 링크 스타일 */
    .stock-title { font-size: 1.1rem; font-weight: bold; color: white; }
    .price-up { color: #FF4B4B; font-weight: bold; float: right; font-size: 1.0rem; }
    .price-down { color: #4B91FF; font-weight: bold; float: right; font-size: 1.0rem; }
    
    .news-item {
        display: block;
        padding: 12px;
        margin-top: 8px;
        background-color: #252525;
        border-radius: 8px;
        color: #e0e0e0;
        text-decoration: none;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    .news-item:hover { background-color: #333; transform: translateX(5px); }
    .news-meta { font-size: 0.75rem; color: #888; margin-top: 5px; }

    /* 불필요한 여백 제거 */
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 분석 엔진 (로직 동일, 로그 출력 제거)
# ==========================================

@st.cache_data(ttl=600)
def build_theme_map_hybrid():
    stock_to_theme = {
        '삼성전자': '반도체', 'SK하이닉스': '반도체', '한미반도체': '반도체/HBM',
        '에코프로': '2차전지', '에코프로비엠': '2차전지', 'LG에너지솔루션': '2차전지', 'POSCO홀딩스': '2차전지',
        '현대차': '자동차', '기아': '자동차',
        '신성델타테크': '초전도체', '서남': '초전도체',
        '우리기술투자': '비트코인', '한화투자증권': '비트코인',
        '한화에어로스페이스': '방산', 'LIG넥스원': '방산', '빅텍': '방산',
        '두산로보틱스': '로봇', '레인보우로보틱스': '로봇',
        'HLB': '바이오', '알테오젠': '바이오', '셀트리온': '바이오',
        'NAVER': '플랫폼', '카카오': '플랫폼'
    }
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = soup.select('.col_type1 a')
        for t in themes[:15]:
            t_name = t.text.strip()
            t_link = "https://finance.naver.com" + t['href']
            sub_res = requests.get(t_link, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            stocks = sub_soup.select('.name_area .name a')
            for s in stocks[:5]:
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
            
            found = False
            for s_name, t_name in stock_map.items():
                if s_name in title:
                    grouped_data.append({'테마': t_name, '종목': s_name, '제목': title, '링크': link, '언론사': press})
                    found = True
                    break
            if not found:
                for t_name in list(set(stock_map.values())):
                    if t_name in title:
                        grouped_data.append({'테마': t_name, '종목': '섹터 종합', '제목': title, '링크': link, '언론사': press})
                        break
    except: pass
    return pd.DataFrame(grouped_data)

# [API 함수들 - 코드 최적화]
@st.cache_data(ttl=600)
def get_live_hot_themes_weekday():
    try: return [t.text.strip() for t in BeautifulSoup(requests.get("https://finance.naver.com/sise/theme.naver", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser').select('.col_type1 a')][:35]
    except: return []

def get_theme_auto_api(code, hot_themes):
    my_theme, news_title = "기타/개별", "-"
    try:
        res = requests.get(f"https://finance.naver.com/item/news_news.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=1)
        soup = BeautifulSoup(res.text, 'html.parser')
        t = soup.select_one('.type5 tbody tr .title a')
        if t: news_title = t.text.strip()
        for ht in hot_themes:
            if ht in news_title: 
                my_theme = ht
                break
    except: pass
    return my_theme, news_title

def check_ath_status(price, token, code, k, s, u):
    try:
        res = requests.get(f"{u}/uapi/domestic-stock/v1/quotation/inquire-price", headers={"authorization": f"Bearer {token}", "appkey": k, "appsecret": s, "tr_id": "FHKST01010100"}, params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code})
        gap = (price - int(res.json()['output']['hst_prc'])) / int(res.json()['output']['hst_prc']) * 100
        if gap > -1: return "👑신고가"
        elif gap > -5: return "🚀임박"
    except: return ""
    return ""

def analyze_program_flow(price, open_p, high_p, low_p, avg_price):
    wick_ratio = (high_p - price) / (high_p - low_p) * 100 if high_p != low_p else 0
    if price > avg_price:
        if wick_ratio < 20: return "매수지속 ↗️", 100
        elif wick_ratio > 50: return "차익실현 ↘️", 50
        else: return "매수유입 ⬆️", 80
    else:
        return ("설거지주의 ☔", 20) if wick_ratio > 50 else ("매도우위 ⬇️", 30)

def get_supply_detail_5days(code):
    f_list = []
    try:
        rows = BeautifulSoup(requests.get(f"https://finance.naver.com/item/frgn.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}).text, 'html.parser').select_one('.type2').select('tr')
        for row in rows:
            cols = row.select('td')
            if len(cols) > 3 and cols[0].text.strip() != "":
                f_val = int(cols[6].text.replace(',', '')) // 1000
                f_list.append(f"+{f_val}" if f_val > 0 else f"{f_val}")
                if len(f_list) >= 5: break
    except: pass
    return f_list

# ==========================================
# 🖥️ 3. 메인 화면 & 사일런트 실행
# ==========================================
st.title("📈 마켓 리더 Mobile")

with st.sidebar:
    st.header("⚙️ 설정")
    mode = st.radio("모드", ["평일(API)", "주말(뉴스)"], index=1)
    if mode == "평일(API)":
        try: 
            APP_KEY, APP_SECRET = st.secrets["APP_KEY"], st.secrets["APP_SECRET"]
            st.success("✅ Ready")
        except: 
            APP_KEY, APP_SECRET = st.text_input("Key", type="password"), st.text_input("Secret", type="password")
        URL_BASE = "https://openapi.koreainvestment.com:9443"

# ----------------------------------------
# A. 주말 모드 (Clean UI)
# ----------------------------------------
if mode == "주말(뉴스)":
    # 설명 텍스트 대신 깔끔한 버튼만 배치
    if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
        
        # 🟢 로딩 바 (텍스트 없이 바만 움직임)
        progress_bar = st.progress(0)
        
        # 1. 내부 처리 (Logs hidden)
        stock_map = build_theme_map_hybrid()
        progress_bar.progress(50) # 50%
        
        df = get_news_hybrid(stock_map)
        progress_bar.progress(100) # 100%
        time.sleep(0.5) # 0.5초 뒤 로딩바 삭제를 위한 딜레이
        progress_bar.empty() # 로딩바 삭제
        
        # 🟢 토스트 메시지 (알림)
        if df.empty:
            st.toast("⚠️ 이슈를 찾지 못했습니다.", icon="📭")
        else:
            st.toast(f"분석 완료! {len(df)}건의 이슈 발견", icon="✅")
            
            # 결과 출력
            theme_groups = df.groupby('테마')
            sorted_themes = sorted(theme_groups.groups.keys(), key=lambda x: len(theme_groups.get_group(x)), reverse=True)
            
            for theme in sorted_themes:
                t_group = theme_groups.get_group(theme)
                
                # 애니메이션 적용된 헤더
                st.markdown(f"<div class='theme-header'>📦 {theme} <span style='font-size:0.9rem; color:#888;'>({len(t_group)})</span></div>", unsafe_allow_html=True)
                
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
# B. 평일 모드 (Clean UI)
# ----------------------------------------
else:
    if st.button("🚀 실시간 분석", use_container_width=True, type="primary"):
        if not APP_KEY: st.toast("⚠️ 키 설정이 필요합니다.", icon="🚨")
        else:
            # 로딩바만 깔끔하게 표시
            progress = st.progress(0)
            
            try:
                body = {"grant_type":"client_credentials", "appkey":APP_KEY, "appsecret":APP_SECRET}
                res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, json=body)
                token = res.json()['access_token']
                progress.progress(20)
                
                headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
                params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
                
                res_data = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
                raw_data = res_data.json()['output'][:25]
                progress.progress(50)
                
                analyzed_data = []
                hot_themes = get_live_hot_themes_weekday()
                
                # 분석 루프
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
                    
                    # 로딩바 부드럽게 채우기 (50% -> 90%)
                    current_prog = 50 + int((i+1)/len(raw_data)*40)
                    progress.progress(current_prog)
                
                progress.progress(100)
                time.sleep(0.5)
                progress.empty()
                st.toast("분석이 완료되었습니다!", icon="🔥")
                
                # 결과 출력
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
                                <div>
                                    <span class="stock-title">{row['종목']}</span> {badges} 
                                    <span class="{price_cls}">{icon} {row['등락']}%</span>
                                </div>
                                <div style="margin-top:5px; font-size:0.9rem; color:#ddd;">현재가: {row['현재가']:,}원</div>
                                <hr style="border-color:#333; margin:10px 0;">
                                <div style="font-size:0.9rem; color:#ccc;">
                                    <span class="flow-txt">🤖 {row['흐름']}</span>
                                    <div style="margin-top:4px;">👽 외인(5일): {', '.join(row['외인'])}</div>
                                </div>
                                <a href="#" class="news-item">📰 {row['뉴스'][:30]}...</a>
                            </div>
                            """, unsafe_allow_html=True)

            except Exception as e:
                st.toast(f"오류 발생: {e}", icon="❌")
