import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import RGBColor, Pt
import io
import json
import datetime

# --- 1. 核心顏色規範 (和弦顯色邏輯不變) ---
CHORD_COLORS = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive AI Pro - Brett", layout="wide")

# 初始化 Session (持久化數據)
if 'my_library' not in st.session_state: st.session_state.my_library = {}
if 'edit_buffer' not in st.session_state: st.session_state.edit_buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""

# --- 2. UI 配色注入 (藍/綠/黃/白風格) ---
st.markdown("""
    <style>
    /* 全域背景與文字 */
    .stApp { background-color: #F8FAFC; }
    
    /* 側邊欄樣式 (藍/白) */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; color: white !important; }
    section[data-testid="stSidebar"] .stMarkdown p { color: white !important; }
    
    /* 分頁標籤與按鈕樣式 (藍/綠/黃) */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 10px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: white !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #22C55E !important; border-radius: 5px; }
    
    div.stButton > button:first-child { 
        background-color: #22C55E; color: white; border-radius: 8px; border: none;
        padding: 10px 24px; font-weight: bold; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #15803D; border: none; }
    
    /* 和弦顯色 CSS */
    .c-A { color: #1D4ED8 !important; font-weight: bold; } .c-F { color: #22C55E !important; font-weight: bold; }
    .c-E { color: #EAB308 !important; font-weight: bold; } .c-G { color: #3B82F6 !important; font-weight: bold; }
    .c-C { color: #EF4444 !important; font-weight: bold; } .c-D { color: #F97316 !important; font-weight: bold; }
    .c-B { color: #A855F7 !important; font-weight: bold; }
    
    /* 樂譜容器 (白底) */
    .output-container { 
        background: white; padding: 45px; line-height: 3.2; font-size: 1.6em; 
        white-space: pre-wrap; border-radius: 15px; border: 2px solid #CBD5E1; 
        color: #334155; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); 
    }
    
    /* 段落標籤與鼓機 */
    .section-header { 
        background: #FDE047; color: #1E3A8A; padding: 8px 15px; 
        border-radius: 5px; font-weight: bold; margin: 20px 0 10px 0;
        border-left: 8px solid #1E3A8A;
    }
    .drum-tag { background: #1E3A8A; color: white !important; padding: 2px 10px; border-radius: 4px; font-weight: bold; font-size: 0.8em; }
    
    /* 演出模式 (深藍/白/彩色) */
    .perf-mode { background-color: #0F172A !important; color: #F8FAFC !important; font-size: 2.6em !important; line-height: 3.8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯處理 ---
def transpose_logic(chord, steps):
    if any(x in chord for x in ['Intro', 'Verse', 'Chorus', 'Bridge', 'Drum']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    lookup = [k if k not in ['Db','Eb','Gb','Ab','Bb'] else {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[k] for k in KEYS]
    norm_map = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
    r = norm_map.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_html(text):
    # 處理標籤
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-header">📍 \1</div>', text)
    text = re.sub(r'\[\[Drum:([^\]]+)\]\]', r'<span class="drum-tag">🥁 \1</span>', text)
    # 處理和弦變色
    parts = re.split(r'(\[[^\]]+\])', text)
    res, cur_cls = "", ""
    for p in parts:
        if p.startswith('[') and p.endswith(']'):
            if 'div' in p or 'drum-tag' in p: res += p; continue
            char = p.split('/')[0][1].upper()
            cur_cls = f"c-{char}"
            res += f'<span class="{cur_cls}">{p}'
        else:
            res += f'{p}</span>' if cur_cls else p
    return res

# --- 4. 介面呈現 ---
st.sidebar.title("🎹 Brett Pro v14.4")
mode = st.sidebar.radio("⏱️ 模式切換", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動", 0, 15, 0)
st.sidebar.markdown("---")

if mode == "演出模式":
    st.markdown(f'<div class="output-container perf-mode">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
else:
    st.title("🎸 Liberlive 智能影音工作站")
    
    with st.expander("🎼 音樂參數設定", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: ok = st.selectbox("原曲調性", KEYS)
        with c2: tk = st.selectbox("目標調性 (C2)", KEYS, index=6) # 預設轉 G
        with c3: bpm = st.number_input("BPM 速度", 40, 240, 90)

    t1, t2, t3 = st.tabs(["🎵 智能轉譜", "🎬 影音練習", "📁 曲庫管理"])

    with t1:
        song_title = st.text_input("歌曲名稱", "New Song")
        raw_in = st.text_area("輸入歌詞與和弦 (可直接貼上有譜麼網址)", height=150, value=st.session_state.edit_buffer)
        
        if st.button("🚀 執行智能轉換"):
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.edit_buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_logic(m.group(1), steps), raw_in)
            st.rerun()

        if st.session_state.edit_buffer:
            st.session_state.edit_buffer = st.text_area("✍️ 編輯與微調", value=st.session_state.edit_buffer, height=300)
            st.markdown(f'<div class="output-container">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
            
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("⭐ 收藏至個人曲庫"):
                    st.session_state.my_library[song_title] = {
                        "content": st.session_state.edit_buffer,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.success(f"已存入曲庫：{song_title}")
            with sc2:
                # Word 導出邏輯...
                st.download_button("💾 下載彩色 Word", "file_data", f"{song_title}.docx")

    with t2:
        st.session_state.yt_url = st.text_input("貼上 YouTube 影片網址", value=st.session_state.yt_url)
        if st.session_state.yt_url:
            st.video(st.session_state.yt_url)
        st.markdown(f'<div class="output-container">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)

    with t3:
        if not st.session_state.my_library:
            st.warning("曲庫是空的，趕快去轉一首歌吧！")
        else:
            for name, data in st.session_state.my_library.items():
                col_n, col_a = st.columns([4, 1])
                col_n.info(f"🎵 {name} | {data['date']}")
                if col_a.button(f"載入", key=f"lib_{name}"):
                    st.session_state.edit_buffer = data['content']
                    st.rerun()

# 滾動控制
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
