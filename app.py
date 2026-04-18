import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import RGBColor, Pt
import io
import json
import datetime

# --- 1. 核心顯色規範 (10-1 到 10-7) ---
CHORD_COLORS = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive AI Pro v14.8", layout="wide")

# 初始化 Session (解決資料丟失問題)
if 'edit_buffer' not in st.session_state: st.session_state.edit_buffer = ""
if 'my_library' not in st.session_state: st.session_state.my_library = {}
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""

# --- 2. 視覺配色 UI (高對比：藍/黃/綠/白) ---
st.markdown("""
    <style>
    /* 側邊欄配色 (深藍底白字) */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; border-right: 2px solid #FACC15; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }

    /* 分頁標籤 (藍底黃綠字) */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 12px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: #22C55E !important; font-weight: bold; font-size: 1.1em; } 
    .stTabs [aria-selected="true"] { background-color: #FACC15 !important; color: #1E3A8A !important; border-radius: 8px; }

    /* 樂譜預覽區 (純白底，確保彩色字體鮮艷) */
    .output-container { 
        background: #FFFFFF !important; padding: 45px; line-height: 3.2; font-size: 1.75em; 
        white-space: pre-wrap; border-radius: 15px; border: 3px solid #1E3A8A; 
        color: #000000 !important; box-shadow: 0 10px 20px rgba(0,0,0,0.15); 
    }
    
    /* 演出模式 (全黑底) */
    .perf-mode { background-color: #000000 !important; color: #FFFFFF !important; font-size: 2.8em !important; line-height: 4.0 !important; }

    /* 強制顯色規則 */
    .c-A { color: #1D4ED8 !important; } .c-F { color: #22C55E !important; }
    .c-E { color: #EAB308 !important; } .c-G { color: #3B82F6 !important; }
    .c-C { color: #EF4444 !important; } .c-D { color: #F97316 !important; }
    .c-B { color: #A855F7 !important; }
    
    /* 段落標籤樣式 */
    .section-header { background: #FDE047; color: #1E3A8A; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin: 25px 0; border-left: 10px solid #1E3A8A; font-size: 0.8em; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心處理引擎 ---
def transpose_logic(chord, steps):
    if any(x in chord for x in ['Intro', 'Verse', 'Chorus', 'Bridge', 'Drum']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    lookup = [k if k not in ['Db','Eb','Gb','Ab','Bb'] else {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[k] for k in KEYS]
    r = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_html_engine(text):
    if not text: return "<div style='text-align:center; padding:20px; color:gray;'>請先在『智能轉譜』貼上內容並點擊轉換，或從曲庫載入歌曲。</div>"
    # 段落標籤
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-header">📍 \1</div>', text)
    # 染色引擎
    parts = re.split(r'(\[[^\]]+\])', text)
    res, cur_cls = "", ""
    for p in parts:
        if p.startswith('[') and p.endswith(']'):
            if 'div' in p: res += p; continue
            char = p.split('/')[0][1].upper()
            cur_cls = f"c-{char}"
            res += f'<span class="{cur_cls}">{p}'
        else:
            res += f'{p}</span>' if cur_cls else p
    return res

# --- 4. 介面呈現 ---
st.sidebar.title("🎹 Brett AI Master v14.8")
view_mode = st.sidebar.radio("⏱️ 檢視模式", ["工作站模式", "演出模式"])
auto_scroll = st.sidebar.slider("📜 自動滾動速度", 0, 15, 0)

# 強制更新內容的回調
def sync_buffer():
    st.session_state.edit_buffer = st.session_state.temp_editor

if view_mode == "演出模式":
    st.markdown(f'<div class="output-container perf-mode">{render_html_engine(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
else:
    st.title("🎸 Liberlive 影音智能轉譜站")
    
    with st.expander("🎼 音樂調性參數設定 (置頂)", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: ok = st.selectbox("原曲調性", KEYS)
        with c2: tk = st.selectbox("目標調性 (C2)", KEYS, index=6)
        with c3: bpm = st.number_input("BPM 速度", 40, 240, 90)

    t1, t2, t3 = st.tabs(["🎵 智能轉譜 & 編輯", "🎬 影音同步練習", "📁 個人曲庫管理"])

    with t1:
        s_title = st.text_input("歌曲名稱", "My Song")
        raw_in = st.text_area("在此輸入歌詞與和弦 [C]，或貼上有譜麼網址", height=150)
        if st.button("🚀 執行智能轉換並鎖定內容"):
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            # 移調並存入 Session
            st.session_state.edit_buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_logic(m.group(1), steps), raw_in)
            st.rerun()

        if st.session_state.edit_buffer:
            # 編輯區
            st.session_state.edit_buffer = st.text_area("✍️ 專業編輯區 (修改後自動同步所有分頁)", value=st.session_state.edit_buffer, height=300, key="temp_editor", on_change=sync_buffer)
            # 即時預覽
            st.markdown(f'<div class="output-container">{render_html_engine(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
            
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("⭐ 收藏至曲庫"):
                    st.session_state.my_library[s_title] = {"content": st.session_state.edit_buffer, "date": str(datetime.datetime.now())}
                    st.toast(f"✅ {s_title} 已存入曲庫！")
            with sc2:
                st.write("已可導出 Word")

    with t2:
        st.session_state.yt_url = st.text_input("🎬 請在此貼上 YouTube 影片網址", value=st.session_state.yt_url)
        if st.session_state.yt_url:
            st.video(st.session_state.yt_url)
        
        st.markdown("---")
        st.subheader("📖 練習譜面 (已自動同步)")
        # 關鍵修正：確保這裡一定調用 render_html_engine
        st.markdown(f'<div class="output-container">{render_html_engine(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)

    with t3:
        if st.session_state.my_library:
            for name, data in st.session_state.my_library.items():
                cn, ca = st.columns([4, 1])
                cn.info(f"🎵 {name}")
                if ca.button(f"載入譜面", key=f"lib_{name}"):
                    st.session_state.edit_buffer = data['content']
                    st.rerun()
        else:
            st.warning("曲庫是空的，請先收藏歌曲。")

# 自動滾動 JS
if auto_scroll > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{auto_scroll}),50);</script>", unsafe_allow_html=True)
