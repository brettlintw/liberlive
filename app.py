import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document

# --- 1. 核心規範與 Brett 專屬 1-7 級配色 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive Pro Master v18.8", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新歌曲", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心工具函數 (恢復 v18.5 抓取邏輯) ---
def fetch_web_lyrics(url):
    if not url: return "請輸入連結。"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": "https://www.yopu.co/"
        }
        res = requests.get(url.strip(), headers=headers, timeout=15)
        res.encoding = 'utf-8'
        if res.status_code != 200: return f"抓取失敗 (狀態碼: {res.status_code})"
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # 比對成功版選擇器
        content = soup.select_one('.chord-content') or soup.select_one('#chord-area') or soup.find('pre')
        
        if content:
            # 移除雜質但保留純文字內容
            for s in content(["script", "style"]): s.decompose()
            return content.get_text()
        return "無法在頁面找到譜面內容，請嘗試手動貼上。"
    except Exception as e:
        return f"抓取出錯: {str(e)}"

def transpose_engine(text, steps):
    def _t(p):
        m = re.match(r"([A-G][#b]?)(.*)", p)
        if m:
            r, s = m.group(1), m.group(2)
            norm = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
            base = norm.get(r, r)
            if base in KEYS:
                return KEYS[(KEYS.index(base) + steps) % 12] + s
        return p
    return re.sub(r'\[([^\]]+)\]', lambda m: "[" + "/".join([_t(x.strip()) for x in m.group(1).split('/')]) + "]", text)

# --- 4. 統一視覺與橫向排版 CSS (解決直列問題) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; color: #1E293B !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; overflow-x: hidden; }}

    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    
    .input-card {{ background: white; padding: 15px; border-radius: 8px; border-top: 4px solid #1E3A8A; box-shadow: 0 4px 6px rgba(0,0,0,0.05); color: #1E3A8A; font-weight: bold; }}
    
    /* 演出模式紙張 - 修正橫向延伸 */
    .stage-paper {{ 
        background: white !important; 
        border: 1px solid #E2E8F0; 
        padding: 40px; 
        border-radius: 12px; 
        min-height: 85vh; 
        box-shadow: 0 10px 15px rgba(0,0,0,0.1); 
        width: 100%; 
    }}
    
    /* 核心橫向行：強制不換行 */
    .chord-line {{ 
        display: block !important; 
        white-space: nowrap !important; 
        line-height: 3.5 !important; 
        margin-bottom: 25px !important; 
        width: 100% !important;
    }}
    
    /* 垂直單元：和弦文字一體 */
    .char-unit {{ 
        display: inline-block !important; /* 確保單元橫著排 */
        vertical-align: bottom !important;
        text-align: center !important;
        margin-right: 1px !important; 
        min-width: 0.9em !important;
    }}
    
    .c-label {{ display: block !important; font-weight: 900 !important; height: 1.5em; margin-bottom: -18px; }}
    .l-label {{ display: block !important; color: #334155 !important; font-weight: 600; }}

    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 8px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; border: none; padding: 10px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 側邊欄與視窗 ---
with st.sidebar:
    st.markdown("### 🎬 影音輔助視窗")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    c_size = st.slider("和弦字體大小", 10, 80, 24)
    l_size = st.slider("歌詞字體大小", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# 頂部控制列
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
        st.markdown('<div class="input-card">🌐 網頁/有譜麼自動抓取</div>', unsafe_allow_html=True)
        url_in = st.text_input("貼上連結", key="web_url_field", label_visibility="collapsed")
        if st.button("🚀 執行抓取"):
            st.session_state.buffer = fetch_web_lyrics(url_in)
            st.rerun()
    with col_b:
        st.markdown('<div class="input-card">📸 圖片/截圖識別</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("上傳照片", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up: st.session_state.buffer = "[C]識別成功的[G]範例內容"
    with col_c:
        st.markdown('<div class="input-card">📄 檔案導入 (DOCX/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("匯入檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])

    st.markdown("---")
    edit_text = st.text_area("✍️ 歌詞與 [和弦] 編輯視窗", value=st.session_state.buffer, height=400)
    
    if st.button("🎸 生成譜面並變調"):
        steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
        st.session_state.buffer = transpose_engine(edit_text, steps)
        st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        for line in st.session_state.buffer.split('\n'):
            if not line.strip(): continue
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #E2E8F0; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
            # 渲染每一行
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
    if st.button("⭐ 收藏譜面"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
        st.toast(f"已收藏 {singer}")
    st.markdown("---")
    for name in st.session_state.db.keys():
        if st.button(f"📖 載入: {name}"):
            st.session_state.buffer = st.session_state.db[name]['buffer']
            st.session_state.meta = st.session_state.db[name]['meta']
            st.rerun()

# 滾動控制
if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
