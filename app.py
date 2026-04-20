import streamlit as st
import re
import io
import json
import datetime
from docx import Document

# --- 1. 核心規範與配色 (Brett 標準) ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive AI Station v17", layout="wide")

# 初始化 Session State (數據緩存鎖定)
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'theme' not in st.session_state: st.session_state.theme = "白晝"
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 2. 極致置頂與演出模式 CSS ---
st.markdown(f"""
    <style>
    /* 移除所有頂部空白與抬頭 */
    .block-container {{ padding-top: 0rem !important; padding-bottom: 0rem !important; }}
    header {{ visibility: hidden !important; height: 0px !important; }}
    
    /* 側邊欄深藍底 */
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 2px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 專業樂譜：和弦在字正上方 */
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; margin-bottom: 10px; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 1px; min-width: 1em; }}
    .c-tag {{ font-weight: 800; height: 1.4em; margin-bottom: -5px; }}
    .slash-part {{ font-size: 0.6em; opacity: 0.8; font-weight: 400; }}
    .l-tag {{ color: #000000; font-weight: 500; }}

    /* 舞台背景切換 */
    .stage-paper {{ background: white; padding: 40px; border-radius: 12px; border: 2px solid #1E3A8A; min-height: 80vh; }}
    .night-stage {{ background: #000000 !important; color: #ff3333 !important; border-color: #440000 !important; }}
    .night-stage .l-tag {{ color: #cc0000 !important; }}

    /* 置頂進度條 (Song Map) */
    .song-map {{ display: flex; gap: 4px; padding: 5px 0; }}
    .map-step {{ flex: 1; height: 10px; border-radius: 5px; background: #E2E8F0; text-align: center; font-size: 9px; line-height: 10px; color: #1E3A8A; }}
    .map-step.active {{ background: #FDE047; font-weight: bold; border: 1px solid #1E3A8A; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心運算引擎 ---
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
    # 支援複合和弦 G/B 同步變調
    return "/".join([_trans(p) for p in chord.split('/')])

def split_chord_html(chord):
    if '/' in chord:
        base, slash = chord.split('/')
        return f'{base}<span class="slash-part">/{slash}</span>'
    return chord

def get_chord_color(chord):
    if not chord: return "transparent"
    # 取第一個字母
    root = chord[0].upper()
    return COLOR_MAP.get(root, "#000")

# --- 4. 介面呈現 ---
with st.sidebar:
    st.markdown("### 🎬 YouTube 播放器")
    st.session_state.yt_url = st.text_input("網址連結", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    
    st.markdown("---")
    st.session_state.theme = st.radio("🌗 視覺主題", ["白晝模式", "演出黑夜", "低對比紅黑"])
    c_size = st.slider("和弦大小", 10, 50, 22)
    l_size = st.slider("歌詞大小", 10, 50, 26)
    
    st.markdown("---")
    st.markdown("### 📸 OCR 圖片轉譜 (AI 預留)")
    st.file_uploader("上傳樂譜照片", type=['png','jpg','jpeg'])

# 置頂控制列
cm1, cm2, cm3, cm4, cm5 = st.columns(5)
with cm1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with cm2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with cm3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with cm4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with cm5: singer = st.text_input("曲名/歌手", value=st.session_state.meta['singer'])

st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

# 段落進度條
sections = re.findall(r'\[(前奏|Intro|主歌|Verse|副歌|Chorus|間奏|Bridge|結尾|Outro)\]', st.session_state.buffer)
if sections:
    st.markdown('<div class="song-map">', unsafe_allow_html=True)
    for s in sections:
        st.markdown(f'<div class="map-step active">{s}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

tab_edit, tab_play, tab_cloud = st.tabs(["🎵 智能樂譜看板", "🎤 演出模式", "📁 雲端曲庫"])

with tab_edit:
    col_in, col_out = st.columns([1, 1])
    with col_in:
        raw_input = st.text_area("輸入 [C]和弦 歌詞內容", value=st.session_state.buffer, height=450)
        if st.button("🚀 執行變調並變色"):
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: f"[{transpose_chord(m.group(1), steps)}]", raw_input)
            st.rerun()
    with col_out:
        st.markdown("### ⚙️ 編輯輔助預覽")
        st.info("請在演出模式查看完整排版效果")

with tab_play:
    # 舞台顯示邏輯
    theme_cls = "night-stage" if "夜" in st.session_state.theme or "紅" in st.session_state.theme else ""
    st.markdown(f'<div class="stage-paper {theme_cls}">', unsafe_allow_html=True)
    
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        lines = st.session_state.buffer.split('\n')
        for line in lines:
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #DDD; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
            # 和弦對齊文字渲染
            st.markdown('<div class="chord-row">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'):
                    pending_chord = p[1:-1]
                else:
                    for char in p:
                        color = get_chord_color(pending_chord)
                        display_c = split_chord_html(pending_chord)
                        st.markdown(f"""
                        <div class="unit-box">
                            <span class="c-tag" style="color:{color}; font-size:{c_size}px;">{display_c}</span>
                            <span class="l-tag" style="font-size:{l_size}px;">{char}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_cloud:
    st.subheader("📁 個人雲端收藏")
    if st.button("⭐ 收藏當前譜面"):
        st.session_state.db[singer + "_" + tk] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
        st.toast("✅ 已存入本地雲端緩存")
    
    st.markdown("---")
    for key, val in st.session_state.db.items():
        if st.button(f"📖 載入曲目: {key}"):
            st.session_state.buffer = val['buffer']
            st.session_state.meta = val['meta']
            st.rerun()

# 自動滾動
if scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
