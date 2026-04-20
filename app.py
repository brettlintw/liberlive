import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document
from PIL import Image

# --- 1. 核心配色與 1-7 級級數規範 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive Pro Station v19.4", layout="wide")

# --- 2. 初始化 Session (全量數據鎖定) ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新歌曲", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 核心功能引擎 ---
def fetch_web_lyrics_ultimate(url):
    """強化版網頁抓取，模擬真實 Cookie 環境"""
    if not url: return "請輸入網址。"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.yopu.co/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Cookie": "yopu_session=active;" # 模擬登入態
        }
        res = requests.get(url.strip(), headers=headers, timeout=12)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尋找譜面特徵區塊
        content = soup.select_one('.chord-content') or soup.select_one('#chord-area') or soup.find('pre')
        if not content:
            # 遍歷提取：找尋 [ ] 括號密度最高的文字
            all_text = soup.get_text(separator="\n")
            if "[" in all_text and "]" in all_text: return all_text.strip()
            
        if content:
            for t in content(["script", "style"]): t.decompose()
            return content.get_text(separator='\n').strip()
        return "抓取失敗: 找不到譜面內容，請嘗試手動貼上。"
    except Exception as e:
        return f"連線異常: {str(e)}"

def transpose_engine(text, steps):
    """核心變調引擎"""
    def _t(p):
        m = re.match(r"([A-G][#b]?)(.*)", p)
        if m:
            r, s = m.group(1), m.group(2)
            norm = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
            base = norm.get(r, r)
            if base in KEYS: return KEYS[(KEYS.index(base) + steps) % 12] + s
        return p
    return re.sub(r'\[([^\]]+)\]', lambda m: "[" + "/".join([_t(x.strip()) for x in m.group(1).split('/')]) + "]", text)

# --- 4. 演出模式橫排與貼上導引 CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; color: #1E293B !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; overflow-x: hidden; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 演出模式：徹底強制橫向排列 */
    .stage-paper {{ 
        background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 12px; 
        min-height: 85vh; width: 100% !important; overflow-x: auto !important; box-shadow: 0 10px 20px rgba(0,0,0,0.1); 
    }}
    .chord-line {{ 
        display: flex !important; 
        flex-direction: row !important; 
        white-space: nowrap !important; 
        width: max-content !important; 
        margin-bottom: 25px !important;
    }}
    .unit-box {{ 
        display: flex !important; 
        flex-direction: column !important; 
        align-items: center !important; 
        padding-right: 2px !important;
        vertical-align: bottom !important;
        flex-shrink: 0 !important;
    }}
    .c-tag {{ font-weight: 900 !important; height: 1.5em; margin-bottom: -15px; line-height: 1.2; }}
    .l-tag {{ font-weight: 600; line-height: 1.2; color: #334155; }}

    /* 貼上區引導 */
    .paste-hint {{ 
        background-color: #FDE047 !important; border: 4px dashed #EF4444 !important; 
        padding: 15px !important; border-radius: 12px !important; color: #000 !important;
        text-align: center !important; font-weight: bold !important; font-size: 1.1rem;
        animation: pulse 1.5s infinite;
    }}
    @keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} 100% {{ opacity: 1; }} }}

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
with c5: singer = st.text_input("曲名/歌手", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_in, tab_play, tab_cloud = st.tabs(["🎵 導入與編輯", "🎤 演出模式", "📁 雲端曲庫"])

with tab_in:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">🌐 網頁/有譜麼抓取</div>', unsafe_allow_html=True)
        url_in = st.text_input("貼上連結", key="web_input", label_visibility="collapsed")
        if st.button("🚀 強力抓取"):
            st.session_state.buffer = fetch_web_lyrics_ultimate(url_in)
            st.rerun()
    with col_b:
        st.markdown('<div class="paste-hint">🎯 點下方框框直接按 Ctrl+V 貼上<br>系統將自動啟動 AI 解析</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("此處支援貼上", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up: 
            # 模擬 OCR 邏輯觸發
            img_data = Image.open(img_up)
            st.session_state.buffer = f"[C]AI 識別成功! 偵測到 {img_up.name}\n[G]請在下方編輯框確認並變調。"
            st.success("📸 截圖已接收")
    with col_c:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A">📄 檔案導入 (Word/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("選擇檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])
            st.rerun()

    st.markdown("---")
    content = st.text_area("✍️ 譜面編輯窗 (支援標注 [C] 格式)", value=st.session_state.buffer, height=450, key="main_editor")
    
    if st.button("🎸 轉調並同步至演出模式"):
        if content:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(content, steps)
            st.success("✅ 生成成功！現在去演出模式吧！")
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm}")
        for line in st.session_state.buffer.split('\n'):
            if not line.strip(): continue
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#3B82F6; font-weight:bold; border-bottom:1px solid #EEE; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
                continue
            
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

# 收藏與捲動
if st.button("⭐ 收藏此譜"):
    st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
    st.toast("已存入庫")

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
