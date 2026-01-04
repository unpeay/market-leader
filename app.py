import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ 앱 기본 설정 & 디자인 주입 (CSS)
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 커스텀 CSS (여기가 디자인의 핵심!)
st.markdown("""
<style>
    /* 전체 배경 및 폰트 */
    .stApp { background-color: #0E1117; }
    
    /* 종목 카드 디자인 */
    .stock-card {
        background-color: #262730;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #333;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* 상승(빨강) / 하락(파랑) 텍스트 */
    .price-up { color: #FF4B4B; font-weight: bold; font-size: 1.2rem; }
    .price-down { color: #4B91FF; font-weight: bold; font-size: 1.2rem; }
    
    /* 뱃지 디자인 */
    .badge-s { background-color: #FFD700; color: black; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 0.8rem; margin-right: 5px; }
    .badge-new { background-color: #FF4B4B; color: white; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 0.8rem; margin-right: 5px; }
    .badge-theme { background-color: #444; color: white; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; }
    
    /* 수급 텍스트 */
    .supply-txt { font-size: 0.9rem; color: #ccc; }
    .flow-txt { font-size: 0.95rem; font-weight: bold; color: #eee; }
    
    /* 뉴스 링크 */
    .news-link { color: #888; font-size: 0.85rem; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# 제목
st.title("📈 마켓 리더 Pro")
st.markdown("#### :dart: 고수의 눈으로 찾은 주도주 (Design v2.0)")
st.markdown("---")

# ==========================================
# 🔑 사이드바: 설정
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        st.success("✅ 인증키 로드 완료")
    except:
        st.warning("⚠️ 키 설정 필요")
        APP_KEY = st.text_input("APP Key", type="password")
        APP_SECRET = st.text_input("APP Secret", type="password")
    
    URL_BASE = "https://openapi.koreainvestment.com:9443"
    st.markdown("---")
    run_btn = st.button("🚀 분석 시작 (Start)", type="primary", use_container_width=True)

# ==========================================
# 🧠 분석 엔진 (V12 로직 유지)
# ==========================================
@st.cache_data(ttl=600)
def get_live_hot_themes():
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = [t.text.strip() for t in soup.select('.col_type1 a')]
        return themes[:35]
    except: return ['반도체', '2차전지', 'AI', '로봇', '바이오']

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

def check_ath_status(price, token, code):
    try:
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"}
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/inquire-price", headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()['output']
            highest_price = int(data['hst_prc'])
            gap = (price - highest_price) / highest_price * 100
            if gap > -1: return "👑신고가"
            elif gap > -5: return f"🚀신고가근접"
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
                f_str = f"+{f_val}" if f_val > 0 else f"{f_val}"
                i_str = f"+{i_val}" if i_val > 0 else f"{i_val}"
                f_list.append(f_str)
                i_list.append(i_str)
                cnt += 1
    except: pass
    return f_list, i_list

# ==========================================
# 🚀 메인 실행 및 UI 렌더링
# ==========================================
if run_btn:
    if not APP_KEY or not APP_SECRET:
        st.error("⚠️ 키가 없습니다. 사이드바 설정을 확인하세요.")
    else:
        status_text = st.empty()
        status_text.info("📡 시장 데이터 스캔 중... (잠시만 기다려주세요)")
        progress_bar = st.progress(0)
        
        try:
            hot_themes = get_live_hot_themes()
            
            # 토큰 발급
            res_token = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, data='{"grant_type":"client_credentials", "appkey":"'+APP_KEY+'", "appsecret":"'+APP_SECRET+'"}')
            if res_token.status_code != 200:
                st.error("❌ 로그인 실패. 키 값이나 서버 상태를 확인하세요.")
                st.stop()
            token = res_token.json()['access_token']
            
            # 데이터 요청
            headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
            
            res_data = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
            raw_data = res_data.json()['output'][:25]
            
            analyzed_data = []
            
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
                ath_status = check_ath_status(price, token, code)
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
            
            # 📊 화면 출력 (디자인 적용)
            df = pd.DataFrame(analyzed_data)
            grouped = df.groupby('테마')
            theme_order = grouped['점수'].mean().sort_values(ascending=False).index
            
            for theme_name in theme_order:
                group_df = grouped.get_group(theme_name)
                if group_df['점수'].max() < 40: continue
                
                # 테마 헤더
                st.markdown(f"#### 📦 {theme_name}")
                
                for idx, row in group_df.head(3).iterrows():
                    # 스타일 클래스 결정
                    price_class = "price-up" if row['등락'] > 0 else "price-down"
                    icon = "🔥" if row['등락'] > 10 else ("🔺" if row['등락'] > 0 else "🔹")
                    
                    # 뱃지 HTML 생성
                    badges = ""
                    if row['점수'] >= 90: badges += "<span class='badge-s'>S급</span>"
                    if row['신고가']: badges += f"<span class='badge-new'>{row['신고가']}</span>"
                    
                    # 카드 시작
                    with st.container():
                        st.markdown(f"""
                        <div class="stock-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <span style="font-size:1.1rem; font-weight:bold; color:white;">{row['종목']}</span>
                                    {badges}
                                </div>
                                <div class="{price_class}">
                                    {icon} {row['등락']}% <span style="font-size:0.9rem; color:#aaa;">({row['현재가']:,}원)</span>
                                </div>
                            </div>
                            <hr style="margin: 10px 0; border-color: #444;">
                            <div style="display:flex; justify-content:space-between;">
                                <div style="width:48%;">
                                    <div class="flow-txt">🤖 {row['흐름']}</div>
                                    <div class="supply-txt">👽외인: {', '.join(row['외인5'])}</div>
                                    <div class="supply-txt">🏦기관: {', '.join(row['기관5'])}</div>
                                </div>
                                <div style="width:48%; text-align:right;">
                                    <div style="color:#888; font-size:0.8rem;">관련 뉴스</div>
                                    <div style="color:#ddd; font-size:0.85rem;">{row['뉴스'][:25]}...</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 게이지 바 (마감 강도)는 스트림릿 기능 사용 (디자인 매칭)
                        st.progress(row['흐름점수'])
                
                st.write("") # 간격

        except Exception as e:
            st.error(f"오류 발생: {e}")
