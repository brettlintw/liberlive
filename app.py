import streamlit as st
import re
import requests
from bs4 import BeautifulSoup
from docx import Document

# --- 1. 核心配色與 1-7 級規範 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive Pro Master v20.5", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新曲目", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 工具函數 ---
def fetch_v18_scraper(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url.strip(), headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.select_one('div.chord-content') or soup.find('pre') or soup.select_one('.post-content')
        return content.get_text() if content else "抓取失敗，找不到譜面區塊。"
    except Exception as e: return f"異常: {str(e)}"

def transpose_engine(text, steps):
    def _t(p):
        m = re.match(r"([A-G][#b]?)(.*)", p)
        if m:
            r, s = m.group(1), m.group(2)
            norm = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
            base = norm.get(r, r)
            if base in KEYS: return KEYS[(KEYS.index(base) + steps) % 12] + s
        return p
    return re.sub(r'\[([^\]]+)\]', lambda m: "[" + "/".join([_t(x.strip()) for x in m.group(1).split('/')]) + "]", text)

# --- 4. 終極橫向鎖定 CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; color: #1E293B !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 演出模式紙張 - 橫向流動鎖定 */
    .stage-paper {{ 
        background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 12px; 
        min-height: 85vh; width: 100% !important; overflow-x: auto !important; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    
    /* 整行歌詞容器：禁止換行 */
    .chord-line {{ 
        display: block !important; 
        white-space: nowrap !important; 
        margin-bottom: 35px !important;
        width: fit-content !important; 
        text-align: left !important;
    }}
    
    /* 核心單元：[和弦] + [下方文字] 的垂直組合，但單元間橫向排列 */
    .char-unit {{ 
        display: inline-grid !important; 
        grid-template-rows: 1.5em auto; 
        justify-items: center;
        text-align: center;
        margin-right: 0px;
        vertical-align: bottom;
    }}
    
    .c-label {{ font-weight: 900 !important; line-height: 1.0; margin-bottom: 8px; }}
    .l-label {{ font-weight: 600; line-height: 1.2; color: #334155; white-space: pre !important; font-family: sans-serif; }}

    .paste-zone {{
        border: 4px dashed #EF4444 !important; background-color: #FDE047 !important;
        padding: 15px; border-radius: 12px; text-align: center; color: black; font-weight: bold;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 8px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; border: none; padding: 12px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. UI 佈局 ---
with st.sidebar:
    st.markdown("### 🎬 影音控制")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    c_size = st.slider("和弦大小", 10, 80, 24)
    l_size = st.slider("歌詞大小", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# 置頂控制
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌曲名稱", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_in, tab_play, tab_cloud = st.tabs(["🎵 智能導入編輯", "🎤 演出模式", "📁 雲端曲庫"])

with tab_in:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A;color:#1E3A8A;font-weight:bold">🌐 網頁抓取</div>', unsafe_allow_html=True)
        url_in = st.text_input("連結", key="scraper_url", label_visibility="collapsed")
        if st.button("🚀 抓取內容"):
            st.session_state.buffer = fetch_v18_scraper(url_in)
            st.rerun()
    with col_b:
        st.markdown('<div class="paste-zone">🎯 截圖後點此框框<br>直接按 Ctrl+V 貼上</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("貼上截圖處", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up: st.session_state.buffer = "[C]截圖已接收，識別中..."
    with col_c:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A;color:#1E3A8A;font-weight:bold">📄 檔案導入 (Word/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("匯入檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])
            st.rerun()

    st.markdown("---")
    content = st.text_area("✍️ 譜面編輯窗口 (歌詞與 [和弦])", value=st.session_state.buffer, height=450, key="editor_main")
    
    if st.button("🎸 生成譜面並變調 (必按)"):
        if content:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(content, steps)
            st.success("✅ 譜面已生成！請切換至演出模式。")
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm}")
        for line in st.session_state.buffer.split('\n'):
            if not line.strip(): continue
            # 區分段落標記 (如 [主歌])
            if line.strip().startswith('[') and len(line.strip()) < 15:
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #E2E8F0; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
            # 橫向佈局：一行歌詞
            st.markdown('<div class="chord-line">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'):
                    pending_chord = p[1:-1]
                else:
                    # 將文字拆解為單個字元，但保持在同一個 inline 單元中
                    for char in p:
                        color, display_c = "transparent", ""
                        if pending_chord:
                            root = pending_chord[0].upper()
                            color = COLOR_MAP.get(root, "#FFFFFF")
                            display_c = pending_chord
                            # 處理 Slash Chord
                            if '/' in pending_chord:
                                b, s = pending_chord.split('/')
                                display_c = f'{b}<span style="font-size:0.6em; opacity:0.8;">/{s}</span>'
                        
                        char_disp = "&nbsp;" if char == " " else char
                        st.markdown(f"""
                        <div class="char-unit">
                            <span class="c-label" style="color:{color}; font-size:{c_size}px;">{display_c}</span>
                            <span class="l-label" style="font-size:{l_size}px;">{char_disp}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_cloud:
    # 雲端資料庫功能
    if st.button("⭐ 收藏此譜"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
    st.markdown("---")
    for name in st.session_state.db.keys():
        if st.button(f"📖 載入: {name}"):
            st.session_state.buffer = st.session_state.db[name]['buffer']
            st.rerun()

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
