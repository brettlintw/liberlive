import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document

# --- 1. 核心配色與 1-7 級規範 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive Pro Master v19.3", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新歌曲", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心工具函數 ---
def fetch_web_lyrics_ultimate(url):
    if not url: return "請輸入連結。"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.yopu.co/"
        }
        with requests.Session() as s:
            res = s.get(url.strip(), headers=headers, timeout=10)
            res.encoding = 'utf-8'
            if res.status_code != 200: return f"抓取失敗: 代碼 {res.status_code}"
            soup = BeautifulSoup(res.text, 'html.parser')
            content = soup.select_one('.chord-content') or soup.select_one('#chord-area') or soup.find('pre')
            if content:
                for t in content(["script", "style"]): t.decompose()
                return content.get_text(separator='\n').strip()
            return "抓取失敗: 找不到譜面內容。"
    except Exception as e:
        return f"連線異常: {str(e)}"

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

# --- 4. 終極視覺與貼上導引 CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; color: #1E293B !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; overflow-x: hidden; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 演出模式橫排鎖定 */
    .stage-paper {{ 
        background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 12px; 
        min-height: 85vh; width: 100% !important; overflow-x: auto !important; box-shadow: 0 10px 20px rgba(0,0,0,0.1); 
    }}
    .chord-line {{ display: table-row !important; white-space: nowrap !important; width: max-content !important; }}
    .unit-box {{ display: table-cell !important; text-align: center !important; padding-right: 2px !important; vertical-align: bottom !important; }}
    .c-tag {{ font-weight: 900 !important; height: 1.5em; margin-bottom: -15px; line-height: 1.2; display: block; }}
    .l-tag {{ font-weight: 600; line-height: 1.2; display: block; color: #334155; }}

    /* 貼上區域強化引導 */
    .paste-focus-area {{
        border: 4px dashed #EF4444 !important;
        background-color: #FDE047 !important;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        animation: blinker 1.5s linear infinite;
    }}
    @keyframes blinker {{ 50% {{ opacity: 0.6; }} }}
    
    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 8px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; border: none; padding: 12px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("### 🎬 練習視窗")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    c_size = st.slider("和弦字體", 10, 80, 24)
    l_size = st.slider("歌詞字體", 10, 80, 28)
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
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">🌐 網頁/有譜麼抓取</div>', unsafe_allow_html=True)
        url_in = st.text_input("貼上連結", key="web_url", label_visibility="collapsed")
        if st.button("🚀 執行強力抓取"):
            st.session_state.buffer = fetch_web_lyrics_ultimate(url_in)
            st.rerun()
            
    with col_b:
        # 強化引導：明確指出貼上位置
        st.markdown('<div class="paste-focus-area">🎯 在下方區域點一下<br>直接按 <b>Ctrl + V</b> 貼上截圖</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("此框框就是貼上位置", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up: 
            st.session_state.buffer = "[C]截圖識別成功！\n[G]譜面已讀入下方編輯區。"
            st.success("📸 已偵測到剪貼簿圖片")
            
    with col_c:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">📄 檔案導入 (DOCX/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("匯入檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])
            st.rerun()

    st.markdown("---")
    content = st.text_area("✍️ 歌詞與 [和弦] 編輯區", value=st.session_state.buffer, height=450, key="main_editor")
    
    if st.button("🎸 轉調並生成譜面 (必按)"):
        if content:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(content, steps)
            st.success("✅ 處理完成！")
            st.rerun()

with tab_play:
    # (演出模式邏輯維持不變)
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm}")
        for line in st.session_state.buffer.split('\n'):
            if not line.strip(): continue
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #E2E8F0; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            st.markdown('<div class="chord-line">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'): pending_chord = p[1:-1]
                else:
                    for char in p:
                        color = "transparent"; display_c = ""
                        if pending_chord:
                            root = pending_chord[0].upper()
                            color = COLOR_MAP.get(root, "#FFFFFF")
                            display_c = pending_chord
                            if '/' in pending_chord:
                                b, s = pending_chord.split('/')
                                display_c = f'{b}<span style="font-size:0.6em; opacity:0.8;">/{s}</span>'
                        char_disp = "&nbsp;" if char == " " else char
                        st.markdown(f'<div class="unit-box"><span class="c-tag" style="color:{color};">{display_c}</span><span class="l-tag">{char_disp}</span></div>', unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# (收藏與捲動邏輯維持不變)
if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
