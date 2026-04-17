import streamlit as st
import re
import pdfplumber
from docx import Document
import io

# --- 1. 介面與配色設定 ---
st.set_page_config(page_title="Liberlive Pro - Brett Edition", layout="wide")

st.markdown("""
    <style>
    .c-red { color: #EF4444; font-weight: bold; }
    .c-orange { color: #F97316; font-weight: bold; }
    .c-yellow { color: #EAB308; font-weight: bold; }
    .c-green { color: #22C55E; font-weight: bold; }
    .c-blue { color: #3B82F6; font-weight: bold; }
    .c-darkblue { color: #1D4ED8; font-weight: bold; }
    .c-purple { color: #A855F7; font-weight: bold; }
    .output-box { background-color: #F8FAFC; padding: 25px; border-radius: 12px; border: 1px solid #E2E8F0; line-height: 2.2; font-family: 'Courier New', monospace; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心邏輯：移調與顏色 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def transpose_chord(chord, steps):
    match = re.match(r"([A-G][#b]?)", chord)
    if not match: return chord
    root = match.group(1)
    suffix = chord[len(root):]
    norm_keys = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
    lookup_keys = [norm_keys.get(k, k) for k in KEYS]
    root = norm_keys.get(root, root)
    if root in lookup_keys:
        new_idx = (lookup_keys.index(root) + steps) % 12
        return KEYS[new_idx] + suffix
    return chord

def get_colored_html(chord_text):
    # 邏輯 10: 抓取前面第一個字母 (處理 G/B 之類的複合和弦)
    first_char = chord_text[0].upper()
    color_map = {
        'A': 'c-darkblue', 'F': 'c-green', 'E': 'c-yellow', 
        'G': 'c-blue', 'C': 'c-red', 'D': 'c-orange', 'B': 'c-purple'
    }
    cls = color_map.get(first_char, "")
    return f'<span class="{cls}">[{chord_text}]</span>'

# --- 3. 不同格式文件讀取 (要求 1) ---
def handle_file_upload(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    return None

# --- 4. UI 介面 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.markdown("**版本:** v3.5 (全格式支援)")
st.sidebar.markdown("**編程者:** Brett")

st.title("Liberlive 智能轉譜系統")

# 要求 3: 調性功能
c1, c2 = st.columns(2)
with c1:
    orig_key = st.selectbox("🎼 原曲調性", KEYS, index=0)
with c2:
    target_key = st.selectbox("🎹 目標調性 (C2)", KEYS, index=0)

# 要求 1: 格式輸入
uploaded_file = st.file_uploader("📁 上傳譜面 (TXT, PDF, Word, 或圖片)", type=['txt', 'pdf', 'docx', 'png', 'jpg'])
manual_text = st.text_area("✍️ 直接貼上文字內容：", height=150)

if st.button("🚀 開始智能轉換"):
    content = ""
    if uploaded_file:
        content = handle_file_upload(uploaded_file)
        if not content and uploaded_file.type in ["image/png", "image/jpeg"]:
            st.warning("目前圖片建議先手動轉為文字。若需自動識別圖片，請聯繫開發者串接 OCR API。")
    else:
        content = manual_text

    if content:
        # 計算移調步數
        steps = (KEYS.index(target_key) - KEYS.index(orig_key)) % 12
        
        # 步驟 2: 先轉成正確調性的和弦譜
        def process_chord(match):
            chord = match.group(1)
            if '/' in chord:
                return "/".join([transpose_chord(p.strip(), steps) for p in chord.split('/')])
            return transpose_chord(chord, steps)
        
        # 移調後的純文本
        transposed_text = re.sub(r'\[([^\]]+)\]', process_chord, content)
        
        # 輸出帶有顏色的 HTML
        final_html = re.sub(r'\[([^\]]+)\]', lambda m: get_colored_html(m.group(1)), transposed_text)

        st.subheader("✅ 最終 Liberlive 和弦 + 詞")
        st.markdown(f'<div class="output-box">{final_html}</div>', unsafe_allow_html=True)
        
        # 下載按鈕 (這就是你的雲端存儲解決方案)
        st.download_button(
            label="💾 下載轉換結果 (TXT)",
            data=transposed_text,
            file_name=f"Brett_Score_{target_key}.txt",
            mime="text/plain"
        )
    else:
        st.error("請提供輸入內容！")
