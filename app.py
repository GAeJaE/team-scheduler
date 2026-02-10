import streamlit as st
from supabase import create_client
from datetime import datetime, date, time, timedelta
import hashlib
from streamlit_calendar import calendar

# ==========================================
# 👇 Supabase 정보 (보안을 위해 secrets 사용 권장)
# ==========================================
try:
    if "SUPABASE_URL" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    else:
        SUPABASE_URL = "https://ovmwkpogwcayuuzablxx.supabase.co"
        SUPABASE_KEY = "sb_publishable_0Z7HSyptiI5rYAQ1uR56Rw_27V4NnFS"
except:
    SUPABASE_URL = "https://ovmwkpogwcayuuzablxx.supabase.co"
    SUPABASE_KEY = "sb_publishable_0Z7HSyptiI5rYAQ1uR56Rw_27V4NnFS"
# ==========================================

st.set_page_config(page_title="팀 스케줄러", page_icon="📅", layout="wide")

# 🎨 색상 함수
def get_neon_color(name):
    colors = ["#FF4B4B", "#1C83E1", "#00C0F2", "#FFA421", "#BD6BFF", "#00D4BB", "#FF2B2B", "#21C354"]
    hash_val = int(hashlib.sha256(name.encode('utf-8')).hexdigest(), 16)
    return colors[hash_val % len(colors)]

# ⚡ DB 연결
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_connection()
except Exception as e:
    st.error(f"DB 연결 실패: {e}")
    st.stop()

# --- 상태 관리 (수정 모드 진입용) ---
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
    st.session_state.selected_id = None
    st.session_state.form_data = {}

# 초기화 함수
def reset_form():
    st.session_state.edit_mode = False
    st.session_state.selected_id = None
    st.session_state.form_data = {}

# --- [사이드바] 입력 폼 (등록 & 수정 겸용) ---
with st.sidebar:
    if st.session_state.edit_mode:
        st.header("✏️ 일정 수정 / 삭제")
        st.info(f"선택된 일정: {st.session_state.form_data.get('title')}")
    else:
        st.header("➕ 일정 등록")

    default_data = st.session_state.form_data if st.session_state.edit_mode else {}
    
    with st.form("event_form", clear_on_submit=False):
        title = st.text_input("일정 내용", value=default_data.get("title", ""), placeholder="예: 현장 미팅")
        author = st.text_input("작성자", value=default_data.get("author", ""), placeholder="이름")
        is_all_day = st.checkbox("하루 종일", value=default_data.get("all_day", False))
        
        c1, c2 = st.columns(2)
        d_start = default_data.get("start_d", date.today())
        d_end = default_data.get("end_d", date.today())
        t_start = default_data.get("start_t", time(9,0))
        t_end = default_data.get("end_t", time(10,0))

        start_d = c1.date_input("시작 날짜", d_start)
        end_d = c2.date_input("종료 날짜", d_end)
        
        if not is_all_day:
            c3, c4 = st.columns(2)
            start_t = c3.time_input("시작 시간", t_start)
            end_t = c4.time_input("종료 시간", t_end)
        else:
            start_t, end_t = time(0,0), time(23,59)
        
        col_submit, col_cancel = st.columns([1, 1])
        
        if st.session_state.edit_mode:
            submit_label = "수정 완료"
            btn_style = "primary"
        else:
            submit_label = "등록 하기"
            btn_style = "primary"

        submitted = col_submit.form_submit_button(submit_label, type=btn_style)
        
    if st.session_state.edit_mode:
        c_del, c_reset = st.columns(2)
        if c_del.button("🗑️ 삭제하기", use_container_width=True):
            try:
                supabase.table("schedules").delete().eq("id", st.session_state.selected_id).execute()
                st.success("삭제되었습니다.")
                reset_form()
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패: {e}")
                
        if c_reset.button("취소 (새 등록)", use_container_width=True):
            reset_form()
            st.rerun()

    if submitted:
        if not title or not author:
            st.error("내용과 이름을 입력해주세요.")
        else:
            if is_all_day:
                s_iso = f"{start_d}T00:00:00"
                e_iso = f"{end_d}T23:59:59"
            else:
                s_iso = f"{start_d}T{start_t}"
                e_iso = f"{end_d}T{end_t}"

            data = {"title": title, "start_time": s_iso, "end_time": e_iso, "author": author}

            try:
                if st.session_state.edit_mode:
                    supabase.table("schedules").update(data).eq("id", st.session_state.selected_id).execute()
                    st.toast("수정 완료!")
                else:
                    supabase.table("schedules").insert(data).execute()
                    st.toast("등록 완료!")
                
                reset_form()
                st.rerun()
            except Exception as e:
                st.error(f"에러 발생: {e}")

# --- [메인 화면] ---
st.title("📅 팀 스케줄러")

try:
    response = supabase.table("schedules").select("*").execute()
    db_events = response.data
except:
    db_events = []

tab1, tab2 = st.tabs(["🗓️ 월간 달력", "📝 리스트 보기"])

# 1. 캘린더 뷰
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
            "extendedProps": {
                "pure_title": evt['title'],
                "author": evt['author']
            }
        })

    cal_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek"},
        "initialView": "dayGridMonth",
        "selectable": True,
    }

    cal_state = calendar(events=calendar_events, options=cal_options, key="main_calendar")

    if cal_state.get("eventClick"):
        event = cal_state["eventClick"]["event"]
        props = event.get("extendedProps", {})
        
        try: # 👈 에러가 났던 부분: try 뒤에 except를 추가하여 해결했습니다!
            s_dt = datetime.fromisoformat(event["start"])
            if event["end"]:
                e_dt = datetime.fromisoformat(event["end"])
            else:
                e_dt = s_dt
                
            st.session_state.edit_mode = True
            st.session_state.selected_id = event["id"]
            st.session_state.form_data = {
                "title": props.get("pure_title", event["title"]),
                "author": props.get("author", ""),
                "all_day": event.get("allDay", False),
                "start_d": s_dt.date(),
                "end_d": e_dt.date(),
                "start_t": s_dt.time(),
                "end_t": e_dt.time()
            }
            st.rerun()
        except Exception as e:
            st.error(f"일정 정보를 불러오는 중 오류가 발생했습니다: {e}")

# 2. 리스트 뷰
with tab2:
    selected_date = st.date_input("날짜 필터", date.today())
    st.caption("💡 리스트의 '수정' 버튼을 누르면 사이드바에서 내용을 고칠 수 있습니다.")
    
    daily_list = [e for e in db_events if e['start_time'].startswith(str(selected_date))]
    
    if not daily_list:
        st.info("해당 날짜에 일정이 없습니다.")
    
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
                if st.button("수정", key=f"btn_{evt['id']}"):
                    s_dt = datetime.fromisoformat(evt['start_time'])
                    e_dt = datetime.fromisoformat(evt['end_time'])
                    is_allday = (evt['start_time'].endswith("00:00:00") and evt['end_time'].endswith("23:59:59"))
                    
                    st.session_state.edit_mode = True
                    st.session_state.selected_id = evt['id']
                    st.session_state.form_data = {
                        "title": evt['title'],
                        "author": evt['author'],
                        "all_day": is_allday,
                        "start_d": s_dt.date(),
                        "end_d": e_dt.date(),
                        "start_t": s_dt.time(),
                        "end_t": e_dt.time()
                    }
                    st.rerun()
            st.divider()