import streamlit as st
import re
import os
import io

# --- 介面設定 ---
st.set_page_config(page_title="Liberlive Pro - Brett Edition", layout="wide")

# 自定義 CSS
st.markdown("""
    <style>
    .chord-red { color: #EF4444; font-weight: bold; }
    .chord-orange { color: #F97316; font-weight: bold; }
    .chord-yellow { color: #EAB308; font-weight: bold; }
    .chord-green { color: #22C55E; font-weight: bold; }
    .chord-blue { color: #3B82F6; font-weight: bold; }
    .chord-darkblue { color: #1D4ED8; font-weight: bold; }
    .chord-purple { color: #A855F7; font-weight: bold; }
    .output-box { 
        background-color: #F8FAFC; 
        padding: 20px; 
        border: 2px solid #E2E8F0;
        border-radius: 10px;
        line-height: 2.0;
        font-family: monospace;
        white-space: pre-wrap;
    }
    </style>
    """, unsafe_allow_html=True)

def get_chord_html(chord_text):
    first_char = chord_text[0].upper()
    color_map = {'C':'chord-red','D':'chord-orange','E':'chord-yellow','F':'chord-green','G':'chord-blue','A':'chord-darkblue','B':'chord-purple'}
    cls = color_map.get(first_char, "")
    return f'<span class="{cls}">[{chord_text}]</span>'

# --- 側邊欄 ---
st.sidebar.title("🎸 Brett Music Tech")
st.sidebar.markdown("**版本:** v3.1 (下載增強版)")
st.sidebar.markdown("**編程者:** Brett")

# --- 主介面 ---
st.title("Liberlive 智能轉譜系統")

manual_text = st.text_area("請貼上帶有中括號和弦的歌詞：", height=200, placeholder="[C]天空[G]晴朗...")

if st.button("✨ 執行轉換"):
    if manual_text:
        # 顏色處理邏輯
        pattern = r'\[([^\]]+)\]'
        converted_html = re.sub(pattern, lambda m: get_chord_html(m.group(1)), manual_text)
        
        # 1. 顯示預覽
        st.subheader("🎵 轉換結果預覽")
        st.markdown(f'<div class="output-box">{converted_html}</div>', unsafe_allow_html=True)
        
        # 2. 提供下載按鈕 (解決看不到檔案的問題)
        st.subheader("💾 儲存檔案")
        st.download_button(
            label="點我下載轉譜結果 (TXT)",
            data=manual_text,
            file_name="liberlive_song_brett.txt",
            mime="text/plain"
        )
        st.success("轉換完成！你可以點擊上方按鈕下載檔案到你的設備。")
    else:
        st.error("請輸入內容")
