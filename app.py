import streamlit as st
import re
import pdfplumber
from docx import Document

# --- 1. 配色與樣式定義 ---
st.set_page_config(page_title="Liberlive Pro - Brett", layout="wide")

# 定義顏色標籤 (要求 10)
def get_colored_html(chord):
    # 邏輯: 如果是 G/B，抓前面那個 G
    main_chord = chord.split('/')[0]
    first_char = main_chord[0].upper()
    
    color_map = {
        'A': '#1D4ED8', # 10-1 深藍色 (六級)
        'F': '#22C55E', # 10-2 綠色 (四級)
        'E': '#EAB308', # 10-3 黃色 (三級)
        'G': '#3B82F6', # 10-4 藍色 (五級)
        'C': '#EF4444', # 10-5 紅色 (一級)
        'D': '#F97316', # 10-6 橘色 (二級)
        'B': '#A855F7'  # 10-7 紫色 (七級)
    }
    color = color_map.get(first_char, "#333333") # 沒匹配到則用深灰色
    return f'<span style="color:{color}; font-weight:bold; font-size:1.1em;">[{chord}]</span>'

# --- 2. 移調邏輯 ---
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

# --- 3. 介面設計 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.info("編程者: Brett | 版本: v3.7")

st.title("Liberlive 智能轉譜系統")

# 調性選擇
c1, c2 = st.columns(2)
with c1:
    orig_key = st.selectbox("🎼 原曲調性", KEYS, index=0)
with c2:
    target_key = st.selectbox("🎹 目標調性 (C2)", KEYS, index=0)

# 輸入區
manual_text = st.text_area("✍️ 請貼上帶有中括號 [和弦] 的歌詞：", height=200)

if st.button("🚀 執行智能轉換"):
    if manual_text:
        steps = (KEYS.index(target_key) - KEYS.index(orig_key)) % 12
        
        # 第一步：移調處理 (保留中括號)
        def process_match(match):
            c = match.group(1)
            if '/' in c:
                return "/".join([transpose_chord(p.strip(), steps) for p in c.split('/')])
            return transpose_chord(c, steps)
        
        # 移調後的純文本
        transposed_text = re.sub(r'\[([^\]]+)\]', process_match, manual_text)
        
        # 第二步：上色處理 (轉為 HTML)
        # 我們要把 [C] 變成 <span style="color:red">[C]</span>
        final_html = re.sub(r'\[([^\]]+)\]', lambda m: get_colored_html(m.group(1)), transposed_text)

        # 顯示結果
        st.subheader("✅ 最終 Liberlive 彩色譜")
        
        # 關鍵在於這個 unsafe_allow_html=True
        st.markdown(f'''
            <div style="background-color: #F0F4F8; padding: 25px; border-radius: 12px; border: 1px solid #D1D5DB; line-height: 2.2; font-family: monospace; white-space: pre-wrap;">
                {final_html}
            </div>
            ''', unsafe_allow_html=True)
        
        # 下載功能 (純文本版供貼入 App)
        st.download_button("💾 下載純文本譜 (供貼入 App)", transposed_text, file_name=f"Brett_Score_{target_key}.txt")
    else:
        st.error("請先輸入內容！")
