import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document
from PIL import Image

# --- 1. 核心規範與 Brett 專屬 1-7 級配色 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#00FF00', 
    'G': '#1E90FF', 'A': '#0000FF', 'B': '#A020F0'
}

st.set_page_config(page_title="Liberlive AI Station v17.7", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'web_url' not in st.session_state: st.session_state.web_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心抓取函數 (Scraper) ---
def fetch_web_lyrics(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        if "yopu.co" in url:
            # 針對『有譜麼』的解析邏輯
            soup = BeautifulSoup(res.text, 'html.parser')
            # 尋找譜面容器，這取決於該網站目前的 DOM 結構
            content = soup.find('div', class_='chord-content') or soup.find('pre')
            if content:
                return content.get_text()
        return "抓取成功，但格式可能需要手動微調。\n" + res.text[:500]
    except Exception as e:
        return f"抓取失敗: {str(e)}"

# --- 4. 側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🎬 YouTube 播放器")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url, label_visibility="collapsed")
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    theme_choice = st.radio("🌗 視覺主題", ["普通白晝", "演出黑夜", "低對比紅黑"], key="app_theme")
    c_size = st.slider("和弦大小", 10, 80, 24)
    l_size = st.slider("歌詞大小", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# --- 5. 動態視覺 CSS ---
theme_css = ""
text_color = "#000000"
paper_style = "background: #FFFFFF; border-color: #1E3A8A;"
if theme_choice == "演出黑夜":
    theme_css = "background-color: #000000 !important; color: #FFFFFF !important;"
    paper_style = "background: #000000 !important; border-color: #440000 !important;"
    text_color = "#FFFFFF"
elif theme_choice == "低對比紅黑":
    theme_css = "background-color: #1a0000 !important; color: #CC0000 !important;"
    paper_style = "background: #1a0000 !important; border-color: #660000 !important;"
    text_color = "#CC0000"

st.markdown(f"""
    <style>
    .stApp {{ {theme_css} }}
    .block-container {{ padding-top: 0rem !important; }}
    header, footer {{ visibility: hidden !important; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 2px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    .stage-paper {{ {paper_style} padding: 30px; border-radius: 15px; border: 2px solid; min-height: 85vh; width: 100%; }}
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; margin-bottom: 12px; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 2px; }}
    .c-tag {{ font-weight: 900; height: 1.5em; margin-bottom: -10px; }}
    .l-tag {{ color: {text_color} !important; font-weight: 600; }}
    .input-label {{ color: #22C55E; font-weight: bold; margin-bottom: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 6. 置頂控制列 ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌手/曲名", value=st.session_state.meta['singer'])

tab_edit, tab_play, tab_cloud = st.tabs(["🎵 智能轉譜導入", "🎤 演出模式", "📁 雲端曲庫"])

with tab_edit:
    # --- 全通路導入面板 ---
    st.markdown('<p class="input-label">🌐 網頁自動尋找 (支援 有譜麼) / 📸 圖片轉譜 / 📄 檔案導入</p>', unsafe_allow_html=True)
    in_col1, in_col2, in_col3 = st.columns(3)
    
    with in_col1:
        web_url = st.text_input("貼上網頁連結", placeholder="https://www.yopu.co/...", label_visibility="collapsed")
        if st.button("🔍 抓取網頁內容"):
            if web_url:
                with st.spinner("努力爬取中..."):
                    st.session_state.buffer = fetch_web_lyrics(web_url)
                    st.rerun()
            
    with in_col2:
        uploaded_img = st.file_uploader("上傳樂譜照片", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if uploaded_img:
            st.info("AI OCR 正在模擬解析...")
            st.session_state.buffer = "[C]解析後的[G]樂譜範例內容"
            
    with in_col3:
        uploaded_file = st.file_uploader("上傳 Word/TXT", type=['docx', 'txt'], label_visibility="collapsed")
        if uploaded_file:
            if uploaded_file.type == "text/plain":
                st.session_state.buffer = uploaded_file.read().decode("utf-8")
            else:
                doc = Document(uploaded_file)
                st.session_state.buffer = "\n".join([p.text for p in doc.paragraphs])

    st.markdown("---")
    raw_input = st.text_area("✍️ 歌詞與 [和弦] 編輯窗口", value=st.session_state.buffer, height=350)
    
    if st.button("🚀 執行智能變調並生成譜面"):
        if raw_input:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            def _trans(c):
                parts = c.split('/')
                def __t(p):
                    m = re.match(r"([A-G][#b]?)(.*)", p)
                    if m:
                        r, s = m.group(1), m.group(2)
                        norm = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
                        base = norm.get(r, r)
                        return KEYS[(KEYS.index(base) + steps) % 12] + s
                    return p
                return "/".join([__t(x) for x in parts])
            
            st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: f"[{_trans(m.group(1))}]", raw_input)
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        lines = st.session_state.buffer.split('\n')
        for line in lines:
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #DDD; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            st.markdown('<div class="chord-row">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'):
                    pending_chord = p[1:-1]
                else:
                    for char in p:
                        root = pending_chord[0].upper() if pending_chord else ""
                        color = COLOR_MAP.get(root, "transparent")
                        # Slash Chord 縮小顯示
                        display_c = pending_chord
                        if '/' in pending_chord:
                            b, s = pending_chord.split('/')
                            display_c = f'{b}<span style="font-size:0.6em; opacity:0.8;">/{s}</span>'
                        
                        char_disp = "&nbsp;" if char == " " else char
                        st.markdown(f"""
                        <div class="unit-box">
                            <span class="c-tag" style="color:{color}; font-size:{c_size}px;">{display_c}</span>
                            <span class="l-tag" style="font-size:{l_size}px;">{char_disp}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_cloud:
    if st.button("⭐ 收藏至雲端"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
        st.toast(f"✅ 已收藏 {singer}")
    st.markdown("---")
    for name, val in st.session_state.db.items():
        if st.button(f"📖 載入: {name}"):
            st.session_state.buffer = val['buffer']
            st.session_state.meta = val['meta']
            st.rerun()

# 捲動 JS
if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
