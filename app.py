import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import RGBColor, Pt
import io
import json
import datetime

# --- 1. 核心顏色與初始化 ---
CHORD_COLORS = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive Pro - Brett v14.6", layout="wide")

# 初始化數據 (持久化核心)
if 'my_library' not in st.session_state: st.session_state.my_library = {}
if 'edit_buffer' not in st.session_state: st.session_state.edit_buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""

# --- 2. 視覺配色與置頂 CSS ---
st.markdown("""
    <style>
    /* 抬頭置頂 */
    header[data-testid="stHeader"] { background-color: #1E3A8A !important; }
    
    /* 側邊欄配色強化 */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; border-right: 1px solid #3B82F6; }
    section[data-testid="stSidebar"] .stMarkdown p, section[data-testid="stSidebar"] label { 
        color: #FFFFFF !important; font-weight: bold; font-size: 1.1em;
    }
    
    /* Tab 分頁美化 */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 12px; padding: 6px; }
    .stTabs [data-baseweb="tab"] { color: #93C5FD !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #FACC15 !important; color: #1E3A8A !important; border-radius: 8px; }
    
    /* 樂譜容器樣式 */
    .output-container { 
        background: #FFFFFF; padding: 45px; line-height: 3.2; font-size: 1.6em; 
        white-space: pre-wrap; border-radius: 20px; border: 3px solid #E2E8F0; 
        color: #1E293B; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); 
    }
    .perf-mode { background-color: #0F172A !important; color: #F8FAFC !important; font-size: 2.6em !important; border: none !important; }
    
    /* 和弦顯色 */
    .c-A { color: #1D4ED8 !important; } .c-F { color: #22C55E !important; }
    .c-E { color: #EAB308 !important; } .c-G { color: #3B82F6 !important; }
    .c-C { color: #EF4444 !important; } .c-D { color: #F97316 !important; }
    .c-B { color: #A855F7 !important; }
    
    .section-header { background: #FDE047; color: #1E3A8A; padding: 10px 20px; border-radius: 8px; font-weight: bold; margin: 25px 0; border-left: 10px solid #1E3A8A; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心邏輯處理 ---
def transpose_logic(chord, steps):
    if any(x in chord for x in ['Intro', 'Verse', 'Chorus', 'Drum', 'Bridge']): return chord
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
    if not text: return "<p style='color:gray;text-align:center;'>尚未輸入內容或載入曲目</p>"
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-header">📍 \1</div>', text)
    text = re.sub(r'\[\[Drum:([^\]]+)\]\]', r'<span style="background:#1E3A8A; color:white; padding:3px 10px; border-radius:6px; font-weight:bold; font-size:0.8em;">🥁 \1</span>', text)
    parts = re.split(r'(\[[^\]]+\])', text)
    res, cur_cls = "", ""
    for p in parts:
        if p.startswith('[') and p.endswith(']'):
            if 'div' in p or 'span' in p: res += p; continue
            char = p.split('/')[0][1].upper()
            cur_cls = f"c-{char}"
            res += f'<span class="{cur_cls}">{p}'
        else:
            res += f'{p}</span>' if cur_cls else p
    return res

def export_docx(text, title):
    doc = Document(); doc.add_heading(title, 0); p = doc.add_paragraph()
    parts = re.split(r'(\[[^\]]+\])', text)
    cur_rgb = None
    for part in parts:
        if part.startswith('[') and part.endswith(']'):
            char = part.split('/')[0][1].upper()
            cur_rgb = CHORD_COLORS.get(char, (0,0,0))
            run = p.add_run(part); run.bold = True
        else:
            run = p.add_run(part)
        if cur_rgb: run.font.color.rgb = RGBColor(*cur_rgb)
    buf = io.BytesIO(); doc.save(buf); return buf.getvalue()

# --- 4. 介面與交互邏輯 ---
st.sidebar.markdown("# 🎹 Brett Pro v14.6")
work_mode = st.sidebar.radio("⏱️ 模式選擇", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動速度", 0, 15, 0)

# 更新 Buffer 的回調
def update_buffer():
    st.session_state.edit_buffer = st.session_state.temp_editor

if work_mode == "演出模式":
    st.markdown(f'<div class="output-container perf-mode">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
else:
    st.title("🎸 Liberlive 旗艦轉譜練習站")
    
    with st.expander("🎼 全域參數設定", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: ok = st.selectbox("原曲調性", KEYS)
        with c2: tk = st.selectbox("目標調性", KEYS, index=6)
        with c3: bpm = st.number_input("BPM 速度", 40, 240, 90)

    t1, t2, t3 = st.tabs(["🎵 智能轉譜", "🎬 影音對齊", "📁 曲庫管理"])

    with t1:
        s_name = st.text_input("歌曲標題", "My Masterpiece")
        raw_in = st.text_area("輸入原始內容 ( lyrics [Chord] )", height=150)
        
        if st.button("🚀 執行智能移調與顯色"):
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.edit_buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_logic(m.group(1), steps), raw_in)
            st.rerun()

        if st.session_state.edit_buffer:
            st.text_area("✍️ 專業編輯區 (修改後自動保存)", value=st.session_state.edit_buffer, height=350, key="temp_editor", on_change=update_buffer)
            st.markdown(f'<div class="output-container">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)
            
            b1, b2 = st.columns(2)
            with b1:
                if st.button("⭐ 收藏至個人雲端曲庫"):
                    st.session_state.my_library[s_name] = {
                        "content": st.session_state.edit_buffer,
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.success(f"✅ 已成功存入曲庫：{s_name}")
            with b2:
                st.download_button("💾 下載全彩 Word 檔", export_docx(st.session_state.edit_buffer, s_name), f"{s_name}.docx")

    with t2:
        st.session_state.yt_url = st.text_input("YouTube 練習連結", value=st.session_state.yt_url)
        if st.session_state.yt_url:
            st.video(st.session_state.yt_url)
        st.markdown("---")
        st.markdown(f'<div class="output-container">{render_html(st.session_state.edit_buffer)}</div>', unsafe_allow_html=True)

    with t3:
        if not st.session_state.my_library:
            st.info("目前曲庫尚無歌曲，請先收藏。")
        else:
            for name, data in list(st.session_state.my_library.items()):
                col_n, col_a = st.columns([4, 1])
                col_n.warning(f"🎵 {name} | {data.get('date', 'N/A')}")
                if col_a.button(f"載入", key=f"load_{name}"):
                    st.session_state.edit_buffer = data['content']
                    st.rerun()
            st.markdown("---")
            st.download_button("📤 導出 JSON 備份", json.dumps(st.session_state.my_library, ensure_ascii=False), "backup.json")

# 自動滾動控制
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
