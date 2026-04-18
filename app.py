import streamlit as st
import re
import io
import json
import datetime
from docx import Document
from docx.shared import RGBColor, Pt

# --- 1. 核心規範與初始化 ---
CHORD_COLORS = {
    'A': (29, 78, 216), 'F': (34, 197, 94), 'E': (234, 179, 8),
    'G': (59, 130, 246), 'C': (239, 68, 68), 'D': (249, 115, 22), 'B': (168, 85, 247)
}
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

st.set_page_config(page_title="Liberlive Pro Master v14.9", layout="wide")

# 雙重鎖定緩存 (解決資料消失問題)
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'my_lib' not in st.session_state: st.session_state.my_lib = {}
if 'yt' not in st.session_state: st.session_state.yt = ""

# --- 2. 視覺配色 (藍/黃/綠/白) 與版面優化 CSS ---
st.markdown("""
    <style>
    /* 全域背景 */
    .stApp { background-color: #F1F5F9; }
    header { visibility: hidden; } /* 隱藏預設抬頭騰出空間 */
    
    /* 側邊欄 (深藍) */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; border-right: 3px solid #FACC15; }
    section[data-testid="stSidebar"] * { color: white !important; }

    /* 分頁標籤 (藍底黃綠字) */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 8px; padding: 5px; gap: 10px; }
    .stTabs [data-baseweb="tab"] { color: #22C55E !important; font-weight: bold; font-size: 1.1em; }
    .stTabs [aria-selected="true"] { background-color: #FACC15 !important; color: #1E3A8A !important; border-radius: 5px; }

    /* 樂譜容器 (純白底，大字彩色) */
    .chord-view { 
        background-color: #FFFFFF !important; padding: 35px; border-radius: 12px; 
        border: 2px solid #1E3A8A; line-height: 2.8; font-size: 1.8em; 
        white-space: pre-wrap; color: #000000 !important;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
    }
    
    /* 演出模式 (全螢幕最大化) */
    .perf-view { background-color: #000000 !important; color: #FFFFFF !important; font-size: 3em !important; line-height: 3.5 !important; }

    /* 和弦染色規則 */
    .c-A { color: #1D4ED8 !important; font-weight: 900; } .c-F { color: #22C55E !important; font-weight: 900; }
    .c-E { color: #EAB308 !important; font-weight: 900; } .c-G { color: #3B82F6 !important; font-weight: 900; }
    .c-C { color: #EF4444 !important; font-weight: 900; } .c-D { color: #F97316 !important; font-weight: 900; }
    .c-B { color: #A855F7 !important; font-weight: 900; }
    
    /* 按鈕配色 (鮮綠) */
    div.stButton > button { background-color: #22C55E !important; color: white !important; border-radius: 10px; font-weight: bold; border: none; padding: 0.5rem 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心處理引擎 ---
def transpose_chord(chord, steps):
    if any(x in chord for x in ['Drum', 'Intro', 'Verse', 'Chorus']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    lookup = [k if k not in ['Db','Eb','Gb','Ab','Bb'] else {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[k] for k in KEYS]
    r = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_html_master(text):
    if not text: return "<div style='text-align:center; color:gray; padding:50px;'>請在『智能轉譜』貼上內容並轉換</div>"
    # 段落標籤
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div style="background:#FDE047; color:#1E3A8A; padding:5px 15px; border-radius:5px; font-weight:bold; margin-top:20px;">📍 \1</div>', text)
    # 染色邏輯
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

def export_docx(text, title):
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

# --- 4. 介面呈現 (版面重新規劃) ---
st.sidebar.title("🎸 Brett Pro v14.9")
view_mode = st.sidebar.radio("⏱️ 模式", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動", 0, 15, 0)

# 置頂參數列 (縮小化)
with st.container():
    col1, col2, col3, col4 = st.columns([1,1,1,2])
    with col1: ok = st.selectbox("原調", KEYS)
    with col2: tk = st.selectbox("目標調", KEYS, index=6)
    with col3: bpm = st.number_input("BPM", 40, 240, 90)
    with col4: st.write("") # 留白

if view_mode == "演出模式":
    st.markdown(f'<div class="chord-view perf-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)
else:
    tab1, tab2, tab3 = st.tabs(["🎵 智能轉譜", "🎬 影音練習", "📁 收藏曲庫"])

    with tab1:
        edit_col, view_col = st.columns([1, 1]) # 左右佈局
        with edit_col:
            song_name = st.text_input("歌曲標題", "New Song")
            raw_input = st.text_area("在此輸入內容", height=350, value=st.session_state.buffer)
            if st.button("🚀 執行轉換並顯色"):
                steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
                st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_chord(m.group(1), steps), raw_input)
                st.rerun()
            if st.button("⭐ 收藏此曲"):
                st.session_state.my_lib[song_name] = {"content": st.session_state.buffer, "date": str(datetime.datetime.now())}
                st.toast("✅ 已加入收藏！")
        with view_col:
            st.markdown(f'<div class="chord-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)
            st.download_button("💾 下載 Word", export_docx(st.session_state.buffer, song_name), f"{song_name}.docx")

    with tab2:
        st.session_state.yt = st.text_input("貼上 YouTube 網址", value=st.session_state.yt)
        if st.session_state.yt:
            v_col, s_col = st.columns([2, 1]) # 影片佔比加大
            with v_col: st.video(st.session_state.yt)
            with s_col: st.info("💡 提示：在此模式下對齊節奏與和弦。")
        
        st.markdown(f'<div class="chord-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)

    with tab3:
        if st.session_state.my_lib:
            for name in st.session_state.my_lib.keys():
                if st.button(f"📖 載入 {name}"):
                    st.session_state.buffer = st.session_state.my_lib[name]['content']
                    st.rerun()
        else: st.warning("曲庫是空的。")

# JavaScript 滾動
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
