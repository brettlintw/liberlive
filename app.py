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

st.set_page_config(page_title="Liberlive Pro Master v15.2", layout="wide")

# 數據鎖定緩存 (Buffer)
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'my_lib' not in st.session_state: st.session_state.my_lib = {}
if 'yt' not in st.session_state: st.session_state.yt = ""

# --- 2. 視覺配色 CSS ---
st.markdown("""
    <style>
    /* 移除頂部空白，保留開關按鈕 */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    header { background-color: transparent !important; }
    
    /* 側邊欄配色 */
    section[data-testid="stSidebar"] { background-color: #1E3A8A !important; border-right: 3px solid #FACC15; }
    section[data-testid="stSidebar"] * { color: white !important; }

    /* 分頁標籤樣式 */
    .stTabs [data-baseweb="tab-list"] { background-color: #1E3A8A; border-radius: 5px; padding: 2px; }
    .stTabs [data-baseweb="tab"] { color: #22C55E !important; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #FACC15 !important; color: #1E3A8A !important; }

    /* 樂譜容器 (純白底彩色字) */
    .chord-view { 
        background-color: #FFFFFF !important; padding: 25px; border-radius: 8px; 
        border: 2px solid #1E3A8A; line-height: 2.8; font-size: 1.8em; 
        white-space: pre-wrap; color: #000000 !important; font-weight: 500;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* 演出模式 */
    .perf-view { background-color: #000000 !important; color: #FFFFFF !important; font-size: 3.2em !important; line-height: 3.5 !important; padding: 50px !important; }

    /* 和弦染色規則 */
    .c-A { color: #1D4ED8 !important; font-weight: 800; } .c-F { color: #16A34A !important; font-weight: 800; }
    .c-E { color: #CA8A04 !important; font-weight: 800; } .c-G { color: #2563EB !important; font-weight: 800; }
    .c-C { color: #DC2626 !important; font-weight: 800; } .c-D { color: #EA580C !important; font-weight: 800; }
    .c-B { color: #9333EA !important; font-weight: 800; }
    
    .section-tag { background: #FDE047; color: #1E3A8A; padding: 2px 12px; border-radius: 4px; font-weight: bold; font-size: 0.7em; margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心處理引擎 ---
def transpose_chord(chord, steps):
    if any(x in chord for x in ['Drum', 'Intro', 'Verse', 'Chorus', 'Bridge']): return chord
    m = re.match(r"([A-G][#b]?)", chord)
    if not m: return chord
    root, suffix = m.group(1), chord[len(m.group(1)):]
    lookup = [k if k not in ['Db','Eb','Gb','Ab','Bb'] else {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}[k] for k in KEYS]
    r = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}.get(root, root)
    if r in lookup:
        return KEYS[(lookup.index(r) + steps) % 12] + suffix
    return chord

def render_html_master(text):
    if not text: return "<div style='text-align:center; color:gray; padding:30px;'>目前無內容</div>"
    text = re.sub(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', r'<div class="section-tag">📍 \1</div>', text)
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
st.sidebar.title("🎸 Brett Pro v15.2")
view_mode = st.sidebar.radio("⏱️ 模式選擇", ["工作站模式", "演出模式"])
scroll_spd = st.sidebar.slider("📜 自動滾動", 0, 15, 0)

# 置頂設定列
c1, c2, c3, c4 = st.columns([1,1,1,2])
with c1: ok = st.selectbox("原調", KEYS)
with c2: tk = st.selectbox("目標調", KEYS, index=6)
with c3: bpm = st.number_input("BPM", 40, 240, 90)
with c4: st.write("")

if view_mode == "演出模式":
    st.markdown(f'<div class="chord-view perf-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)
else:
    t1, t2, t3 = st.tabs(["智能轉譜", "影音練習", "收藏曲庫"])

    with t1:
        edit_col, view_col = st.columns([1, 1])
        with edit_col:
            song_name = st.text_input("歌曲標題", "New Song")
            # 關鍵修復：移除 on_change，直接使用 value 綁定 buffer
            st.session_state.buffer = st.text_area("內容輸入區", height=450, value=st.session_state.buffer)
            
            btn_col1, btn_col2 = st.columns(2)
            if btn_col1.button("🚀 執行轉換"):
                steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
                st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: transpose_chord(m.group(1), steps), st.session_state.buffer)
                st.rerun()
            if btn_col2.button("⭐ 收藏此曲"):
                st.session_state.my_lib[song_name] = {"content": st.session_state.buffer}
                st.toast("✅ 已收藏")
        with view_col:
            st.markdown(f'<div class="chord-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)

    with t2:
        st.session_state.yt = st.text_input("YouTube 網址", value=st.session_state.yt)
        if st.session_state.yt:
            st.video(st.session_state.yt)
        st.markdown(f'<div class="chord-view">{render_html_master(st.session_state.buffer)}</div>', unsafe_allow_html=True)

    with t3:
        if st.session_state.my_lib:
            for name in st.session_state.my_lib.keys():
                if st.button(f"📖 載入 {name}"):
                    st.session_state.buffer = st.session_state.my_lib[name]['content']
                    st.rerun()
        else: st.info("曲庫尚無內容")

# JavaScript 滾動
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
