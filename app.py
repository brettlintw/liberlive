import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import RGBColor, Pt
import io
import json
import datetime

# --- 1. 核心顏色規範 (和弦 10-1 到 10-7) ---
CHORD_COLORS = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive AI Pro - Brett", layout="wide")

# 初始化 Session (確保數據永不丟失)
if 'edit_buffer' not in st.session_state: st.session_state.edit_buffer = ""
if 'my_library' not in st.session_state: st.session_state.my_library = {}
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""

# --- 2. 視覺配色 UI (藍底/黃綠標籤/白底紅字) ---
st.markdown("""
    <style>
    /* 全域背景 */
    .stApp { background-color: #F8FAFC; }
    
    /* 側邊欄配色 (深藍底白字) */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }

    /* 分頁標籤配色 (藍/綠/黃) */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 10px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { color: #22C55E !important; font-weight: bold; } /* 綠色標籤 */
    .stTabs [aria-selected="true"] { background-color: #FACC15 !important; color: #1E3A8A !important; border-radius: 5px; } /* 選中變黃色 */

    /* 樂譜容器 (純白底，確保彩色字體明顯) */
    .output-container { 
        background: #FFFFFF !important; padding: 45px; line-height: 3.2; font-size: 1.7em; 
        white-space: pre-wrap; border-radius: 15px; border: 3px solid #CBD5E1; 
        color: #1E293B; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); 
    }
    
    /* 演出模式 (深藍底/白字/大字) */
    .perf-mode { background-color: #0F172A !important; color: #F8FAFC !important; font-size: 2.6em !important; line-height: 3.8 !important; }

    /* 和弦顯色 (強制顏色) */
    .c-A { color: #1D4ED8 !important; font-weight: bold; } .c-F { color: #22C55E !important; font-weight: bold; }
    .c-E { color: #EAB308 !important; font-weight: bold; } .c-G { color: #3B82F6 !important; font-weight: bold; }
    .c-C { color: #EF4444 !important; font-weight: bold; } .c-D { color: #F97316 !important; font-weight: bold; }
    .c-B { color: #A855F7 !important; font-weight: bold; }
    
    /* 段落標籤 (黃底藍字) */
    .section-header { background: #FDE047; color: #1E3A8A; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin: 25px 0; border-left: 10px solid #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯處理 ---
def transpose_logic(chord, steps):
    if any(x in chord for x in ['Intro', 'Verse', 'Chorus', 'Drum']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    lookup = [k if k not in ['Db','Eb','Gb','Ab','Bb'] else {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[k] for k in KEYS]
    r = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_html_master(text):
    if not text: return "<p style='text-align:center; color:#64748B;'>尚無樂譜內容，請輸入或載入曲目</p>"
    # 處理標籤
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-header">📍 \1</div>', text)
    # 處理彩色文字核心引擎
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

def export_docx_master(text, title):
    doc = Document(); doc.add_heading(title, 0); p = doc.add_paragraph()
    parts = re.split(r'(\[[^\]]+\])', text)
    cur_rgb = None
    for part in parts:
        if part.startswith('[') and part.endswith(']'):
            char = part.split('/')[0][1].upper()
            cur_rgb = CHORD_COLORS.get(char, (0,0,0))
            run = p.add_run(part); run.bold = True
        else: run = p.add_run(part)
        if cur_rgb: run.font.color.rgb = RGBColor(*cur_rgb)
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- 4. 介面呈現 ---
st.sidebar.title("🎹 Brett AI v14.7")
mode = st.sidebar.radio("⏱️ 模式選擇", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動", 0, 15, 0)

# 強制更新 Buffer
def update_buffer():
    st.session_state.edit_buffer = st.session_state.temp_editor

if mode == "演出模式":
    st.markdown(f'<div class="output-container perf-mode">{render_html_master(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
else:
    st.title("🎸 Liberlive 智能影音工作站")
    
    with st.expander("🎼 音樂參數設定", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: ok = st.selectbox("原曲調性", KEYS)
        with c2: tk = st.selectbox("目標調性", KEYS, index=6)
        with c3: bpm = st.number_input("BPM 速度", 40, 240, 90)

    t1, t2, t3 = st.tabs(["🎵 智能轉譜", "🎬 影音練習", "📁 曲庫管理"])

    with t1:
        s_title = st.text_input("歌曲名稱", "New Song")
        raw_in = st.text_area("輸入歌詞與 [和弦]", height=150)
        if st.button("🚀 開始智能移調並顯色"):
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.edit_buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_logic(m.group(1), steps), raw_in)
            st.rerun()

        if st.session_state.edit_buffer:
            st.text_area("✍️ 專業編輯區 (同步保存)", value=st.session_state.edit_buffer, height=300, key="temp_editor", on_change=update_buffer)
            st.markdown(f'<div class="output-container">{render_html_master(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
            
            sc1, sc2 = st.columns(2)
            with sc1:
                if st.button("⭐ 收藏至個人曲庫"):
                    st.session_state.my_library[s_title] = {"content": st.session_state.edit_buffer, "date": str(datetime.datetime.now())}
                    st.toast(f"已存入曲庫：{s_title}")
            with sc2:
                st.download_button("💾 下載彩色 Word", export_docx_master(st.session_state.edit_buffer, s_title), f"{s_title}.docx")

    with t2:
        st.session_state.yt_url = st.text_input("貼上 YouTube 網址", value=st.session_state.yt_url)
        if st.session_state.yt_url:
            st.video(st.session_state.yt_url)
        st.markdown("---")
        # 確保影音練習下也有譜面
        st.markdown(f'<div class="output-container">{render_html_master(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)

    with t3:
        if st.session_state.my_library:
            for name, data in st.session_state.my_library.items():
                cn, ca = st.columns([4, 1])
                cn.info(f"🎵 {name}")
                if ca.button(f"載入", key=f"lib_{name}"):
                    st.session_state.edit_buffer = data['content']
                    st.rerun()
        else: st.warning("曲庫是空的")

# 滾動控制
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
