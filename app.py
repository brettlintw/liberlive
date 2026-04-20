import streamlit as st
import re
import io
import json
import datetime
from docx import Document

# --- 1. 核心規範與 Brett 專屬配色 (1-7級) ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#FF0000', # 1 紅 (高飽和)
    'D': '#FF8C00', # 2 橘
    'E': '#FFD700', # 3 黃
    'F': '#00FF00', # 4 綠
    'G': '#1E90FF', # 5 藍
    'A': '#0000FF', # 6 深藍
    'B': '#A020F0', # 7 紫
}

st.set_page_config(page_title="Liberlive Pro Station v17.3", layout="wide")

# 初始化數據與緩存
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "未知歌手", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 2. 視覺配色與極致置頂 CSS ---
st.markdown(f"""
    <style>
    /* 徹底移除頂部所有空白 */
    .block-container {{ padding-top: 0rem !important; padding-bottom: 0rem !important; margin-top: -30px; }}
    header {{ visibility: hidden !important; height: 0px !important; }}
    footer {{ visibility: hidden !important; }}

    /* 側邊欄配色 (深藍) */
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    
    /* 專業樂譜：垂直對齊與間距優化 */
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; margin-bottom: 12px; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 1px; min-width: 0.8em; }}
    .c-tag {{ font-weight: 900; height: 1.5em; margin-bottom: -8px; font-family: 'Arial'; }}
    .slash-part {{ font-size: 0.65em; opacity: 0.8; font-weight: normal; }}
    .l-tag {{ color: #000000; font-weight: 600; }}

    /* 舞台背景模式 */
    .stage-paper {{ background: white; padding: 45px; border-radius: 15px; border: 3px solid #1E3A8A; min-height: 85vh; }}
    .night-stage {{ background: #000000 !important; border-color: #440000 !important; }}
    .night-stage .l-tag {{ color: #FFFFFF !important; }} /* 黑夜模式文字變白 */
    .red-stage {{ background: #1a0000 !important; border-color: #660000 !important; }}
    .red-stage .l-tag {{ color: #CC0000 !important; }}

    /* 分頁與按鈕樣式 */
    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 10px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心處理引擎 ---
def transpose_chord(chord, steps):
    def _trans(c_part):
        m = re.match(r"([A-G][#b]?)(.*)", c_part)
        if not m: return c_part
        root, suffix = m.group(1), m.group(2)
        norm = {'Db':'C#', 'Eb':'D#', 'Gb':'F#', 'Ab':'G#', 'Bb':'A#'}
        r = norm.get(root, root)
        if r in KEYS:
            return KEYS[(KEYS.index(r) + steps) % 12] + suffix
        return c_part
    return "/".join([_trans(p) for p in chord.split('/')])

def split_chord_html(chord):
    if '/' in chord:
        base, slash = chord.split('/')
        return f'{base}<span class="slash-part">/{slash}</span>'
    return chord

def get_chord_color(chord):
    if not chord: return "transparent"
    root = chord[0].upper()
    return COLOR_MAP.get(root, "#000000")

# --- 4. 側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🎬 YouTube 聯動播放")
    st.session_state.yt_url = st.text_input("貼上網址", value=st.session_state.yt_url, label_visibility="collapsed")
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    
    st.markdown("---")
    theme_choice = st.radio("🌗 舞台視覺主題", ["普通白晝", "演出黑夜", "低對比紅黑"])
    c_size = st.slider("和弦字體", 10, 80, 24)
    l_size = st.slider("歌詞字體", 10, 80, 28)
    scroll_spd = st.slider("📜 自動捲動", 0, 20, 0)

# --- 5. 主介面控制列 (置頂) ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌手/曲名", value=st.session_state.meta['singer'])

# 數據同步
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_edit, tab_play, tab_cloud = st.tabs(["🎵 智能轉譜看板", "🎤 演出模式", "📁 雲端曲庫"])

with tab_edit:
    col_in, col_out = st.columns([1, 1])
    with col_in:
        raw_input = st.text_area("輸入 [C] 歌詞內容", value=st.session_state.buffer, height=450, placeholder="例如: [C]我來到[G]你的城市...")
        if st.button("🚀 執行變調與顯色"):
            if raw_input:
                steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
                st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: f"[{transpose_chord(m.group(1), steps)}]", raw_input)
                st.rerun()
    with col_out:
        st.markdown("### ⚙️ 快速預覽")
        st.info("💡 專業和弦對齊與顏色請在『演出模式』查看。")

with tab_play:
    # 主題切換邏輯
    theme_cls = ""
    if theme_choice == "演出黑夜": theme_cls = "night-stage"
    elif theme_choice == "低對比紅黑": theme_cls = "red-stage"
    
    st.markdown(f'<div class="stage-paper {theme_cls}">', unsafe_allow_html=True)
    
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        lines = st.session_state.buffer.split('\n')
        for line in lines:
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #DDD; margin:15px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
            st.markdown('<div class="chord-row">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'):
                    pending_chord = p[1:-1]
                else:
                    # 處理空格與文字，確保對齊
                    for char in p:
                        color = get_chord_color(pending_chord)
                        display_c = split_chord_html(pending_chord)
                        char_display = "&nbsp;" if char == " " else char
                        st.markdown(f"""
                        <div class="unit-box">
                            <span class="c-tag" style="color:{color}; font-size:{c_size}px;">{display_c}</span>
                            <span class="l-tag" style="font-size:{l_size}px;">{char_display}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_cloud:
    if st.button("⭐ 收藏當前內容至本地曲庫"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
        st.success(f"✅ 已成功收藏: {singer}")
    
    st.markdown("---")
    for name, val in st.session_state.db.items():
        if st.button(f"📖 載入曲目: {name}"):
            st.session_state.buffer = val['buffer']
            st.session_state.meta = val['meta']
            st.rerun()

# 終極捲動控制
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
