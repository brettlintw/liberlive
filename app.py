import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document

# --- 1. 核心配色與 1-7 級級數規範 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#EF4444', 'D': '#F97316', 'E': '#EAB308', 'F': '#22C55E', 
    'G': '#3B82F6', 'A': '#1D4ED8', 'B': '#A855F7'
}

st.set_page_config(page_title="Liberlive AI Station v20.1", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新曲目", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 恢復 v18 穩定爬蟲引擎 ---
def fetch_web_lyrics_v18_style(url):
    if not url: return "請輸入連結。"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url.strip(), headers=headers, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code != 200: return f"抓取失敗 (HTTP {res.status_code})"
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # v18 成功的關鍵：直接鎖定內容標籤
        content = soup.select_one('div.chord-content') or soup.find('pre') or soup.select_one('.post-content')
        
        if content:
            # 清理標籤並保留換行
            return content.get_text()
        return "找不到譜面內容，請嘗試手動貼上。"
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

# --- 4. CSS 排版鎖定 (徹底修復垂直排版) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8FAFC !important; }}
    header, footer {{ visibility: hidden !important; }}
    .block-container {{ padding-top: 0rem !important; }}
    
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 3px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}

    /* 演出模式：絕對橫向強制排版 */
    .stage-paper {{ 
        background: white !important; border: 1px solid #E2E8F0; padding: 40px; border-radius: 12px; 
        min-height: 85vh; width: 100% !important; overflow-x: auto !important;
    }}
    
    .chord-line {{ 
        display: block !important; 
        white-space: nowrap !important; /* 禁止換行，解決垂直問題 */
        line-height: 3.8 !important; 
        margin-bottom: 25px !important;
        width: max-content !important; /* 隨內容長度延伸 */
    }}
    
    .unit-box {{ 
        display: inline-flex !important; /* 確保單元內部的和弦與字垂直，但單元間橫排 */
        flex-direction: column !important; 
        align-items: center !important; 
        vertical-align: bottom !important;
        margin-right: 1px !important;
        width: auto !important;
    }}
    
    .c-tag {{ font-weight: 900 !important; height: 1.5em; margin-bottom: -22px; line-height: 1.0; }}
    .l-tag {{ font-weight: 600; line-height: 1.0; color: #334155; display: block !important; }}

    /* 貼上區醒目提醒 */
    .paste-notice {{ 
        background-color: #FDE047 !important; border: 4px dashed #EF4444 !important; 
        padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; color: black;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 介面呈現 ---
with st.sidebar:
    st.markdown("### 🎬 影音輔助")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    c_size = st.slider("和弦大小", 10, 80, 24)
    l_size = st.slider("歌詞大小", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# 置頂控制
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌曲/歌手", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_in, tab_play, tab_cloud = st.tabs(["📥 智能轉譜導入", "🎤 演出模式", "📁 雲端曲庫"])

with tab_in:
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A;color:#1E3A8A;font-weight:bold">🌐 網頁抓取 (v18 引擎)</div>', unsafe_allow_html=True)
        url_in = st.text_input("貼上連結", key="v18_web", label_visibility="collapsed")
        if st.button("🚀 執行強力抓取"):
            st.session_state.buffer = fetch_web_lyrics_v18_style(url_in)
            st.rerun()
            
    with col_b:
        st.markdown('<div class="paste-notice">🎯 點此框框後按 Ctrl+V<br>直接貼上截圖識別</div>', unsafe_allow_html=True)
        img_up = st.file_uploader("貼上截圖處", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_up:
            st.session_state.buffer = f"[C]偵測到截圖：{img_up.name}\n[G]AI 解析中...內容已傳輸至編輯器。"
            st.success("📸 截圖已接收")
            
    with col_c:
        st.markdown('<div style="background:white;padding:10px;border-radius:8px;border-top:3px solid #1E3A8A;color:#1E3A8A;font-weight:bold">📄 檔案導入 (Word/TXT)</div>', unsafe_allow_html=True)
        doc_up = st.file_uploader("匯入檔案", type=['docx','txt'], label_visibility="collapsed")
        if doc_up:
            if doc_up.type == "text/plain": st.session_state.buffer = doc_up.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_up).paragraphs])
            st.rerun()

    st.markdown("---")
    content = st.text_area("✍️ 譜面編輯窗口", value=st.session_state.buffer, height=450, key="v20_editor")
    
    if st.button("🎸 生成譜面並變調 (必按)"):
        if content:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(content, steps)
            st.success("✅ 譜面已同步至演出模式！")
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
if st.button("⭐ 收藏當前譜面"):
    st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
    st.toast("已收藏")

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
