import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import RGBColor, Pt
import io
import json
import datetime

# --- 1. 樣式與核心定義 (10-1 到 10-7) ---
COLOR_RULES = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive AI Workstation v14.2", layout="wide")

# 初始化 Session State 防止刷新丟失數據
if 'my_library' not in st.session_state: st.session_state.my_library = {}
if 'edit_buffer' not in st.session_state: st.session_state.edit_buffer = ""

# CSS 注入：全畫面、變色、段落與鼓機樣式
st.markdown("""
    <style>
    .c-A { color: #1D4ED8 !important; font-weight: bold; } .c-F { color: #22C55E !important; font-weight: bold; }
    .c-E { color: #EAB308 !important; font-weight: bold; } .c-G { color: #3B82F6 !important; font-weight: bold; }
    .c-C { color: #EF4444 !important; font-weight: bold; } .c-D { color: #F97316 !important; font-weight: bold; }
    .c-B { color: #A855F7 !important; font-weight: bold; }
    .drum-tag { background: #333; color: #fff !important; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }
    .section-anchor { background: #F1F5F9; border-left: 6px solid #1E3A8A; padding: 12px; margin: 18px 0; font-weight: bold; color: #1E3A8A; border-radius: 0 8px 8px 0; }
    .output-container { background: white; padding: 45px; border-radius: 15px; border: 1px solid #E2E8F0; line-height: 3.0; font-size: 1.6em; white-space: pre-wrap; color: #333; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .perf-mode { background-color: #000 !important; color: #FFF !important; font-size: 2.6em !important; line-height: 3.8 !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心邏輯處理 ---

def transpose_logic(chord, steps):
    """精確移調引擎，自動排除段落標籤"""
    if any(tag in chord for tag in ['Intro', 'Verse', 'Chorus', 'Bridge', 'Outro', 'Drum']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    norm = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
    lookup = [norm.get(k, k) for k in KEYS]; r = norm.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_final_html(text):
    """全功能渲染：段落、鼓機、彩色歌詞"""
    # 處理段落標籤
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-anchor">📍 \1</div>', text)
    # 處理鼓機標籤
    text = re.sub(r'\[\[Drum:([^\]]+)\]\]', r'<span class="drum-tag">🥁 \1</span>', text)
    
    parts = re.split(r'(\[[^\]]+\])', text)
    res, cur_cls = "", ""
    for p in parts:
        if p.startswith('[') and p.endswith(']'):
            if 'class=' in p or 'drum-tag' in p: # 已被段落或鼓機處理過
                res += p; continue
            char = p.split('/')[0][1].upper()
            cur_cls = f"c-{char}"
            res += f'<span class="{cur_cls}" title="Liberlive C2: {p}">{p}'
        else:
            res += f'{p}</span>' if cur_cls else p
    return res

def export_docx_master(text, title):
    """專業 Word 導出：保留顏色、加粗與排版"""
    doc = Document(); doc.add_heading(title, 0); p = doc.add_paragraph()
    parts = re.split(r'(\[\[Drum:[^\]]+\]\]|\[[^\]]+\])', text)
    cur_rgb = None
    for part in parts:
        if part.startswith('[[Drum:'):
            run = p.add_run(f" 🥁 {part[7:-2]} "); run.bold = True; run.font.size = Pt(11)
        elif part.startswith('[') and part.endswith(']'):
            char = part.split('/')[0][1].upper()
            cur_rgb = COLOR_RULES.get(char, (0,0,0))
            run = p.add_run(part); run.bold = True; run.font.color.rgb = RGBColor(*cur_rgb)
        else:
            run = p.add_run(part)
            if cur_rgb: run.font.color.rgb = RGBColor(*cur_rgb)
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- 3. 介面呈現 ---

st.sidebar.title("🎸 Brett AI Station v14.2")
mode = st.sidebar.radio("模式選擇", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動速度", 0, 15, 0)
st.sidebar.markdown("---")

if mode == "演出模式":
    st.markdown(f'<div class="output-container perf-mode">{render_final_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
else:
    st.title("Liberlive 智能影音工作站")
    
    # 音樂參數
    col1, col2, col3 = st.columns(3)
    with col1: ok = st.selectbox("原曲調性", KEYS)
    with col2: tk = st.selectbox("目標調性", KEYS, index=0)
    with col3: bpm = st.number_input("BPM 速度", 40, 240, 90)
    
    tab_edit, tab_sync, tab_lib = st.tabs(["🎵 智能轉譜", "🎬 影音練習", "💾 曲庫管理"])
    
    with tab_edit:
        raw_in = st.text_area("在此輸入/貼上內容或有譜麼網址", height=150, value=st.session_state.edit_buffer)
        if st.button("🚀 執行智能轉換"):
            # 移調邏輯
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.edit_buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_logic(m.group(1), steps), raw_in)
            st.rerun()

        if st.session_state.edit_buffer:
            final_txt = st.text_area("專業編輯區", value=st.session_state.edit_buffer, height=350)
            st.session_state.edit_buffer = final_txt
            st.markdown(f'<div class="output-container">{render_final_html(final_txt)}</div>', unsafe_allow_html=True)
            
            # 導出與收藏
            d1, d2 = st.columns(2)
            with d1: 
                if st.button("⭐ 加入收藏曲庫"):
                    st.session_state.my_library[datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] = {"content": final_txt}
                    st.toast("已加入收藏！")
            with d2: 
                st.download_button("💾 導出彩色 Word", export_docx_master(final_txt, "Liberlive Score"), "Score.docx")

# JavaScript 自動滾動控制 (Bug Fix: 速度切換不再累加)
if scroll_spd > 0:
    st.markdown(f"""
        <script>
        if(window.scrollInterval) clearInterval(window.scrollInterval);
        window.scrollInterval = setInterval(() => window.scrollBy(0, {scroll_spd}), 50);
        </script>
        """, unsafe_allow_html=True)
