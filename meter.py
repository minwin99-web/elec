import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import io
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="동두천 세아프라자 전기검침", layout="wide")

# --- 세션 상태(Session State) 초기화 ---
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'images' not in st.session_state:
    st.session_state.images = {} # 촬영된 사진을 세대명으로 메모리에 임시 저장
if 'current_floor' not in st.session_state:
    st.session_state.current_floor = 1
if 'current_unit_idx' not in st.session_state:
    st.session_state.current_unit_idx = 0
if 'ocr_done' not in st.session_state:
    st.session_state.ocr_done = False
if 'final_data' not in st.session_state:
    st.session_state.final_data = pd.DataFrame()

st.title("🏢 동두천 세아프라자 전기검침")

# ==========================================
# 1. 기초 설정 화면 (설정 완료 시 숨김 처리)
# ==========================================
if not st.session_state.setup_complete:
    st.header("1. 단지 및 층/호실 설정")
    st.info("설정을 완료하면 이 화면은 사라지며, 본격적인 촬영 모드로 진입합니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        dong_num = st.text_input("동 번호 입력 (예: 101)", value="101")
        reading_date = st.date_input("검침일자", datetime.today())
    with col2:
        min_floor = st.number_input("최저 층수 (시작 층)", min_value=1, value=1)
        max_floor = st.number_input("최고 층수 (마지막 층)", min_value=1, value=15)
        
    col3, col4 = st.columns(2)
    with col3:
        start_unit = st.number_input("층별 시작 호실 번호 (예: 1호)", min_value=1, value=1)
    with col4:
        end_unit = st.number_input("층별 최종 호실 번호 (예: 4호)", min_value=1, value=4)

    if st.button("설정 완료 및 촬영 시작", type="primary", use_container_width=True):
        st.session_state.dong_num = dong_num
        st.session_state.reading_date = reading_date.strftime("%Y-%m-%d")
        st.session_state.min_floor = min_floor
        st.session_state.max_floor = max_floor
        st.session_state.start_unit = start_unit
        st.session_state.end_unit = end_unit
        
        # 촬영 시작 위치 초기화
        st.session_state.current_floor = min_floor
        st.session_state.current_unit_idx = 0
        st.session_state.setup_complete = True
        st.rerun()

# ==========================================
# 2. 촬영 및 일괄 처리 화면 (설정 완료 후 표시)
# ==========================================
else:
    # --- 설정 요약 및 등록변경(수정) 버튼 ---
    with st.expander(f"📌 현재 설정: {st.session_state.dong_num}동 ({st.session_state.min_floor}층 ~ {st.session_state.max_floor}층)", expanded=False):
        st.write(f"**검침일자:** {st.session_state.reading_date} | **호라인:** {st.session_state.start_unit}호 ~ {st.session_state.end_unit}호")
        if st.button("등록변경 (설정 수정)"):
            st.session_state.setup_complete = False
            st.rerun()
            
    st.divider()

    # --- 촬영 모드 (OCR 진행 전) ---
    if not st.session_state.ocr_done:
        # 현재 층의 전체 세대 리스트 생성
        current_floor_units = []
        for unit in range(st.session_state.start_unit, st.session_state.end_unit + 1):
            unit_str = f"{st.session_state.current_floor}{unit:02d}호"
            current_floor_units.append(unit_str)

        st.header(f"📷 {st.session_state.current_floor}층 촬영 진행")
        
        # 현재 층의 촬영이 남아있는 경우
        if st.session_state.current_unit_idx < len(current_floor_units):
            target_unit = current_floor_units[st.session_state.current_unit_idx]
            full_unit_name = f"{st.session_state.dong_num}동 {target_unit}"
            
            st.subheader(f"👉 대상: {full_unit_name} ({st.session_state.current_unit_idx + 1} / {len(current_floor_units)})")
            
            # 카메라 위젯 (각 호수마다 고유 key를 부여하여 충돌 방지)
            img_buffer = st.file_uploader(
                "아래 버튼을 눌러 카메라로 계량기를 촬영하세요.", 
                type=['png', 'jpg', 'jpeg'], 
                key=f"cam_{st.session_state.current_floor}_{target_unit}"
            )
            
            if img_buffer is not None:
                # 사진을 세대번호명으로 세션에 저장 (나중에 일괄 처리)
                st.session_state.images[full_unit_name] = img_buffer.getvalue()
                st.success(f"{full_unit_name} 사진 저장 완료!")
                
                # 다음 호수로 인덱스 이동
                st.session_state.current_unit_idx += 1
                st.rerun()
                
        # 현재 층의 모든 세대 촬영이 끝난 경우
        else:
            st.success(f"✅ {st.session_state.current_floor}층의 모든 세대({len(current_floor_units)}가구) 촬영이 완료되었습니다.")
            
            if st.session_state.current_floor < st.session_state.max_floor:
                st.info(f"다음 층({st.session_state.current_floor + 1}층) 촬영을 시작하시겠습니까?")
                if st.button(f"{st.session_state.current_floor + 1}층 촬영 시작", type="primary"):
                    st.session_state.current_floor += 1
                    st.session_state.current_unit_idx = 0
                    st.rerun()
            else:
                st.balloons()
                st.success("🎉 지정하신 최고 층까지 모든 단지의 촬영이 종료되었습니다!")
                if st.button("📸 촬영 종료 및 일괄 검침(OCR) 시작", type="primary", use_container_width=True):
                    st.session_state.ocr_done = True
                    st.rerun()

    # --- OCR 일괄 처리 및 엑셀 다운로드 모드 ---
    if st.session_state.ocr_done:
        st.header("📊 데이터 변환 및 마감")
        
        # 아직 데이터프레임이 생성되지 않았다면 일괄 OCR 수행
        if st.session_state.final_data.empty and len(st.session_state.images) > 0:
            st.write("저장된 사진을 읽어 숫자를 추출하고 있습니다...")
            progress_bar = st.progress(0)
            
            results = []
            total_images = len(st.session_state.images)
            
            # 저장된 이미지를 순회하며 OCR 분석
            for i, (unit_name, img_bytes) in enumerate(st.session_state.images.items()):
                try:
                    image = Image.open(io.BytesIO(img_bytes))
                    # 숫자와 소수점만 인식하도록 설정
                    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.'
                    extracted_text = pytesseract.image_to_string(image, config=custom_config).strip()
                except Exception:
                    extracted_text = "인식실패"
                
                dong, ho = unit_name.split("동 ")
                results.append({
                    "동": dong,
                    "호수": ho.replace("호", ""),
                    "검침일자": st.session_state.reading_date,
                    "당월지침": extracted_text
                })
                progress_bar.progress((i + 1) / total_images)
                
            st.session_state.final_data = pd.DataFrame(results)
            st.success("모든 사진의 데이터 변환이 완료되었습니다!")

        # 추출된 데이터 수정 및 확인 (Streamlit 데이터 에디터 활용)
        if not st.session_state.final_data.empty:
            st.info("표 안의 셀을 터치하여 인식 오류가 있는 숫자를 직접 수정할 수 있습니다.")
            edited_df = st.data_editor(st.session_state.final_data, use_container_width=True, num_rows="dynamic")
            
            # 엑셀 다운로드 버튼
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False, sheet_name='당월검침')
            excel_data = output.getvalue()

            st.download_button(
                label="📁 최종 검침데이터 엑셀 다운로드",
                data=excel_data,
                file_name=f"세아프라자_전기검침_{st.session_state.dong_num}동_{st.session_state.reading_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
