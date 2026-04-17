import streamlit as st
import re
import pdfplumber
from docx import Document
from PIL import Image

# --- 1. 介面設定與 CSS 注入 ---
st.set_page_config(page_title="Liberlive Pro - Brett", layout="wide")

# 強制注入 CSS 樣式確保顏色類別存在
st.markdown("""
    <style>
    .chord-A { color: #1D4ED8 !important; font-weight: bold; }
    .chord-F { color: #22C55E !important; font-weight: bold; }
    .chord-E { color: #EAB308 !important; font-weight: bold; }
    .chord-G { color: #3B82F6 !important; font-weight: bold; }
    .chord-C { color: #EF4444 !important; font-weight: bold; }
    .chord-D { color: #F97316 !important; font-weight: bold; }
    .chord-B { color: #A855F7 !important; font-weight: bold; }
    .output-container { 
        background-color: #F0F4F8; 
        padding: 25px; 
        border-radius: 12px; 
        line-height: 2.2; 
        font-family: 'Courier New', monospace; 
        white-space: pre-wrap;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 顏色邏輯函數 (要求 10) ---
def apply_color_html(text):
    # 正則表達式匹配 [Chord]
    pattern = r'\[([^\]]+)\]'
    
    def replace_with_html(match):
        chord = match.group(1)
        # 處理 G/B，抓第一個字母
        first_char = chord.split('/')[0][0].upper()
        # 對應 10-1 到 10-7 的顏色類別
        return f'<span class="chord-{first_char}">[{chord}]</span>'
    
    return re.sub(pattern, replace_with_html, text)

# --- 3. 移調邏輯 (要求 9) ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

def transpose_chord(chord, steps):
    match = re.match(r"([A-G][#b]?)", chord)
    if not match: return chord
    root, suffix = match.group(1), chord[len(match.group(1)):]
    norm = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
    lookup = [norm.get(k, k) for k in KEYS]
    root = norm.get(root, root)
    if root in lookup:
        new_idx = (lookup.index(root) + steps) % 12
        return KEYS[new_idx] + suffix
    return chord

# --- 4. 多格式讀取 (要求 7) ---
def extract_text_from_file(file):
    if file.type == "text/plain":
        return file.read().decode("utf-8")
    elif file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(file)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file.type in ["image/png", "image/jpeg"]:
        st.warning("📸 偵測到圖片！目前的雲端環境建議先使用手機 OCR 功能轉為文字貼入，或待後續串接 Google OCR API。")
        return ""
    return ""

# --- 5. UI 介面 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.markdown("**編程者:** Brett | **版本:** v4.0")

st.title("Liberlive 智能轉譜系統")

# 調性選擇
c1, c2 = st.columns(2)
with c1: orig_key = st.selectbox("🎼 原曲調性", KEYS, index=0)
with c2: target_key = st.selectbox("🎹 目標調性 (C2)", KEYS, index=0)

# 輸入區
uploaded_file = st.file_uploader("📁 上傳譜面 (文字, PDF, Word, 圖片)", type=['txt', 'pdf', 'docx', 'png', 'jpg'])
manual_text = st.text_area("✍️ 直接貼上文字內容：", height=150)

if st.button("🚀 執行智能轉換"):
    raw_content = extract_text_from_file(uploaded_file) if uploaded_file else manual_text
    
    if raw_content:
        steps = (KEYS.index(target_key) - KEYS.index(orig_key)) % 12
        
        # 移調處理
        def process_match(match):
            c = match.group(1)
            if '/' in c:
                return "/".join([transpose_chord(p.strip(), steps) for p in c.split('/')])
            return transpose_chord(c, steps)
        
        transposed_text = re.sub(r'\[([^\]]+)\]', process_match, raw_content)
        
        # 加上顏色標籤
        colored_html = apply_color_html(transposed_text)

        st.subheader("✅ 最終 Liberlive 彩色譜")
        # 關鍵：使用 HTML 容器封裝
        st.write(f'<div class="output-container">{colored_html}</div>', unsafe_allow_html=True)
        
        st.download_button("💾 下載純文本譜 (貼入 App)", transposed_text, file_name=f"Brett_{target_key}.txt")
    else:
        st.error("請提供輸入內容！")
