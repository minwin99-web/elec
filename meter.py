import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="현장 검침 사진 촬영 앱", layout="wide")

# --- 세션 상태(Session State) 초기화 ---
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'images' not in st.session_state:
    st.session_state.images = {}  # { "301.jpg": bytes, "302.jpg": bytes, ... }
if 'current_floor' not in st.session_state:
    st.session_state.current_floor = 1
if 'current_unit_idx' not in st.session_state:
    st.session_state.current_unit_idx = 0
if 'shooting_complete' not in st.session_state:
    st.session_state.shooting_complete = False

st.title("📱 현장 검침 사진 촬영 시스템")

# ==========================================
# 1. 기초 설정 화면 (등록 전 표시)
# ==========================================
if not st.session_state.setup_complete:
    st.header("1. 검침 대상 및 층/호실 등록")
    
    col1, col2 = st.columns(2)
    with col1:
        dong_num = st.text_input("동 번호 입력 (예: 101)", value="101")
        reading_date = st.date_input("검침일자", datetime.today())
    with col2:
        min_floor = st.number_input("최저 층수 (시작 층)", min_value=1, value=1)
        max_floor = st.number_input("최고 층수 (마지막 층)", min_value=1, value=15)
        
    col3, col4 = st.columns(2)
    with col3:
        start_unit = st.number_input("층별 시작 호실 (예: 1호)", min_value=1, value=1)
    with col4:
        end_unit = st.number_input("층별 최종 호실 (예: 4호)", min_value=1, value=4)

    if st.button("설정 완료 및 촬영 시작", type="primary", use_container_width=True):
        st.session_state.dong_num = dong_num
        st.session_state.reading_date = reading_date.strftime("%Y-%m-%d")
        st.session_state.min_floor = min_floor
        st.session_state.max_floor = max_floor
        st.session_state.start_unit = start_unit
        st.session_state.end_unit = end_unit
        
        # 촬영 상태 초기화
        st.session_state.current_floor = min_floor
        st.session_state.current_unit_idx = 0
        st.session_state.images = {}
        st.session_state.shooting_complete = False
        st.session_state.setup_complete = True
        st.rerun()

# ==========================================
# 2. 촬영 및 다운로드 화면 (등록 후 표시)
# ==========================================
else:
    # 상단 요약 바 및 등록변경 버튼
    with st.expander(f"📌 설정 요약: {st.session_state.dong_num}동 ({st.session_state.min_floor}층 ~ {st.session_state.max_floor}층)", expanded=False):
        st.write(f"**검침일자:** {st.session_state.reading_date} | **호수 범위:** {st.session_state.start_unit}호 ~ {st.session_state.end_unit}호")
        if st.button("등록변경 (처음부터 다시 설정)"):
            st.session_state.setup_complete = False
            st.rerun()
            
    st.divider()

    # --- [A] 촬영 진행 모드 ---
    if not st.session_state.shooting_complete:
        # 현재 층의 전체 호수 리스트 생성 (예: 301, 302, 303, 304)
        current_floor_units = []
        for unit in range(st.session_state.start_unit, st.session_state.end_unit + 1):
            unit_name = f"{st.session_state.current_floor}{unit:02d}"
            current_floor_units.append(unit_name)

        st.header(f"📷 {st.session_state.current_floor}층 촬영 중")
        
        # 아직 현재 층에 촬영할 세대가 남은 경우
        if st.session_state.current_unit_idx < len(current_floor_units):
            target_unit = current_floor_units[st.session_state.current_unit_idx]
            
            st.subheader(f"👉 촬영 대상 호수: {target_unit}호")
            st.caption(f"진행도: {st.session_state.current_unit_idx + 1} / {len(current_floor_units)} 세대")
            
            # 카메라 기능 호출 (각 호실별 고유 key 매핑)
            img_buffer = st.file_uploader(
                f"{target_unit}호 계량기 촬영 버튼", 
                type=['png', 'jpg', 'jpeg'],
                key=f"cam_{target_unit}"
            )
            
            if img_buffer is not None:
                # 파일명을 호수 기준으로 즉시 변경하여 메모리에 저장 (예: 301.jpg)
                file_name_re = f"{target_unit}.jpg"
                st.session_state.images[file_name_re] = img_buffer.getvalue()
                st.success(f"✅ {target_unit}호 사진이 정상 저장되었습니다. ({file_name_re})")
                
                # 다음 세대로 즉시 이동
                st.session_state.current_unit_idx += 1
                st.rerun()
                
        # 현재 층의 모든 세대 촬영이 완료된 경우 (UI 전환 분기점)
        else:
            st.success(f"🎉 {st.session_state.current_floor}층의 모든 세대 촬영이 완료되었습니다!")
            
            # 최고 층 전이라면 다음 층 선택 UI 표시
            if st.session_state.current_floor < st.session_state.max_floor:
                next_floor_num = st.session_state.current_floor + 1
                st.info(f"다음 층인 **{next_floor_num}층** 촬영으로 넘어가시겠습니까?")
                
                if st.button(f"➡️ {next_floor_num}층 선택 및 촬영 계속", type="primary", use_container_width=True):
                    st.session_state.current_floor = next_floor_num
                    st.session_state.current_unit_idx = 0  # 세대 인덱스 초기화
                    st.rerun()
            # 최고 층의 최종 세대까지 촬영이 전부 끝난 경우
            else:
                st.balloons()
                st.success("🏁 최상층 최종 세대까지 모든 촬영이 종료되었습니다!")
                if st.button("💾 전체 사진 압축 및 다운로드 준비", type="primary", use_container_width=True):
                    st.session_state.shooting_complete = True
                    st.rerun()

    # --- [B] 촬영 종료 및 PC 다운로드 모드 ---
    if st.session_state.shooting_complete:
        st.header("💾 PC 다운로드 센터")
        st.write("스마트폰에서 순서대로 촬영된 파일들이 호수명으로 변환 완료되었습니다. PC로 전송할 압축팩을 다운로드하세요.")
        
        # 1. 사진 파일들을 ZIP으로 압축하는 로직
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for f_name, f_bytes in st.session_state.images.items():
                zip_file.writestr(f_name, f_bytes)
        zip_data = zip_buffer.getvalue()
        
        # 2. 호수별 검침량을 입력할 수 있는 기초 엑셀 파일 생성
        excel_results = []
        for f_name in sorted(st.session_state.images.keys()):
            unit_number = f_name.replace(".jpg", "")
            excel_results.append({
                "동": f"{st.session_state.dong_num}동",
                "호수": f"{unit_number}호",
                "검침일자": st.session_state.reading_date,
                "당월지침(PC입력용)": ""
            })
        df = pd.DataFrame(excel_results)
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='검침기록부')
        excel_data = excel_buffer.getvalue()

        # 다운로드 버튼 배치
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            st.download_button(
                label="📦 1. 호수별 변환 사진 다운로드 (ZIP)",
                data=zip_data,
                file_name=f"{st.session_state.dong_num}동_검침사진_{st.session_state.reading_date}.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
        with col_down2:
            st.download_button(
                label="📊 2. 호수별 검침 엑셀파일 다운로드 (XLSX)",
                data=excel_data,
                file_name=f"{st.session_state.dong_num}동_검침기록부_{st.session_state.reading_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
        st.success("위의 두 파일을 PC로 내려받아 매칭 및 마감 작업을 진행하시면 됩니다.")
