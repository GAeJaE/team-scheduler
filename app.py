import streamlit as st
from supabase import create_client
from datetime import datetime, date, time
import hashlib
from streamlit_calendar import calendar

# 1. 페이지 설정 (반드시 코드 최상단에 위치해야 합니다)
st.set_page_config(page_title="팀 스케줄러", page_icon="📅", layout="wide")

# ==========================================
# 👇 Supabase 연결 설정
# ==========================================
# secrets 설정이 없을 경우를 대비한 기본값 처리
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

# 🎨 작성자별 고유 색상 생성 함수
def get_neon_color(name):
    colors = ["#FF4B4B", "#1C83E1", "#00C0F2", "#FFA421", "#BD6BFF", "#00D4BB", "#FF2B2B", "#21C354"]
    hash_val = int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16)
    return colors[hash_val % len(colors)]

# ⚡ DB 연결 최적화
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"DB 연결 중 오류가 발생했습니다: {e}")
        return None

supabase = init_connection()

if not supabase:
    st.stop()

# ==========================================
# 💡 [핵심] 수정/삭제용 팝업창 (Dialog)
# ==========================================
@st.dialog("✏️ 일정 수정 / 삭제")
def edit_dialog(item):
    s_dt = datetime.fromisoformat(item['start_time'])
    e_dt = datetime.fromisoformat(item['end_time'])
    is_allday = (item['start_time'].endswith("00:00:00") and item['end_time'].endswith("23:59:59"))

    with st.form("edit_form"):
        new_title = st.text_input("내용", value=item['title'])
        new_author = st.text_input("작성자", value=item['author'])
        new_is_allday = st.checkbox("하루 종일", value=is_allday)
        
        c1, c2 = st.columns(2)
        new_start_d = c1.date_input("시작일", value=s_dt.date())
        new_end_d = c2.date_input("종료일", value=e_dt.date())
        
        c3, c4 = st.columns(2)
        if new_is_allday:
            new_start_t = time(0,0)
            new_end_t = time(23,59)
            st.info("하루 종일 일정은 시간이 고정됩니다.")
        else:
            new_start_t = c3.time_input("시작 시간", value=s_dt.time())
            new_end_t = c4.time_input("종료 시간", value=e_dt.time())
            
        col_save, col_del = st.columns([1, 1])
        submitted = col_save.form_submit_button("💾 수정 저장", type="primary", use_container_width=True)
        deleted = col_del.form_submit_button("🗑️ 삭제 하기", type="secondary", use_container_width=True)

        if submitted:
            s_iso = f"{new_start_d}T{new_start_t}"
            e_iso = f"{new_end_d}T{new_end_t}"
            try:
                supabase.table("schedules").update({
                    "title": new_title, "author": new_author, 
                    "start_time": s_iso, "end_time": e_iso
                }).eq("id", item['id']).execute()
                st.toast("수정 완료!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

        if deleted:
            try:
                supabase.table("schedules").delete().eq("id", item['id']).execute()
                st.toast("삭제 완료!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ==========================================
# ➕ [사이드바] 신규 등록
# ==========================================
with st.sidebar:
    st.header("➕ 새 일정 등록")
    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    with st.form(key=f"add_form_{st.session_state.form_key}", clear_on_submit=True):
        title = st.text_input("일정 내용", placeholder="예: 현장 미팅")
        author = st.text_input("작성자", placeholder="이름")
        is_all_day = st.checkbox("하루 종일")
        
        c1, c2 = st.columns(2)
        start_d = c1.date_input("시작 날짜", date.today())
        end_d = c2.date_input("종료 날짜", date.today())
        
        c3, c4 = st.columns(2)
        start_t = c3.time_input("시작 시간", time(9,0))
        end_t = c4.time_input("종료 시간", time(10,0))
        
        if st.form_submit_button("등록 하기", type="primary", use_container_width=True):
            if not title or not author:
                st.error("내용과 이름을 입력해주세요.")
            else:
                s_iso = f"{start_d}T00:00:00" if is_all_day else f"{start_d}T{start_t}"
                e_iso = f"{end_d}T23:59:59" if is_all_day else f"{end_d}T{end_t}"
                
                try:
                    supabase.table("schedules").insert({
                        "title": title, "start_time": s_iso, "end_time": e_iso, "author": author
                    }).execute()
                    st.toast("✅ 등록되었습니다!")
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"에러: {e}")

# ==========================================
# 📅 [메인 화면]
# ==========================================
st.title("📅 팀 스케줄러")

try:
    response = supabase.table("schedules").select("*").execute()
    db_events = response.data
except Exception:
    db_events = []

tab1, tab2 = st.tabs(["🗓️ 월간 달력", "📝 리스트 보기"])

with tab1:
    calendar_events = []
    for evt in db_events:
        color = get_neon_color(evt['author'])
        is_allday = (evt['start_time'].endswith("00:00:00") and evt['end_time'].endswith("23:59:59"))
        calendar_events.append({
            "id": evt['id'],
            "title": f"{evt['title']} ({evt['author']})",
            "start": evt['start_time'],
            "end": evt['end_time'],
            "backgroundColor": color,
            "borderColor": color,
            "allDay": is_allday,
            "extendedProps": evt
        })

    cal_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        "initialView": "dayGridMonth",
        "selectable": True,
    }

    cal_state = calendar(events=calendar_events, options=cal_options, key="main_calendar")

    if cal_state.get("eventClick"):
        clicked_evt = cal_state["eventClick"]["event"]["extendedProps"]
        edit_dialog(clicked_evt)

with tab2:
    selected_date = st.date_input("날짜 필터", date.today())
    daily_list = [e for e in db_events if e['start_time'].startswith(str(selected_date))]
    
    if not daily_list:
        st.info("일정이 없습니다.")
    
    for evt in daily_list:
        with st.container():
            col_txt, col_btn = st.columns([4, 1])
            color = get_neon_color(evt['author'])
            with col_txt:
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding-left: 10px;">
                    <b>{evt['title']}</b> <br>
                    <span style="color:gray; font-size:0.9em;">{evt['author']} | {evt['start_time'][11:16]}~{evt['end_time'][11:16]}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                if st.button("수정/삭제", key=f"btn_{evt['id']}"):
                    edit_dialog(evt)
            st.divider()