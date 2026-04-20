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

st.set_page_config(page_title="Liberlive AI Station v18.0", layout="wide")

# --- 2. 初始化 Session ---
if 'db' not in st.session_state: st.session_state.db = {}
if 'buffer' not in st.session_state: st.session_state.buffer = ""
if 'yt_url' not in st.session_state: st.session_state.yt_url = ""
if 'meta' not in st.session_state: 
    st.session_state.meta = {"singer": "新曲目", "arranger": "Brett", "bpm": 65, "beat": "4/4", "orig": "E", "target": "C"}

# --- 3. 強化版抓取函數 ---
def fetch_web_lyrics(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        res = requests.get(url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        if res.status_code != 200: return f"連線失敗 (HTTP {res.status_code})"
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 針對『有譜麼』及常見譜庫的深度選擇器
        content = (
            soup.select_one('div.chord-content') or 
            soup.select_one('pre.chord-content') or 
            soup.select_one('div.post-content') or
            soup.select_one('#chord-area') or
            soup.find('pre')
        )
        
        if content:
            # 清理 HTML 標籤，保留換行
            text = content.decode_contents()
            text = text.replace('<br/>', '\n').replace('<br>', '\n')
            clean_text = BeautifulSoup(text, 'html.parser').get_text()
            return clean_text
        return "抓取成功但找不到譜面區塊，請確認網址是否正確。"
    except Exception as e:
        return f"抓取異常: {str(e)}"

def transpose_logic(chord_text, steps):
    def _trans_single(p):
        m = re.match(r"([A-G][#b]?)(.*)", p)
        if m:
            root, suffix = m.group(1), m.group(2)
            norm = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
            r = norm.get(root, root)
            if r in KEYS:
                idx = (KEYS.index(r) + steps) % 12
                return KEYS[idx] + suffix
        return p
    return "/".join([_trans_single(x.strip()) for x in chord_text.split('/')])

# --- 4. 側邊欄與視覺設定 ---
with st.sidebar:
    st.markdown("### 🎬 影音控制")
    st.session_state.yt_url = st.text_input("YouTube 網址", value=st.session_state.yt_url)
    if st.session_state.yt_url: st.video(st.session_state.yt_url)
    st.markdown("---")
    theme_choice = st.radio("🌗 視覺主題", ["普通白晝", "演出黑夜", "低對比紅黑"], key="app_theme")
    c_size = st.slider("和弦字體", 10, 80, 24)
    l_size = st.slider("歌詞字體", 10, 80, 28)
    scroll_spd = st.slider("📜 捲動速度", 0, 20, 0)

# --- 5. CSS 注入 ---
text_color, paper_bg, border_color, app_bg = ("#000000", "#FFFFFF", "#1E3A8A", "#F8FAFC")
if theme_choice == "演出黑夜":
    app_bg, text_color, paper_bg, border_color = ("#000000", "#FFFFFF", "#000000", "#440000")
elif theme_choice == "低對比紅黑":
    app_bg, text_color, paper_bg, border_color = ("#1a0000", "#CC0000", "#1a0000", "#660000")

st.markdown(f"""
    <style>
    .stApp {{ background-color: {app_bg} !important; color: {text_color} !important; }}
    .block-container {{ padding-top: 0rem !important; }}
    header, footer {{ visibility: hidden !important; }}
    section[data-testid="stSidebar"] {{ background-color: #1E3A8A !important; border-right: 2px solid #FDE047; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    .stage-paper {{ background: {paper_bg} !important; border: 2px solid {border_color}; padding: 30px; border-radius: 15px; min-height: 85vh; width: 100%; }}
    .chord-row {{ display: flex; flex-wrap: wrap; line-height: 2.8; margin-bottom: 12px; }}
    .unit-box {{ display: flex; flex-direction: column; align-items: center; margin-right: 2px; }}
    .c-tag {{ font-weight: 900; height: 1.5em; margin-bottom: -10px; }}
    .l-tag {{ color: {text_color} !important; font-weight: 600; }}
    </style>
    """, unsafe_allow_html=True)

# --- 6. 置頂設定列 ---
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ok = st.selectbox("原調", KEYS, index=KEYS.index(st.session_state.meta['orig']))
with c2: tk = st.selectbox("目標調", KEYS, index=KEYS.index(st.session_state.meta['target']))
with c3: bpm = st.number_input("BPM", 20, 250, st.session_state.meta['bpm'])
with c4: beat = st.text_input("拍號", value=st.session_state.meta['beat'])
with c5: singer = st.text_input("歌曲名稱", value=st.session_state.meta['singer'])
st.session_state.meta.update({"orig": ok, "target": tk, "bpm": bpm, "beat": beat, "singer": singer})

tab_edit, tab_play, tab_cloud = st.tabs(["🎵 導入編輯", "🎤 演出模式", "📁 雲端曲庫"])

with tab_edit:
    st.markdown("### 📥 多路導入與清理工具")
    in_col1, in_col2, in_col3 = st.columns(3)
    with in_col1:
        web_url = st.text_input("🌐 網頁連結", placeholder="https://www.yopu.co/...")
        if st.button("🔍 抓取內容"):
            if web_url: 
                st.session_state.buffer = fetch_web_lyrics(web_url)
                st.rerun()
    with in_col2:
        if st.button("🧹 刪除所有歌詞 (僅保留和弦)"):
            if st.session_state.buffer:
                # 邏輯：保留 [和弦] 標籤，刪除標籤外的所有非換行文字
                def remove_lyrics(text):
                    # 先把換行符標記起來
                    text = text.replace('\n', ' [BR] ')
                    # 匹配 [和弦] 或 [BR]
                    tokens = re.findall(r'\[[^\]]+\]', text)
                    return "\n".join(tokens).replace('[BR]', '').replace('  ', ' ')
                
                # 簡易清理：只保留和弦括號內容
                clean_chords = ""
                for line in st.session_state.buffer.split('\n'):
                    chords = re.findall(r'\[[^\]]+\]', line)
                    clean_chords += "".join(chords) + "\n"
                st.session_state.buffer = clean_chords
                st.success("歌詞已清除！")
                st.rerun()
    with in_col3:
        up_doc = st.file_uploader("📄 檔案導入", type=['docx','txt'], label_visibility="collapsed")
        if up_doc:
            if up_doc.type == "text/plain": st.session_state.buffer = up_doc.read().decode("utf-8")
            else:
                doc = Document(up_doc)
                st.session_state.buffer = "\n".join([p.text for p in doc.paragraphs])
    
    st.markdown("---")
    # 編輯器區塊
    current_text = st.text_area("✍️ 譜面編輯視窗", value=st.session_state.buffer, height=350, key="editor_v18")
    
    if st.button("🚀 執行變調並生成譜面"):
        if current_text:
            steps = (KEYS.index(tk) - KEYS.index(ok)) % 12
            st.session_state.buffer = re.sub(r'\[([^\]]+)\]', lambda m: f"[{transpose_logic(m.group(1), steps)}]", current_text)
            st.rerun()

with tab_play:
    st.markdown(f'<div class="stage-paper">', unsafe_allow_html=True)
    if st.session_state.buffer:
        st.markdown(f"#### {singer} | BPM: {bpm}")
        for line in st.session_state.buffer.split('\n'):
            if line.strip().startswith('['):
                st.markdown(f'<div style="color:#3B82F6; font-weight:bold; border-bottom:1px solid #333; margin:10px 0;">📍 {line}</div>', unsafe_allow_html=True)
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
            st.rerun()

if 'scroll_spd' in locals() and scroll_spd > 0:
    st.markdown(f"<script>if(window.si)clearInterval(window.si);window.si=setInterval(()=>window.scrollBy(0,{scroll_spd}),50);</script>", unsafe_allow_html=True)
