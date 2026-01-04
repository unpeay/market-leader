import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ 앱 기본 설정
# ==========================================
st.set_page_config(
    page_title="마켓 리더 Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 제목
st.title("📈 마켓 리더 V12 : 프로 트레이더 대시보드")
st.caption("신고가 감지 | 프로그램 수급 포착 | 5일 상세 수급 | 테마별 대장주")
st.markdown("---")

# ==========================================
# 🔑 사이드바: 설정 (자동 로그인 + 수동 입력 겸용)
# ==========================================
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 1. Secrets(비밀금고)에서 키 가져오기 시도
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        st.success("✅ 인증키가 자동으로 로드되었습니다!")
        auth_status = True
    except:
        st.warning("⚠️ Secrets 설정이 감지되지 않았습니다.")
        st.info("수동으로 키를 입력하거나, 배포 설정에서 Secrets를 등록하세요.")
        APP_KEY = st.text_input("APP Key", type="password")
        APP_SECRET = st.text_input("APP Secret", type="password")
        auth_status = False
    
    # 👉 [중요] 실전투자 주소 (평일 09:00~15:30 사용)
    URL_BASE = "https://openapi.koreainvestment.com:9443"
    
    st.markdown("---")
    run_btn = st.button("🚀 데이터 분석 시작", use_container_width=True, type="primary")
    st.caption("※ 장 운영 시간(평일)에만 정상 작동합니다.")

# ==========================================
# 🧠 분석 엔진 (함수 모음)
# ==========================================

# 1. 핫 테마 수집 (네이버 금융)
@st.cache_data(ttl=600) # 10분마다 갱신
def get_live_hot_themes():
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        themes = [t.text.strip() for t in soup.select('.col_type1 a')]
        return themes[:35]
    except:
        return ['반도체', '2차전지', 'AI', '로봇', '바이오']

# 2. 종목별 테마 & 뉴스 매칭
def get_theme_auto(code, hot_themes):
    my_theme = "기타/개별"
    news_title = "-"
    try:
        # 뉴스 크롤링
        res = requests.get(f"https://finance.naver.com/item/news_news.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        t_tag = soup.select_one('.type5 tbody tr .title a')
        if t_tag: news_title = t_tag.text.strip()
        
        # 뉴스 제목 기반 테마 매칭
        for ht in hot_themes:
            if ht in news_title: 
                my_theme = ht
                break
        
        # 없으면 네이버 섹터 정보
        if my_theme == "기타/개별":
            res_m = requests.get(f"https://finance.naver.com/item/main.naver?code={code}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            th_tag = BeautifulSoup(res_m.text, 'html.parser').select_one('.section.trade_compare > h4 > em')
            if th_tag: my_theme = th_tag.text.strip()
    except: pass
    return my_theme, news_title

# 3. 52주 신고가 감지 (API)
def check_ath_status(price, token, code):
    try:
        headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHKST01010100"}
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        res = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/inquire-price", headers=headers, params=params)
        
        if res.status_code == 200:
            data = res.json()['output']
            highest_price = int(data['hst_prc'])
            gap = (price - highest_price) / highest_price * 100
            
            if gap > -1: return "👑신고가 돌파!"
            elif gap > -5: return f"🚀신고가 근접({gap:.1f}%)"
    except: pass
    return ""

# 4. 프로그램 흐름 추정 (평단가 vs 현재가)
def analyze_program_flow(price, open_p, high_p, low_p, avg_price):
    if high_p != low_p: wick_ratio = (high_p - price) / (high_p - low_p) * 100
    else: wick_ratio = 0
    
    # 로직 판단
    if price > avg_price:
        if wick_ratio < 20: return "매수 우위 (지속) ↗️", 100
        elif wick_ratio > 50: return "차익실현 중 (주의) ↘️", 50
        else: return "매수세 유입 중 ⬆️", 80
    else:
        if wick_ratio > 50: return "막판 매도세 (설거지) ☔", 20
        else: return "매도 우위 (약세) ⬇️", 30

# 5. 5일 상세 수급 (크롤링)
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
                # 1000주 단위로 변환
                f_val = int(cols[6].text.replace(',', '')) // 1000 
                i_val = int(cols[5].text.replace(',', '')) // 1000
                f_list.append(f"+{f_val}" if f_val > 0 else f"{f_val}")
                i_list.append(f"+{i_val}" if i_val > 0 else f"{i_val}")
                cnt += 1
    except: pass
    return f_list, i_list

# ==========================================
# 🚀 메인 실행 로직
# ==========================================
if run_btn:
    if not APP_KEY or not APP_SECRET:
        st.error("⚠️ APP KEY와 SECRET이 입력되지 않았습니다.")
    else:
        status_area = st.empty()
        status_area.info("📡 네이버 금융에서 '오늘의 핫 테마'를 스캔 중입니다...")
        
        # 1. 테마 수집
        hot_themes = get_live_hot_themes()
        
        status_area.info(f"🔑 한국투자증권 서버에 접속 중입니다... ({URL_BASE})")
        
        try:
            # 2. 토큰 발급 (안전장치 포함)
            body = {"grant_type":"client_credentials", "appkey":APP_KEY, "appsecret":APP_SECRET}
            res_token = requests.post(f"{URL_BASE}/oauth2/tokenP", headers={"content-type":"application/json"}, json=body)
            
            if res_token.status_code != 200:
                status_area.error(f"❌ 로그인 실패 (상태코드: {res_token.status_code})")
                st.error("원인: 키 값이 틀렸거나, 현재 서버 점검 중(주말/공휴일)일 수 있습니다.")
                st.stop()
                
            token = res_token.json()['access_token']
            
            # 3. 거래대금 상위 종목 요청
            status_area.info("⏳ 전 종목 거래대금을 분석하고 있습니다... (약 20초 소요)")
            
            headers = {"content-type": "application/json", "authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "FHPST01710000", "custtype": "P"}
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_COND_SCR_GRP_CODE": "11518", "FID_INPUT_ISCD_2": "0000", "FID_INPUT_CNT_1": "30", "FID_APLY_RANG_VOL": "0", "FID_RANK_SORT_CLS_CODE": "1", "FID_TRGT_CLS_CODE": "0", "FID_TRGT_EXLS_CLS_CODE": "0", "FID_INPUT_PRICE_1": "", "FID_INPUT_PRICE_2": "", "FID_VOL_CNT": ""}
            
            res_data = requests.get(f"{URL_BASE}/uapi/domestic-stock/v1/quotation/volume-rank", headers=headers, params=params)
            
            if res_data.status_code != 200:
                status_area.error("❌ 데이터 조회 실패. 서버 점검 중일 수 있습니다.")
                st.stop()

            # 4. 데이터 정밀 분석
            raw_data = res_data.json()['output'][:25] # 상위 25개
            analyzed_data = []
            
            progress_bar = st.progress(0)
            
            for i, item in enumerate(raw_data):
                code = item['mksc_shrn_iscd']
                name = item['hts_kor_isnm']
                price = int(item['stck_prpr'])
                open_p = int(item['stck_oprc'])
                high_p = int(item['stck_hgpr'])
                low_p = int(item['stck_lwpr'])
                rate = float(item['prdy_ctrt'])
                vol = int(item['acml_tr_pbmn']) // 100000000
                
                # 평균단가 계산
                total_vol = int(item['acml_vol'])
                avg_price = (int(item['acml_tr_pbmn']) / total_vol) if total_vol > 0 else price
                
                # 분석 함수 호출
                theme, news = get_theme_auto(code, hot_themes)
                ath_status = check_ath_status(price, token, code)
                flow_txt, flow_score = analyze_program_flow(price, open_p, high_p, low_p, avg_price)
                f_list, i_list = get_supply_detail_5days(code)
                
                # 점수 계산
                score = 0
                if "매수" in flow_txt: score += 30
                if "신고가" in ath_status: score += 30
                if vol >= 1000: score += 20
                if price > open_p: score += 20
                
                analyzed_data.append({
                    '테마': theme, '종목': name, '등락': rate, '점수': score, 
                    '현재가': price, '신고가': ath_status, 
                    '흐름': flow_txt, '흐름점수': flow_score, 
                    '외인5': f_list, '기관5': i_list, '뉴스': news
                })
                
                # 진행률 업데이트
                progress_bar.progress((i + 1) / len(raw_data))
            
            status_area.empty() # 로딩 메시지 삭제
            progress_bar.empty()
            
            # 5. 화면 출력 (테마별 그룹핑)
            df = pd.DataFrame(analyzed_data)
            grouped = df.groupby('테마')
            theme_order = grouped['점수'].mean().sort_values(ascending=False).index
            
            st.success(f"✅ 분석 완료! 총 {len(raw_data)}개 종목을 스캔했습니다.")
            
            for theme_name in theme_order:
                group_df = grouped.get_group(theme_name)
                # 점수 낮은 테마는 패스 (노이즈 제거)
                if group_df['점수'].max() < 40: continue
                
                # 테마 박스
                with st.expander(f"📦 [{theme_name}] 섹터 (평균 {group_df['등락'].mean():.1f}%)", expanded=True):
                    for idx, row in group_df.head(3).iterrows(): # 상위 3개만
                        c1, c2 = st.columns([1.2, 2])
                        
                        with c1:
                            st.subheader(f"{row['종목']}")
                            color = "red" if row['등락'] > 0 else "blue"
                            st.markdown(f":{color}[**{row['등락']}%**] ( {row['현재가']:,}원 )")
                            if row['신고가']: 
                                st.warning(f"{row['신고가']}")
                        
                        with c2:
                            st.caption(f"🤖 프로그램: {row['흐름']}")
                            st.progress(row['흐름점수'])
                            # 수급 데이터 예쁘게 표시
                            f_str = ", ".join(row['외인5']) if row['외인5'] else "-"
                            i_str = ", ".join(row['기관5']) if row['기관5'] else "-"
                            st.text(f"👽외인(5일): [{f_str}]")
                            st.text(f"🏦기관(5일): [{i_str}]")
                        
                        # 뉴스 표시 (1등이거나 점수 높으면)
                        if idx == 0 and row['점수'] >= 60:
                            st.info(f"📰 {row['뉴스'][:45]}...")
                        
                        st.divider()

        except Exception as e:
            status_area.error(f"오류 발생: {e}")
