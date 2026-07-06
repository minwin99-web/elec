import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import io
import zipfile
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="세아프라자 PC 일괄 검침 시스템", layout="wide")

st.title("🖥️ PC 전용 일괄 검침 자동화 시스템")
st.info("현장에서 스마트폰 '기본 카메라'로 연속 촬영한 사진들을 PC로 옮긴 후, 이곳에 한 번에 업로드하여 호수 매칭과 엑셀 마감을 진행합니다.")

# ==========================================
# 1. 단지 및 검침 범위 설정
# ==========================================
st.subheader("1. 검침 범위 설정")
col1, col2 = st.columns(2)
with col1:
    dong_num = st.text_input("동 번호 (예: 101)", value="101")
    reading_date = st.date_input("검침일자", datetime.today())
with col2:
    min_floor = st.number_input("시작 층", min_value=1, value=3)
    max_floor = st.number_input("종료 층", min_value=1, value=18)

col3, col4 = st.columns(2)
with col3:
    start_unit = st.number_input("층별 시작 호라인", min_value=1, value=1)
with col4:
    end_unit = st.number_input("층별 최종 호라인", min_value=1, value=15)

# 설정된 범위에 따라 예상되는 전체 호수 리스트 생성
expected_units = []
for floor in range(min_floor, max_floor + 1):
    for unit in range(start_unit, end_unit + 1):
        expected_units.append(f"{floor}{unit:02d}호")

st.write(f"📌 **예상 세대 수:** 총 {len(expected_units)}가구 ({expected_units[0]} ~ {expected_units[-1]})")
st.divider()

# ==========================================
# 2. 사진 일괄 업로드 및 자동 매칭
# ==========================================
st.subheader("2. 사진 업로드 및 데이터 추출")
uploaded_files = st.file_uploader(
    "스마트폰에서 PC로 옮긴 검침 사진을 모두 선택하여 아래에 끌어다 놓으세요.",
    type=['png', 'jpg', 'jpeg'],
    accept_multiple_files=True
)

if uploaded_files:
    st.write(f"📁 업로드된 사진 수: **{len(uploaded_files)}장**")
    
    # 누락/중복 촬영 검증
    if len(uploaded_files) != len(expected_units):
        st.warning(f"⚠️ 주의: 설정된 예상 세대 수({len(expected_units)}가구)와 업로드된 사진 수({len(uploaded_files)}장)가 일치하지 않습니다. 순서가 밀릴 수 있으니 확인이 필요합니다.")
    
    if st.button("🚀 사진 호수 자동 매칭 및 검침(OCR) 시작", type="primary", use_container_width=True):
        # 파일 이름 순으로 정렬 (스마트폰 촬영 순서를 정확히 보장하기 위함)
        sorted_files = sorted(uploaded_files, key=lambda x: x.name)
        
        results = []
        renamed_images = {} # ZIP 저장용 메모리 딕셔너리
        
        progress_text = "사진 매칭 및 숫자 인식 중..."
        my_bar = st.progress(0, text=progress_text)
        
        # 파일 수와 세대 수 중 작은 값만큼만 반복하여 오류 방지
        total_process = min(len(expected_units), len(sorted_files))
        
        for i in range(total_process):
            target_ho = expected_units[i]
            file = sorted_files[i]
            
            # [핵심 로직] 사진 파일 이름을 대상 호수 이름으로 변경
            renamed_filename = f"{dong_num}동_{target_ho}.jpg"
            img_bytes = file.getvalue()
            renamed_images[renamed_filename] = img_bytes
            
            # OCR 숫자 추출 진행
            try:
                image = Image.open(io.BytesIO(img_bytes))
                custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.'
                extracted_text = pytesseract.image_to_string(image, config=custom_config).strip()
            except Exception:
                extracted_text = "인식실패"
                
            results.append({
                "동": f"{dong_num}동",
                "호수": target_ho,
                "검침일자": reading_date.strftime("%Y-%m-%d"),
                "당월지침": extracted_text
            })
            
            # 진행률 표시 업데이트
            my_bar.progress((i + 1) / total_process, text=f"{target_ho} 처리 완료... ({i+1}/{total_process})")
            
        # 추출 완료된 데이터를 세션에 저장하여 다운로드 준비
        st.session_state.final_data = pd.DataFrame(results)
        st.session_state.renamed_images = renamed_images
        st.success("✅ 모든 파일명 변경 및 데이터 추출이 완료되었습니다!")

# ==========================================
# 3. 결과 확인 및 최종 다운로드
# ==========================================
if 'final_data' in st.session_state and not st.session_state.final_data.empty:
    st.divider()
    st.subheader("3. 검침 결과 확인 및 다운로드")
    st.info("아래 표에서 인식 오류가 난 숫자를 클릭하여 직접 수정한 후 다운로드하세요.")
    
    # 데이터 에디터 출력
    edited_df = st.data_editor(st.session_state.final_data, use_container_width=True, num_rows="dynamic")
    
    # 1. 엑셀 파일 생성
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='당월검침')
    excel_data = excel_buffer.getvalue()
    
    # 2. 이름이 변경된 사진 압축(ZIP) 파일 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for f_name, f_bytes in st.session_state.renamed_images.items():
            zip_file.writestr(f_name, f_bytes)
    zip_data = zip_buffer.getvalue()

    # 다운로드 버튼 배치
    col_down1, col_down2 = st.columns(2)
    with col_down1:
        st.download_button(
            label="📊 1. 최종 검침기록 엑셀 다운로드",
            data=excel_data,
            file_name=f"세아프라자_전기검침_{dong_num}동_{reading_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
    with col_down2:
        st.download_button(
            label="📦 2. 호수별로 이름이 바뀐 사진 보관용(ZIP) 다운로드",
            data=zip_data,
            file_name=f"세아프라자_검침사진_{dong_num}동_{reading_date}.zip",
            mime="application/zip",
            use_container_width=True
        )
