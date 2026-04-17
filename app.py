import streamlit as st
import re
import pdfplumber
from docx import Document

# --- 1. 介面設定 ---
st.set_page_config(page_title="Liberlive Pro - Brett Edition", layout="wide")

# --- 2. 核心邏輯：調性索引 ---
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

# --- 3. 顏色規則邏輯 (關鍵修正區) ---
def get_colored_html(chord_text):
    # 規則 1.1: 碰到 G/B 抓前面那個 G
    main_chord = chord_text.split('/')[0]
    # 抓取首字母進行顏色匹配
    first_char = main_chord[0].upper()
    
    color_map = {
        'A': '#1D4ED8', # 10-1 深藍色
        'F': '#22C55E', # 10-2 綠色
        'E': '#EAB308', # 10-3 黃色
        'G': '#3B82F6', # 10-4 藍色
        'C': '#EF4444', # 10-5 紅色
        'D': '#F97316', # 10-6 橘色
        'B': '#A855F7'  # 10-7 紫色
    }
    color = color_map.get(first_char, "#000000") # 沒匹配到則黑色
    
    # 這裡使用 <span> 標籤並直接寫入 style
    return f'<span style="color:{color}; font-weight:bold; font-size:1.1em;">[{chord_text}]</span>'

# --- 4. 檔案處理 ---
def handle_file_upload(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        doc = Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

# --- 5. UI 介面 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.markdown("**編程者:** Brett | **版本:** v3.6")

st.title("Liberlive 智能轉譜系統")

col1, col2 = st.columns(2)
with col1:
    orig_key = st.selectbox("🎼 原曲調性", KEYS, index=0)
with col2:
    target_key = st.selectbox("🎹 目標調性 (C2)", KEYS, index=0)

uploaded_file = st.file_uploader("📁 上傳譜面 (TXT, PDF, Word)", type=['txt', 'pdf', 'docx'])
manual_text = st.text_area("✍️ 或直接貼上文字：", height=150)

if st.button("🚀 執行轉換並顯色"):
    content = handle_file_upload(uploaded_file) if uploaded_file else manual_text
    
    if content:
        steps = (KEYS.index(target_key) - KEYS.index(orig_key)) % 12
        
        # 步驟 A: 先進行移調處理
        def transpose_match(match):
            c = match.group(1)
            if '/' in c:
                return "/".join([transpose_chord(p.strip(), steps) for p in c.split('/')])
            return transpose_chord(c, steps)
        
        transposed_text = re.sub(r'\[([^\]]+)\]', transpose_match, content)
        
        # 步驟 B: 將移調後的和弦轉為彩色 HTML (核心修復：直接在標籤內上色)
        # 我們使用一個特殊預留字元來防止 HTML 標籤被 escape
        final_display_html = re.sub(r'\[([^\]]+)\]', lambda m: get_colored_html(m.group(1)), transposed_text)

        st.subheader("✅ 最終 Liberlive 彩色譜預覽")
        # 關鍵：使用 unsafe_allow_html=True 讓顏色生效
        st.markdown(f'''
            <div style="background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; line-height: 2.2; font-family: monospace; white-space: pre-wrap;">
                {final_display_html}
            </div>
            ''', unsafe_allow_html=True)
        
        # 下載按鈕 (純文字版供 App 使用)
        st.download_button("💾 下載純文字譜 (供貼入 App)", transposed_text, file_name=f"Brett_{target_key}.txt")
    else:
        st.error("請輸入內容！")
