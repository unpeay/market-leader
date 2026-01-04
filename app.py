import streamlit as st
import random

# ==========================================
# 1. 페이지 설정 및 CSS 스타일링 (KT 멤버십 스타일 적용)
# ==========================================
st.set_page_config(
    page_title="종가베팅 Pro - 마켓 리더",
    page_icon="📈",
    layout="wide"
)

# KT 멤버십 스타일의 커스텀 CSS 적용
st.markdown("""
<style>
    /* 전체 배경 및 폰트 설정 */
    .stApp {
        background-color: #f4f6f9; /* 밝은 회색 배경 */
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* 메인 타이틀 스타일 */
    .main-title {
        font-size: 2rem;
        font-weight: 800;
        color: #222;
        margin-bottom: 1rem;
        padding-left: 10px;
        border-left: 5px solid #e74c3c; /* 포인트 컬러 (붉은색 계열) */
    }

    /* 테마 컨테이너 박스 스타일 */
    .theme-box {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); /* 부드러운 그림자 */
    }

    /* 테마 헤더 스타일 */
    .theme-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    .theme-icon { margin-right: 8px; }

    /* 개별 종목 카드 스타일 */
    .stock-card {
        background-color: #fdfdfd;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .stock-card:hover {
        border-color: #e74c3c;
        transform: translateY(-2px);
    }

    /* 카드 상단 정보행 스타일 */
    .card-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        font-weight: 600;
        font-size: 1rem;
    }
    .stock-name { font-size: 1.1rem; font-weight: 700; }
    .rank-badge { margin-right: 5px; }

    /* 등락률 컬러 */
    .rate-up { color: #e74c3c; } /* 상승 - 빨강 */
    .rate-down { color: #3498db; } /* 하락 - 파랑 */

    /* 등급 뱃지 */
    .grade-badge-S { background-color: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; }
    .grade-badge-A { background-color: #f39c12; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; }

    /* 마감강도 바 */
    .strength-bar { color: #e74c3c; letter-spacing: -2px; }

    /* 하단 상세 정보 텍스트 스타일 (요청하신 레이아웃) */
    .sub-info-text {
        font-size: 0.9rem;
        color: #555;
        line-height: 1.5;
        margin-top: 4px;
    }
    .ai-flow { font-weight: bold; color: #333; }
    .news-link { text-decoration: none; color: #333; font-weight: 500; }
    .news-link:hover { color: #e74c3c; text-decoration: underline; }
    .trend-data { font-family: monospace; font-weight: 600; color: #333; }
    .trend-comment { color: #e74c3c; font-weight: bold; font-size: 0.85rem; }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 더미 데이터 생성 함수 (실제 API 연동 시 교체)
# ==========================================
def get_mock_theme_data():
    """화면 구성을 위한 임시 데이터 반환"""
    data = {
        "HBM (고대역폭메모리)": [
            {
                "rank": "🥇대장", "name": "한미반도체", "rate": 15.2, "rate_type": "up", "grade": "S급",
                "strength": "▮▮▮▮▮▮▮▮▮▮",
                "reasons": ["꽉찬양봉", "쌍끌이", "주도주", "👑신고가 돌파!"],
                "ai_flow": "매수 우위 (지속) ↗️",
                "news_title": "[특징주] 한미반도체, 엔비디아 공급 확대 기대감에 급등...",
                "foreign": "[+30, +15, -5, +20, +10]", "foreign_cmt": "오늘 3만주 매수중",
                "inst": "[+50, +20, +10, -5, -2]"
            },
            {
                "rank": "🥈2등", "name": "SK하이닉스", "rate": 4.5, "rate_type": "up", "grade": "A급",
                "strength": "▮▮▮▮▮▮▮▮▯▯",
                "reasons": ["외인대량매수", "전고점 돌파 시도"],
                "ai_flow": "매수세 유입 중 ↗️",
                "news_title": "SK하이닉스, HBM 시장 독주 체제 굳히나",
                "foreign": "[+100, +50, +20, -10, +30]", "foreign_cmt": "",
                "inst": "[+20, -10, +5, +5, +10]"
            },
            {
                "rank": "🥉3등", "name": "이수페타시스", "rate": 2.1, "rate_type": "up", "grade": "B급",
                "strength": "▮▮▮▮▮▯▯▯▯▯",
                "reasons": ["기관 수급 개선", "눌림목 반등"],
                "ai_flow": "관망세 ➡️",
                "news_title": "이수페타시스, AI 서버용 기판 수요 증가 전망",
                "foreign": "[-10, -5, -2, +5, +8]", "foreign_cmt": "",
                "inst": "[+5, +10, +15, +2, -1]"
            },
        ],
        "초전도체 / 신소재": [
             {
                "rank": "🥇대장", "name": "신성델타테크", "rate": 21.5, "rate_type": "up", "grade": "S급",
                "strength": "▮▮▮▮▮▮▮▮▮▮",
                "reasons": ["거래량 폭발", "테마 대장주 탈환"],
                "ai_flow": "강력 매수 신호 🔥",
                "news_title": "LK-99 관련 새로운 논문 발표 기대감에 강세",
                "foreign": "[-5, -10, +2, +50, +10]", "foreign_cmt": "장막판 급매수 유입",
                "inst": "[0, 0, 0, +5, +2]"
            },
             {
                "rank": "🥈2등", "name": "서남", "rate": -3.2, "rate_type": "down", "grade": "C급",
                "strength": "▮▮▯▯▯▯▯▯▯▯",
                "reasons": ["차익실현 매물", "단기 과열"],
                "ai_flow": "매도 우위 (주의) ↘️",
                "news_title": "서남, 단기 급등에 따른 피로감... 하락 전환",
                "foreign": "[+10, +5, -10, -20, -15]", "foreign_cmt": "",
                "inst": "[+1, +1, -1, -5, -2]"
            },
              {
                "rank": "🥉3등", "name": "파워로직스", "rate": 1.5, "rate_type": "up", "grade": "B급",
                "strength": "▮▮▮▮▯▯▯▯▯▯",
                "reasons": ["기술적 반등", "대장주 추종"],
                "ai_flow": "중립 ➡️",
                "news_title": "초전도체 테마 내 순환매 흐름",
                "foreign": "[-2, -1, 0, +3, +5]", "foreign_cmt": "",
                "inst": "[0, 0, 0, 0, 0]"
            },
        ]
    }
    return data

# ==========================================
# 3. UI 컴포넌트 함수 (종목 카드 렌더링)
# ==========================================
def render_stock_card(stock_data):
    """개별 종목 데이터를 받아 카드 형태로 렌더링하는 함수"""
    s = stock_data
    
    # 등락률 부호 및 스타일 결정
    rate_sign = "+" if s["rate_type"] == "up" else ""
    rate_emoji = "🔥" if s["rate"] >= 10 and s["rate_type"] == "up" else ("💧" if s["rate_type"] == "down" else "🔺")
    
    # 등급 뱃지 스타일 결정
    grade_class = f"grade-badge-{s['grade'][0]}"

    # 외인 코멘트 처리
    f_cmt = f" <- {s['foreign_cmt']}" if s['foreign_cmt'] else ""

    st.markdown(f"""
    <div class="stock-card">
        <div class="card-top-row">
            <div>
                <span class="rank-badge">{s['rank']}</span>
                <span class="stock-name">{s['name']}</span>
            </div>
            <div>
                <span class="rate-{s['rate_type']}">{rate_emoji}{rate_sign}{s['rate']}%</span>
                <span class="{grade_class}">{s['grade']}</span>
                <span style="margin-left: 10px; font-size: 0.9rem;">강도: <span class="strength-bar">{s['strength']}</span></span>
            </div>
        </div>

        <div class="sub-info-text">
            <div>
                {' '.join([f'#{r}' for r in s['reasons']])} <span class="ai-flow">🤖흐름: {s['ai_flow']}</span>
            </div>
            <div style="margin-top: 5px;">
                └ 📰 <a href="#" class="news-link">{s['news_title']}</a>
            </div>
            <div>
                └ 👽외인(5일): <span class="trend-data">{s['foreign']}</span><span class="trend-comment">{f_cmt}</span>
            </div>
            <div>
                └ 🏦기관(5일): <span class="trend-data">{s['inst']}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. 메인 애플리케이션 실행 로직
# ==========================================
def main():
    # 메인 타이틀
    st.markdown('<div class="main-title">📈 오늘의 종가베팅 테마</div>', unsafe_allow_html=True)
    st.write("장 마감 기준, 가장 강력한 수급과 모멘텀을 보여준 테마별 Top 3 종목입니다.")

    # 데이터 가져오기
    theme_data = get_mock_theme_data()
    theme_icons = ["📦", "⚡", "🤖", "💊"] # 테마별 아이콘 예시

    # 각 테마별로 반복하여 UI 구성
    for idx, (theme_name, stocks) in enumerate(theme_data.items()):
        icon = theme_icons[idx % len(theme_icons)]
        
        # 테마 컨테이너 시작
        st.markdown(f"""
        <div class="theme-box">
            <div class="theme-header">
                <span class="theme-icon">{icon}</span> [{theme_name}] 섹터
            </div>
        """, unsafe_allow_html=True)

        # 해당 테마의 상위 3개 종목 카드 렌더링
        for stock in stocks[:3]: # Top 3만 표시
            render_stock_card(stock)
        
        # 테마 컨테이너 종료
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
