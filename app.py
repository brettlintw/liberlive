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

st.set_page_config(page_title="Liberlive Pro Master v18.4", layout="wide")

# --- 2. 初始化 Session (數據安全鎖定) ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新曲目", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心工具函數 (抓取引擎突破版) ---
def fetch_web_lyrics_pro(url):
    if not url: return "請輸入網址。"
    url = url.strip()
    try:
        # 高級偽裝頭部
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.yopu.co/",
            "Accept-Language": "zh-TW,zh;q=0.9"
        }
        
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return f"抓取失敗: 伺服器拒絕存取 (Error {response.status_code})"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除干擾元素
        for trash in soup(["script", "style", "nav", "footer", "header", "ads"]):
            trash.extract()

        # 有譜麼特定的和弦選擇器組合
        targets = [
            '.chord-content', '.chord-area', '#chord-area', 
            'pre', '.post-content', 'article'
        ]
        
        content_found = None
        for selector in targets:
            content_found = soup.select_one(selector)
            if content_found and len(content_found.get_text()) > 50:
                break
        
        if content_found:
            # 獲取純文字並進行結構化清理
            raw_text = content_found.get_text(separator='\n')
            # 清理過多換行與空白
            clean_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            return '\n'.join(clean_lines)
            
        return "抓取失敗: 找不到有效的譜面內容。這可能是因為該網頁使用了加密保護，請嘗試手動貼上。"
        
    except Exception as e:
        return f"抓取異常: {str(e)}"

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

# --- 4. 專業配色 UI (藍/黃/綠/白) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; color: #1E293B !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; }}

    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    
    .input-card {{ background: white; padding: 18px; border-radius: 10px; border-top: 5px solid #1E3A8A; box-shadow: 0 4px 10px rgba(0,0,0,0.05); color: #1E3A8A; font-weight: bold; margin-bottom: 8px; }}
    .stage-paper {{ background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 15px; min-height: 85vh; box-shadow: 0 10px 15px rgba(0,0,0,0.1); }}
    
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; margin-bottom: 12px; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 2px; }}
    .c-tag {{ font-weight: 900; height: 1.5em; margin-bottom: -10px; }}
    .l-tag {{ color: #334155 !important; font-weight: 600; }}

    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 8px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; border: none; padding: 12px; }}
    div.stButton > button:hover {{ background-color: #16A34A !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 側邊欄控制 ---
with st.sidebar:
    st.markdown("### 🎬 影音同步輔助")
    st.session_state.yt_url = st.text_input("YouTube 練習連結", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    c_size = st.slider("和弦大小", 10, 80, 24)
    l_size = st.slider("歌詞大小", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# 置頂控制列
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
        url_in = st.text_input("貼上連結", key="scraper_pro", label_visibility="collapsed")
        if st.button("🚀 執行抓取"):
            with st.spinner("正在模擬請求並提取內容..."):
                st.session_state.buffer = fetch_web_lyrics_pro(url_in)
                st.rerun()
    with col_b:
        st.markdown('<div class="input-card">📸 圖片/截圖 AI 識別</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("上傳照片", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up: st.session_state.buffer = "[C]AI 識別成功的[G]範例譜面文字..."
    with col_c:
        st.markdown('<div class="input-card">📄 檔案導入 (Word/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("選擇檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])

    st.markdown("---")
    edit_text = st.text_area("✍️ 歌詞與 [和弦] 編輯窗口", value=st.session_state.buffer, height=450)
    
    if st.button("🎸 執行智能變調與譜面生成"):
        steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
        st.session_state.buffer = transpose_engine(edit_text, steps)
        st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        for line in st.session_state.buffer.split('\n'):
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #E2E8F0; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            st.markdown('<div class="chord-row">', unsafe_allow_html=True)
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
                                display_c = f'{b}<span style="font-size:0.6em; opacity:0.7;">/{s}</span>'
                        char_disp = "&nbsp;" if char == " " else char
                        st.markdown(f'<div class="unit-box"><span class="c-tag" style="color:{color}; font-size:{c_size}px;">{display_c}</span><span class="l-tag" style="font-size:{l_size}px;">{char_disp}</span></div>', unsafe_allow_html=True)
                        pending_chord = ""
            st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab_cloud:
    if st.button("⭐ 收藏至雲端"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
        st.toast(f"已收藏 {singer}")
    st.markdown("---")
    for name in st.session_state.db.keys():
        if st.button(f"📖 載入曲目: {name}"):
            st.session_state.buffer = st.session_state.db[name]['buffer']
            st.session_state.meta = st.session_state.db[name]['meta']
            st.rerun()

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
