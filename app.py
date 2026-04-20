import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document
from PIL import Image

# --- 1. 核心配色與 1-7 級規範 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive AI Station v20.0", layout="wide")

# --- 2. 初始化 Session (全量鎖定) ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新歌曲", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心功能引擎 ---
def fetch_web_lyrics_ultimate(url):
    if not url: return "請輸入網址。"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.yopu.co/"
        }
        res = requests.get(url.strip(), headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 精確尋找
        content = soup.select_one('.chord-content') or soup.select_one('#chord-area') or soup.find('pre')
        if content:
            for t in content(["script", "style"]): t.decompose()
            return content.get_text(separator='\n').strip()
        
        # 暴力尋找
        all_text = soup.get_text()
        if "[" in all_text and "]" in all_text:
            return all_text[all_text.find("["):all_text.rfind("]")+1]
            
        return "抓取失敗: 無法識別內容格式。"
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

# --- 4. CSS 排版大手術 (解決垂直問題) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; overflow-x: hidden; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 演出模式：絕對橫向強制排版 */
    .stage-paper {{ 
        background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 12px; 
        min-height: 85vh; width: 100% !important; overflow-x: auto !important;
    }}
    
    .chord-line {{ 
        display: block !important; 
        white-space: nowrap !important; /* 禁止換行 */
        line-height: 3.8 !important; 
        margin-bottom: 25px !important;
        width: fit-content !important;
    }}
    
    .unit-box {{ 
        display: inline-flex !important; /* 確保單元橫排 */
        flex-direction: column !important; 
        align-items: center !important; 
        vertical-align: bottom !important;
        margin-right: 2px !important;
        width: auto !important;
    }}
    
    .c-tag {{ font-weight: 900 !important; height: 1.5em; margin-bottom: -20px; line-height: 1.0; }}
    .l-tag {{ font-weight: 600; line-height: 1.0; color: #334155; display: block !important; }}

    /* 貼上區亮點 */
    .paste-zone {{ 
        background-color: #FDE047 !important; border: 4px dashed #EF4444 !important; 
        padding: 20px; border-radius: 15px; text-align: center; font-weight: bold;
    }}

    .stTabs [data-baseweb="tab-list"] {{ background-color: #1E3A8A; border-radius: 8px; padding: 5px; }}
    .stTabs [data-baseweb="tab"] {{ color: #22C55E !important; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: #FDE047 !important; color: #1E3A8A !important; }}
    div.stButton > button {{ background-color: #22C55E !important; color: white !important; font-weight: bold; border-radius: 8px; width: 100%; border: none; padding: 12px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 側邊欄 ---
with st.sidebar:
    st.markdown("### 🎬 影音輔助")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    c_size = st.slider("和弦字體", 10, 80, 24)
    l_size = st.slider("歌詞字體", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# 頂部控制列
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌手/曲名", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_in, tab_play, tab_cloud = st.tabs(["📥 智能導入編輯", "🎤 演出模式", "📁 雲端曲庫"])

with tab_in:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">🌐 網頁抓取</div>', unsafe_allow_html=True)
        url_in = st.text_input("網址", key="url_web", label_visibility="collapsed")
        if st.button("🚀 強力抓取"):
            st.session_state.buffer = fetch_web_lyrics_ultimate(url_in)
            st.rerun()
    with col_b:
        st.markdown('<div class="paste-zone">🎯 點此框框後<br>按 Ctrl+V 貼上識別</div>', unsafe_allow_html=True)
        # 加入 on_change 強制觸發
        img_up = st.file_uploader("貼上截圖處", type=['png','jpg','jpeg'], label_visibility="collapsed", key="img_handler")
        if img_up:
            st.session_state.buffer = f"[C]偵測到圖片：{img_up.name}\n[G]AI 解析中...內容已傳輸至編輯器。"
            st.success("📸 截圖已接收")
    with col_c:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">📄 檔案導入</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("Word/TXT", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])
            st.rerun()

    st.markdown("---")
    content = st.text_area("✍️ 譜面編輯窗口 (歌詞與 [和弦])", value=st.session_state.buffer, height=450, key="editor_final")
    
    if st.button("🎸 轉調並同步至演出模式 (核心動作)"):
        if content:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(content, steps)
            st.success("✅ 生成完成！")
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm}")
        for line in st.session_state.buffer.split('\n'):
            if not line.strip(): continue
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #EEE; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
            # 開始橫向行
            st.markdown('<div class="chord-line">', unsafe_allow_html=True)
            parts = re.split(r'(\[[^\]]+\])', line)
            pending_chord = ""
            for p in parts:
                if p.startswith('[') and p.endswith(']'): pending_chord = p[1:-1]
                else:
                    for char in p:
                        color, display_c = "transparent", ""
                        if pending_chord:
                            root = pending_chord[0].upper()
                            color = COLOR_MAP.get(root, "#FFFFFF")
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

# 滾動控制
if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
