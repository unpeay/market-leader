import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from datetime import datetime

# ==========================================
# ⚙️ 1. 앱 설정 & 디자인 (Integrated Corporate Style)
# ==========================================
st.set_page_config(
    page_title="Market Leader Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css" rel="stylesheet">
<style>
    /* 기본 폰트 및 배경 */
    html, body, .stApp {
        font-family: 'Pretendard', sans-serif;
        background-color: #F0F2F5;
    }

    /* 메인 헤더 */
    .pro-header {
        background: linear-gradient(135deg, #1A237E, #283593); /* Deep Navy */
        color: white;
        padding: 25px 30px;
        border-radius: 0 0 20px 20px;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }
    .pro-title { font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; }
    .pro-subtitle { font-size: 0.95rem; opacity: 0.8; margin-top: 5px; font-weight: 300; }

    /* --- [평일 모드 스타일] --- */
    .section-title {
        font-size: 1.4rem; font-weight: 800; color: #1A237E;
        margin: 40px 0 15px 0; padding-bottom: 10px;
        border-bottom: 3px solid #1A237E;
        display: flex; justify-content: space-between; align-items: flex-end;
    }
    .theme-box {
        background-color: white; border-radius: 12px; padding: 20px;
        margin-bottom: 20px; border: 1px solid #E0E0E0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .theme-name { font-size: 1.3rem; font-weight: 800; color: #333; }
    .theme-stat { font-size: 0.9rem; color: #666; float: right; font-weight:bold; }
    
    .stock-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 0; border-bottom: 1px solid #F0F0F0;
    }
    .stock-row:last-child { border-bottom: none; }
    .s-name { font-weight: 700; font-size: 1rem; color: #222; width: 40%; }
    .s-cap { font-size: 0.85rem; color: #888; width: 25%; text-align: right; }
    .s-price { font-weight: 600; font-size: 0.95rem; width: 20%; text-align: right; }
    .s-rate { font-weight: 800; font-size: 0.95rem; width: 15%; text-align: right; }
    .up { color: #D32F2F; } .down { color: #1976D2; }
    .tag-leader { background:#FFF3E0; color:#EF6C00; padding:2px 6px; border-radius:4px; font-size:0.7rem; margin-left:5px; font-weight:bold; }

    /* --- [주말 모드 스타일] --- */
    .theme-header {
        font-size: 1.4rem; font-weight: 800; color: #1A237E;
        margin: 30px 0 15px 0; padding-bottom: 10px;
        border-bottom: 2px solid #1A237E;
    }
    .news-card {
        background-color: white; padding: 20px; border-radius: 12px;
        margin-bottom: 15px; border: 1px solid #E0E0E0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .news-card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
    .news-title { font-size: 1.1rem; font-weight: 700; color: #333; text-decoration: none; display: block; margin-bottom: 10px;}
    .news-info { font-size: 0.85rem; color: #888; margin-bottom: 12px; }
    
    .related-stock-box {
        background-color: #F5F7FA; padding: 12px; border-radius: 8px;
        border-left: 4px solid #1A237E; margin-top: 10px;
    }
    .stock-tag {
        display: inline-block; background: white; border: 1px solid #ddd;
        padding: 4px 10px; border-radius: 15px; font-size: 0.85rem;
        font-weight: 600; color: #333; margin-right: 6px; margin-bottom: 4px;
    }
    .theme-tag {
        background-color: #E8EAF6; color: #1A237E; font-weight: bold;
        padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 2. 공통 데이터 & 헬퍼 함수
# ==========================================

# [주말용] 알짜 종목 DB (섹터 상세 분류)
def get_static_stock_db():
    return {
        '비트코인/가상화폐': ['우리기술투자', '한화투자증권', '위지트', '티사이언티픽', '다날', '갤럭시아머니트리'],
        '반도체/HBM': ['삼성전자', 'SK하이닉스', '한미반도체', '이수페타시스', '주성엔지니어링', 'STI'],
        '반도체 소부장': ['HPSP', '동진쎄미켐', '하나마이크론', '리노공업', '솔브레인', '원익IPS', '유진테크'],
        '온디바이스AI/NPU': ['제주반도체', '가온칩스', '오픈엣지테크놀로지', '칩스앤미디어', '텔레칩스', '퀄리타스반도체'],
        '2차전지/배터리': ['에코프로', '에코프로비엠', 'LG에너지솔루션', 'POSCO홀딩스', '포스코퓨처엠', '금양', '나노신소재'],
        '초전도체/신소재': ['신성델타테크', '서남', '덕성', '파워로직스', '모비스'],
        '방위산업/전쟁': ['한화에어로스페이스', 'LIG넥스원', '현대로템', '빅텍', '스페코', '한국항공우주'],
        'AI/로봇': ['두산로보틱스', '레인보우로보틱스', '로보티즈', '이랜시스', '뉴로메카'],
        '제약/바이오': ['HLB', '알테오젠', '셀트리온', '유한양행', '삼천당제약', '레고켐바이오'],
        '저PBR/금융/지주': ['제주은행', 'KB금융', '하나금융지주', '현대차', '기아', '삼성물산']
    }

# [평일용] 시가총액 크롤링 (억 단위 변환)
@st.cache_data(ttl=3600)
def get_market_cap(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        raw = soup.select_one('#_market_sum').text.strip()
        cap_val = 0
        if "조" in raw:
            parts = raw.split("조")
            jo = int(parts[0].replace(',', '').strip()) * 10000
            eok = int(parts[1].replace(',', '').strip()) if parts[1].strip() else 0
            cap_val = jo + eok
        else:
            cap_val = int(raw.replace(',', '').strip())
        return cap_val
    except:
        return 0

# ==========================================
# 🧠 3. 핵심 분석 로직 (주말 vs 평일)
# ==========================================

# [주말] 뉴스 크롤링 & 매핑 (V24 로직)
@st.cache_data(ttl=600)
def analyze_weekend_news():
    news_data = []
    stock_db = get_static_stock_db()
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # 랭킹뉴스 (가장 많이 본 뉴스)
        base_url = "https://finance.naver.com/news/news_list.naver?mode=RANK&date=" + datetime.now().strftime("%Y%m%d")
        
        res = requests.get(base_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = soup.select('.newsList li')
        
        for item in news_items:
            a_tag = item.select_one('a')
            if not a_tag: continue
            
            title = a_tag.text.strip()
            link = "https://finance.naver.com" + a_tag['href']
            press = item.select_one('.press').text.strip() if item.select_one('.press') else "뉴스"
            summary = item.select_one('.articleSummary').text.strip()[:60] + "..." if item.select_one('.articleSummary') else ""

            matched_theme = "기타 이슈"
            related_stocks = []
            
            # DB 매칭
            for theme, stocks in stock_db.items():
                # 1. 키워드 매칭 (테마명)
                keywords = theme.split('/')
                is_match = False
                for k in keywords:
                    if k in title:
                        is_match = True
                        break
                # 2. 종목명 매칭
                if not is_match:
                    for s in stocks:
                        if s in title:
                            is_match = True
                            break
                
                if is_match:
                    matched_theme = theme
                    related_stocks = stocks
                    break
            
            if matched_theme != "기타 이슈":
                news_data.append({
                    '테마': matched_theme,
                    '제목': title,
                    '요약': summary,
                    '링크': link,
                    '언론사': press,
                    '관련주': related_stocks
                })
    except Exception as e:
        print(e)
    return pd.DataFrame(news_data)

# [평일] 시총 3000억 이상 필터링 + 랭킹 (V23 로직)
@st.cache_data(ttl=600)
def analyze_weekday_market_filtered():
    final_themes = []
    try:
        url = "https://finance.naver.com/sise/theme.naver"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        theme_links = soup.select('.col_type1 a')
        
        # 진행상황 공유용
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 상위 20개 테마 분석
        for idx, t_link in enumerate(theme_links[:20]):
            t_name = t_link.text.strip()
            link = "https://finance.naver.com" + t_link['href']
            
            status_text.text(f"📡 분석 중... {t_name} (시가총액 3,000억 이상 선별)")
            progress_bar.progress((idx + 1) / 20)
            
            sub_res = requests.get(link, headers=headers, timeout=2)
            sub_soup = BeautifulSoup(sub_res.text, 'html.parser')
            rows = sub_soup.select('.type_5 tbody tr')
            
            valid_stocks = []
            theme_total_vol = 0
            theme_avg_rate = 0.0
            count = 0
            
            for row in rows:
                cols = row.select('td')
                if len(cols) < 2: continue
                try:
                    name = cols[0].text.strip()
                    code = cols[0].select_one('a')['href'].split('code=')[1]
                    price = cols[1].text.strip()
                    rate = float(cols[3].text.strip().replace('%', ''))
                    vol_val = int(cols[6].text.strip().replace(',', '')) # 백만 단위
                    
                    # 🚨 시가총액 조회 (속도 저하 원인이지만 정확성 위해 필수)
                    market_cap = get_market_cap(code) # 억 단위
                    
                    if market_cap >= 3000: # 3000억 이상만
                        valid_stocks.append({
                            '종목명': name,
                            '현재가': price,
                            '등락률': rate,
                            '시가총액': market_cap,
                            '거래대금': vol_val
                        })
                        theme_total_vol += vol_val
                        theme_avg_rate += rate
                        count += 1
                except: continue
            
            if count >= 3: # 유효 종목 3개 이상인 테마만
                valid_stocks.sort(key=lambda x: x['등락률'], reverse=True)
                final_themes.append({
                    '테마명': t_name,
                    '평균등락률': theme_avg_rate / count,
                    '총거래대금': theme_total_vol,
                    '구성종목': valid_stocks[:5] # 상위 5개만
                })
        
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        print(e)
        
    return final_themes

# ==========================================
# 🖥️ 4. 메인 화면 출력
# ==========================================

# 헤더 영역
st.markdown("""
<div class="pro-header">
    <div class="pro-title">Market Leader Pro</div>
    <div class="pro-subtitle">Integrated Intelligence System</div>
</div>
""", unsafe_allow_html=True)

# 사이드바 설정
with st.sidebar:
    st.header("Settings")
    mode = st.radio("Mode Selection", ["주말/야간 (뉴스 인사이트)", "평일 장중 (우량주 랭킹)"], index=0)
    st.markdown("---")
    st.info("시가총액 3,000억 이상 종목만 분석하여 잡주를 배제합니다.")

# ----------------------------------------
# A. 주말 모드 (뉴스 분석 + 관련주 매핑)
# ----------------------------------------
if mode == "주말/야간 (뉴스 인사이트)":
    st.write("")
    if st.button("🚀 주말 핫 이슈 & 섹터 분석 (Deep Scan)", use_container_width=True, type="primary"):
        
        with st.spinner("주말 뉴스 및 관련주 데이터베이스 매칭 중..."):
            df = analyze_weekend_news()
        
        if df.empty:
            st.warning("⚠️ 분석된 핵심 이슈가 없습니다. (뉴스 제목 키워드 부재)")
        else:
            st.success(f"✅ 총 {len(df)}건의 유의미한 이슈를 포착했습니다.")
            
            # 테마별 그룹핑 & 정렬
            theme_groups = df.groupby('테마')
            sorted_themes = sorted(theme_groups.groups.keys(), key=lambda x: len(theme_groups.get_group(x)), reverse=True)
            
            for theme in sorted_themes:
                t_group = theme_groups.get_group(theme)
                
                # 테마 헤더
                st.markdown(f"""
                <div class="theme-header">
                    📦 {theme} <span style="font-size:1rem; color:#666; font-weight:400;">({len(t_group)}건)</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 뉴스 카드 루프
                for idx, row in t_group.iterrows():
                    # 관련주 태그 생성
                    stock_tags_html = ""
                    for s in row['관련주']:
                        stock_tags_html += f"<span class='stock-tag'>{s}</span>"
                    
                    with st.container():
                        st.markdown(f"""
                        <div class="news-card">
                            <span class="theme-tag">{row['테마']}</span>
                            <span style="font-size:0.8rem; color:#888;">{row['언론사']}</span>
                            
                            <a href="{row['링크']}" target="_blank" class="news-title" style="margin-top:8px;">
                                {row['제목']}
                            </a>
                            <div class="news-info">{row['요약']}</div>
                            
                            <div class="related-stock-box">
                                <div style="font-size:0.8rem; color:#555; margin-bottom:5px; font-weight:bold;">💡 관련 대장주 및 주요 종목</div>
                                {stock_tags_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

# ----------------------------------------
# B. 평일 모드 (우량주 테마 랭킹)
# ----------------------------------------
else:
    st.write("")
    if st.button("🚀 실시간 우량주 테마 랭킹 (시총 3000억↑)", use_container_width=True, type="primary"):
        
        # 필터링 로직 실행 (V23 로직)
        data = analyze_weekday_market_filtered()
        
        if not data:
            st.error("데이터 수신 실패 (네이버 금융 접속 오류 등)")
        else:
            df = pd.DataFrame(data)
            
            # 1. 상승률 TOP 5
            st.markdown("""
            <div class="section-title">
                <div>🔥 상승률 상위 TOP 5 <span style="font-size:0.9rem; color:#666; font-weight:400;">(오늘의 주도 테마)</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            top_change = df.sort_values(by='평균등락률', ascending=False).head(5)
            
            for idx, row in top_change.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="theme-box">
                        <div style="overflow:hidden; margin-bottom:10px;">
                            <span class="theme-name">{row['테마명']}</span>
                            <span class="theme-stat" style="color:#D32F2F;">평균 +{row['평균등락률']:.2f}%</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for i, s in enumerate(row['구성종목']):
                        color = "up" if s['등락률'] > 0 else "down"
                        leader = "<span class='tag-leader'>대장주</span>" if i == 0 else ""
                        st.markdown(f"""
                        <div class="stock-row">
                            <div class="s-name">{s['종목명']}{leader}</div>
                            <div class="s-cap">{s['시가총액']:,}억</div>
                            <div class="s-price">{s['현재가']}</div>
                            <div class="s-rate {color}">{s['등락률']}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            
            # 2. 거래대금 TOP 5
            st.markdown("""
            <div class="section-title">
                <div>💰 거래대금 상위 TOP 5 <span style="font-size:0.9rem; color:#666; font-weight:400;">(돈이 몰리는 곳)</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            top_vol = df.sort_values(by='총거래대금', ascending=False).head(5)
            
            for idx, row in top_vol.iterrows():
                vol_eok = row['총거래대금'] // 100
                with st.container():
                    st.markdown(f"""
                    <div class="theme-box">
                        <div style="overflow:hidden; margin-bottom:10px;">
                            <span class="theme-name">{row['테마명']}</span>
                            <span class="theme-stat" style="color:#1A237E;">총 {vol_eok:,}억 거래</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    for i, s in enumerate(row['구성종목']):
                        color = "up" if s['등락률'] > 0 else "down"
                        leader = "<span class='tag-leader'>대장주</span>" if i == 0 else ""
                        st.markdown(f"""
                        <div class="stock-row">
                            <div class="s-name">{s['종목명']}{leader}</div>
                            <div class="s-cap">{s['시가총액']:,}억</div>
                            <div class="s-price">{s['현재가']}</div>
                            <div class="s-rate {color}">{s['등락률']}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
