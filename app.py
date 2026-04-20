import streamlit as st
import re
import io
import requests
from bs4 import BeautifulSoup
from docx import Document

# --- 1. 核心規範與配色 ---
KEYS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
COLOR_MAP = {
    'C': '#FF0000', 'D': '#FF8C00', 'E': '#FFD700', 'F': '#00FF00', 
    'G': '#1E90FF', 'A': '#0000FF', 'B': '#A020F0'
}

st.set_page_config(page_title="Liberlive AI Station v18.1", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新曲目", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 強化版抓取與變調函數 ---
def fetch_web_lyrics(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        # 深度定位有譜麼內容
        chord_area = soup.select_one('.chord-content') or soup.select_one('pre') or soup.select_one('.post-content')
        if chord_area:
            # 移除所有內嵌標籤，只留純文字內容
            for tag in chord_area.find_all(['script', 'style', 'head']): tag.decompose()
            return chord_area.get_text('\n', strip=True)
        return "找不到譜面內容，請嘗試手動複製貼上。"
    except Exception as e:
        return f"抓取失敗: {str(e)}"

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

# --- 4. CSS 注入 ---
theme_choice = st.sidebar.radio("🌗 視覺主題", ["普通白晝", "演出黑夜", "低對比紅黑"], key="app_theme")
text_color, paper_bg, app_bg = ("#000", "#FFF", "#F8F")
if theme_choice == "演出黑夜": app_bg, text_color, paper_bg = ("#000", "#FFF", "#000")
elif theme_choice == "低對比紅黑": app_bg, text_color, paper_bg = ("#1a0000", "#C00", "#1a0000")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {app_bg} !important; color: {text_color} !important; }}
    .block-container {{ padding-top: 0rem !important; }}
    header, footer {{ visibility: hidden !important; }}
    .input-card {{ background: #f1f5f9; padding: 20px; border-radius: 10px; border-left: 5px solid #1E3A8A; margin-bottom: 10px; color: #333; }}
    .stage-paper {{ background: {paper_bg} !important; border: 2px solid #1E3A8A; padding: 30px; border-radius: 15px; min-height: 80vh; }}
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 2px; }}
    .c-tag {{ font-weight: 900; height: 1.5em; margin-bottom: -10px; }}
    .l-tag {{ color: {text_color} !important; font-weight: 600; }}
    </style>
    """, unsafe_allow_html=True)

# --- 5. 介面呈現 ---
with st.sidebar:
    st.session_state.yt_url = st.text_input("YouTube 練習連結", value=st.session_state.yt_url)
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
with c5: singer = st.text_input("歌曲名稱", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_in, tab_play, tab_cloud = st.tabs(["📥 多路導入編輯", "🎤 演出模式", "📁 雲端曲庫"])

with tab_in:
    # 採用卡片式並列佈局
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div class="input-card">🌐 網頁/有譜麼抓取</div>', unsafe_allow_html=True)
        url_input = st.text_input("貼上譜面連結", key="web_url", label_visibility="collapsed")
        if st.button("🔍 執行抓取"):
            st.session_state.buffer = fetch_web_lyrics(url_input)
            st.rerun()
            
    with col_b:
        st.markdown('<div class="input-card">📸 圖片/截圖 識別</div>', unsafe_allow_html=True)
        img_file = st.file_uploader("上傳譜面照片或截圖", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if img_file: st.session_state.buffer = "[C]截圖識別[G]範例內容"
        
    with col_c:
        st.markdown('<div class="input-card">📄 檔案導入 (Word/TXT)</div>', unsafe_allow_html=True)
        doc_file = st.file_uploader("匯入現有譜面文件", type=['docx','txt'], label_visibility="collapsed")
        if doc_file:
            if doc_file.type == "text/plain": st.session_state.buffer = doc_file.read().decode("utf-8")
            else: st.session_state.buffer = "\n".join([p.text for p in Document(doc_file).paragraphs])

    st.markdown("---")
    # 使用 Form 鎖定編輯區，解決沒反應的問題
    with st.form("editor_form"):
        st.markdown("**✍️ 歌詞與 [和弦] 編輯窗口**")
        editor_text = st.text_area("內容", value=st.session_state.buffer, height=400, label_visibility="collapsed")
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            submitted = st.form_submit_state = st.form_submit_button("🚀 執行智能變調並生成譜面")
        with btn_c2:
            clean_btn = st.form_submit_button("🧹 僅保留和弦 (刪除歌詞)")

        if submitted:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = transpose_engine(editor_text, steps)
            st.rerun()
            
        if clean_btn:
            lines = editor_text.split('\n')
            st.session_state.buffer = "\n".join(["".join(re.findall(r'\[[^\]]+\]', l)) for l in lines])
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm} | {beat}")
        for line in st.session_state.buffer.split('\n'):
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#1D4ED8; font-weight:bold; border-bottom:1px solid #DDD; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
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
    if st.button("⭐ 收藏當前譜面"):
        st.session_state.db[singer] = {"buffer": st.session_state.buffer, "meta": st.session_state.meta.copy()}
    st.markdown("---")
    for name in st.session_state.db.keys():
        if st.button(f"📖 載入: {name}"):
            st.session_state.buffer = st.session_state.db[name]['buffer']
            st.session_state.meta = st.session_state.db[name]['meta']
            st.rerun()

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
