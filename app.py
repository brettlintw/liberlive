import streamlit as st
import re

# --- 介面設定 ---
st.set_page_config(page_title="Liberlive Pro - Brett Edition", layout="wide")

# 定義調性索引
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

# 移調函數
def transpose_chord(chord, steps):
    # 提取根音 (例如 Am7 提取 A)
    match = re.match(r"([A-G][#b]?)", chord)
    if not match: return chord
    root = match.group(1)
    suffix = chord[len(root):]
    
    # 標準化根音 (如 Eb 轉為 D# 來計算)
    norm_keys = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
    lookup_keys = [norm_keys.get(k, k) for k in KEYS]
    root = norm_keys.get(root, root)
    
    if root in lookup_keys:
        current_idx = lookup_keys.index(root)
        new_idx = (current_idx + steps) % 12
        return KEYS[new_idx] + suffix
    return chord

# 顏色邏輯 (要求 10)
def get_chord_html(chord_text):
    first_char = chord_text[0].upper()
    color_map = {'C':'#EF4444','D':'#F97316','E':'#EAB308','F':'#22C55E','G':'#3B82F6','A':'#1D4ED8','B':'#A855F7'}
    color = color_map.get(first_char, "#000000")
    return f'<span style="color:{color}; font-weight:bold;">[{chord_text}]</span>'

# --- 介面 CSS ---
st.markdown("""
    <style>
    .output-box { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; line-height: 2; font-family: monospace; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.markdown("**版本:** v3.2 (移調+下載版)")
st.sidebar.markdown("**編程者:** Brett")

# --- 主畫面 ---
st.title("Liberlive 智能轉譜系統")

# 要求 9: 調性功能
col1, col2 = st.columns(2)
with col1:
    orig_key = st.selectbox("🎼 原曲調性", KEYS, index=0)
with col2:
    target_key = st.selectbox("🎹 目標調性 (Liberlive)", KEYS, index=0)

manual_text = st.text_area("請貼上帶有中括號和弦的歌詞：", height=200, placeholder="[C]天空[G]晴朗...")

if st.button("✨ 執行移調與轉換"):
    if manual_text:
        # 計算位移步數
        steps = (KEYS.index(target_key) - KEYS.index(orig_key)) % 12
        
        # 處理邏輯：先移調，再上色
        def process_match(match):
            original_chord = match.group(1)
            # 處理複合和弦如 G/B
            if '/' in original_chord:
                parts = original_chord.split('/')
                transposed = "/".join([transpose_chord(p, steps) for p in parts])
            else:
                transposed = transpose_chord(original_chord, steps)
            return transposed

        # 得到移調後的純文本 (用來下載)
        final_plain_text = re.sub(r'\[([^\]]+)\]', process_match, manual_text)
        
        # 得到帶 HTML 顏色的預覽
        final_html = re.sub(r'\[([^\]]+)\]', lambda m: get_chord_html(m.group(1)), final_plain_text)

        st.subheader("🎵 轉換結果預覽")
        st.markdown(f'<div class="output-box">{final_html}</div>', unsafe_allow_html=True)
        
        # 下載功能 (解決找不到檔案的問題)
        st.download_button(
            label="💾 下載轉換後的歌譜 (TXT)",
            data=final_plain_text,
            file_name=f"brett_score_{target_key}_key.txt",
            mime="text/plain"
        )
    else:
        st.error("請輸入內容")
