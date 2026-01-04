import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

# 페이지 기본 설정
st.set_page_config(page_title="마켓 리더 Pro", page_icon="📈", layout="wide")

# 제목
st.title("📈 마켓 리더 V12 : 고수의 눈 (Expert Eye)")
st.markdown("---")

# ==========================================
# 🔑 사이드바: 설정 및 키 입력
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    st.info("실전투자 서버(API)를 사용합니다.")
    
    # 매번 입력하기 귀찮으면 여기에 본인 키를 적어두세요 (보안 주의!)
    APP_KEY = st.text_input("PSK10caZvUr1pW68nGscZmanqNEYIlnYtPjd", value="", type="password")
    APP_SECRET = st.text_input("cLrXue1No1GjWvnhcCT/YO3eE9PtI/5nie359YS9BW+OTagIFcsdWJFKM2L9oymG4rSQ5YgGI44mApjm1h2MVAexN8u5+OCe3+0UzY6u6Hx+kLA/tzTPBsqbFUzYQa1wYOn4r68fV2CwuUF3GTs7WMVL0z1LSipkG3Ho5GmJJmEadI9cebk=", value="", type="password")
    
    URL_BASE = "https://openapi.koreainvestment.com:9443" # 실전투자 주소
    
    run_btn = st.button("🚀 데이터 분석 시작")

# ==========================================
# 🧠 분석 로직 (V12 엔진 탑재)
# ==========================================
def get_live_hot_themes():
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = [t.text.strip() for t in soup.select('.col_type1 a')]
        return themes[:35]
    except: return ['반도체', '2차전지', 'AI', '로봇', '바이오']

def get_theme_auto(code, hot_themes):
    my_theme = "기타"
    news_title = ""
    try:
        res = requests.get(f"https://finance.naver.com/item/news_news.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        t_tag = soup.select_one('.type5 tbody tr .title a')
        if t_tag: news_title = t_tag.text.strip()
        for ht in hot_themes:
            if ht in news_title: 
                my_theme = ht
                break
        if my_theme == "기타":
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
        data = res.json()['output']
        highest_price = int(data['hst_prc'])
        gap = (price - highest_price) / highest_price * 100
        if gap > -1: return "👑신고가 돌파!"
        elif gap > -5: return f"🚀신고가 근접({gap:.1f}%)"
        else: return ""
    except: return ""

def analyze_program_flow(price, open_p, high_p, low_p, avg_price):
    if high_p != low_p: wick_ratio = (high_p - price) / (high_p - low_p) * 100
    else: wick_ratio = 0
    
    if price > avg_price:
        if wick_ratio < 20: return "매수 우위 (지속) ↗️", 100
        elif wick_ratio > 50: return "차익실현 중 (주의) ↘️", 50
        else: return "매수세 유입 중 ⬆️", 80
    else:
        if wick_ratio > 50: return "막판 매도세 (설거지) ☔", 20
        else: return "매도 우위 (약세) ⬇️", 30

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

# 메인 로직 실행
if run_btn:
    if not APP_KEY or not APP_SECRET:
        st.error("⚠️ 사이드바에 APP KEY와 SECRET을 입력해주세요!")
    else:
        with st.spinner('📡 마켓 데이터를 분석하고 있습니다... (약 20초 소요)'):
            hot_themes = get_live_hot_themes()
            
            try:
                # 토큰 발급
                res = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, data='{"grant_type":"client_credentials", "appkey":"'+APP_KEY+'", "appsecret":"'+APP_SECRET+'"}')
                token = res.json()['access_token']
                
                # 데이터 요청
                headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
                params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
                
                res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
                data = res.json()['output'][:25]
                
                analyzed_data = []
                for item in data:
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
                    
                    analyzed_data.append({'테마': theme, '종목': name, '등락': rate, '점수': score, '현재가':price, '신고가': ath_status, '흐름': flow_txt, '흐름점수':flow_score, '외인5': f_list, '기관5': i_list, '뉴스': news})
                
                # 화면 출력
                df = pd.DataFrame(analyzed_data)
                grouped = df.groupby('테마')
                theme_order = grouped['점수'].mean().sort_values(ascending=False).index
                
                st.success("✅ 분석 완료! 신고가와 프로그램 매수세가 강한 종목을 확인하세요.")
                
                for theme_name in theme_order:
                    group_df = grouped.get_group(theme_name)
                    if group_df['점수'].max() < 40: continue
                    
                    with st.expander(f"📦 [{theme_name}] 섹터 (평균 {group_df['등락'].mean():.1f}%)", expanded=True):
                        for idx, row in group_df.head(3).iterrows():
                            c1, c2 = st.columns([2, 3])
                            with c1:
                                st.subheader(f"{row['종목']} {row['등락']}%")
                                st.caption(f"현재가: {row['현재가']:,}원")
                                if row['신고가']: st.warning(row['신고가'])
                            with c2:
                                st.text(f"🤖 {row['흐름']}")
                                st.progress(row['흐름점수'])
                                st.text(f"👽외인: {', '.join(row['외인5'])}")
                                st.text(f"🏦기관: {', '.join(row['기관5'])}")
                            if idx==0 and row['점수'] >= 60:
                                st.info(f"📰 {row['뉴스'][:40]}...")
                            st.divider()

            except Exception as e:
                st.error(f"오류 발생: {e}")
