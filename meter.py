import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import io
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="스마트폰 전기검침 앱", layout="wide")

# 세션 상태(Session State) 초기화 - 화면이 새로고침되어도 데이터 유지
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'units_list' not in st.session_state:
    st.session_state.units_list = []
if 'readings_data' not in st.session_state:
    st.session_state.readings_data = {} # 형식: {"동-호": {"검침일자": date, "지침": value}}
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0

st.title("📱 세대 전기계량기 스마트폰 검침")

# 기능별로 탭 분리
tab1, tab2, tab3 = st.tabs(["1. 기초 설정 (동/호수)", "2. 사진 촬영 및 검침", "3. 마감 및 다운로드"])

# --- TAB 1: 기초 설정 ---
with tab1:
    st.header("단지 및 세대 설정")
    col1, col2 = st.columns(2)
    with col1:
        dong_num = st.text_input("동 번호 입력 (예: 101)")
        reading_date = st.date_input("검침일자", datetime.today())
    with col2:
        max_floor = st.number_input("최고 층수", min_value=1, value=15)
        units_per_floor = st.number_input("층당 세대수", min_value=1, value=2)

    if st.button("세대 생성 및 설정 완료"):
        units = []
        for floor in range(1, max_floor + 1):
            for unit in range(1, units_per_floor + 1):
                unit_num = f"{floor}{unit:02d}"
                units.append(f"{dong_num}동 {unit_num}호")
        
        st.session_state.units_list = units
        st.session_state.setup_complete = True
        st.session_state.reading_date = reading_date.strftime("%Y-%m-%d")
        st.success(f"총 {len(units)}세대 리스트가 생성되었습니다. '사진 촬영' 탭으로 이동하세요.")

# --- TAB 2: 촬영 및 OCR ---
with tab2:
    st.header("계량기 사진 촬영")
    if not st.session_state.setup_complete:
        st.warning("먼저 '기초 설정' 탭에서 세대 설정을 완료해주세요.")
    else:
        # 촬영할 세대 선택 (선택 변경 시 기존 저장 데이터는 안전하게 유지됨)
        selected_unit = st.selectbox(
            "검침할 세대 선택 (저장 후 자동으로 다음 세대로 넘어갑니다)",
            st.session_state.units_list,
            index=st.session_state.current_index
        )

        # 스마트폰 카메라 호출
        # 스마트폰 기본 카메라 앱 호출 (후면 카메라 기본 작동)
        img_file_buffer = st.file_uploader(f"📷 {selected_unit} 계량기 촬영 (터치하여 '카메라' 선택)", type=['png', 'jpg', 'jpeg'])

        if img_file_buffer is not None:
            image = Image.open(img_file_buffer)
            
            # --- OCR 숫자 추출 ---
            try:
                # 숫자와 마침표만 인식하도록 환경 설정
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.'
                extracted_text = pytesseract.image_to_string(image, config=custom_config).strip()
                
                if extracted_text:
                    # 데이터 저장
                    st.session_state.readings_data[selected_unit] = {
                        "검침일자": st.session_state.reading_date,
                        "검침수치": extracted_text
                    }
                    st.success(f"✅ {selected_unit} 저장 완료: {extracted_text}")
                    
                    # 자동으로 다음 호수로 이동
                    current_idx = st.session_state.units_list.index(selected_unit)
                    if current_idx < len(st.session_state.units_list) - 1:
                        st.session_state.current_index = current_idx + 1
                        st.rerun() # 화면 새로고침
                    else:
                        st.info("🎉 모든 세대 검침이 완료되었습니다. 마감 탭으로 이동하세요.")
                else:
                    st.error("숫자를 인식하지 못했습니다. 다시 촬영하거나 수동으로 입력해주세요.")
            except Exception as e:
                st.error(f"OCR 처리 중 오류 발생: {e}")

        # OCR 실패 시 수동 입력 창 제공
        st.markdown("---")
        manual_input = st.text_input("수동 입력 (빛 반사 등으로 인식 실패 시)")
        if st.button("수동 저장 및 다음 세대 이동"):
            if manual_input:
                st.session_state.readings_data[selected_unit] = {
                    "검침일자": st.session_state.reading_date,
                    "검침수치": manual_input
                }
                st.success(f"수동 저장 완료: {manual_input}")
                current_idx = st.session_state.units_list.index(selected_unit)
                if current_idx < len(st.session_state.units_list) - 1:
                    st.session_state.current_index = current_idx + 1
                    st.rerun()

# --- TAB 3: 마감 및 다운로드 ---
with tab3:
    st.header("검침 마감 및 엑셀 다운로드")
    if not st.session_state.readings_data:
        st.info("아직 저장된 검침 데이터가 없습니다.")
    else:
        # 딕셔너리 데이터를 데이터프레임으로 변환
        df_data = []
        for unit, data in st.session_state.readings_data.items():
            dong, ho = unit.split("동 ")
            ho = ho.replace("호", "")
            df_data.append({
                "동": dong,
                "호수": ho,
                "검침일자": data["검침일자"],
                "당월지침": float(data["검침수치"]) if data["검침수치"].replace('.','',1).isdigit() else data["검침수치"]
            })
        df = pd.DataFrame(df_data)
        
        st.dataframe(df, use_container_width=True)

        # 엑셀 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='검침데이터')
        
        excel_data = output.getvalue()

        st.download_button(
            label="📁 마감 (엑셀 다운로드)",
            data=excel_data,
            file_name=f"전기검침_{st.session_state.reading_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )
