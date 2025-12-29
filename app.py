import streamlit as st
import pandas as pd
import sqlite3
import json
import time
import re
import os
from datetime import datetime
from PIL import Image
import io
import google.generativeai as genai
from github import Github

# ==========================================
# 0. 頁面配置
# ==========================================
st.set_page_config(page_title="'Amis/Pangcah AI", layout="wide", page_icon="🦅")

# ==========================================
# 🛡️ 安全防護層 (Security Gate) - 新增區域
# ==========================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

def verify_and_login(key):
    """驗證 API Key 有效性並登入"""
    if not key: return False
    try:
        genai.configure(api_key=key)
        genai.list_models() # 嘗試連線測試
        return True
    except:
        return False

# 如果尚未通過驗證，顯示鎖定畫面並停止程式
if not st.session_state.authenticated:
    st.title("🛡️ 'Amis/Pangcah AI 系統鎖定")
    st.markdown("### ⚠️ 存取受限 / Restricted Access")
    st.info("本系統包含核心戰略數據與原始碼，請輸入授權金鑰以解鎖。")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        input_key = st.text_input("Google API Key", type="password", help="請輸入 Gemini API Key")
    with col2:
        st.write("") # 排版用
        st.write("")
        if st.button("🚀 解鎖系統", use_container_width=True):
            if verify_and_login(input_key):
                st.session_state.authenticated = True
                st.session_state.api_key = input_key
                st.success("✅ 驗證通過！正在載入核心模組...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 金鑰無效，拒絕存取。")
    
    st.divider()
    st.caption("🔒 Security Protocol Active. Unauthorized access is prohibited.")
    st.stop() # <--- ⛔ 關鍵指令：在此停止，保護下方程式碼不被執行

# ==========================================
# ⬇️ 以下為您的原版程式碼 (Original Code) ⬇️
# ==========================================

# 取得通過驗證的 API Key (取代原本側邊欄輸入)
api_key = st.session_state.api_key 

@st.cache_resource(show_spinner=False)
def get_verified_models(key):
    """
    自動偵測使用者帳號可用的模型列表，並優先排序 Flash 版本
    """
    if not key: return []
    try:
        genai.configure(api_key=key)
        # 取得所有支援 generateContent 的模型
        ms = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 排序邏輯：優先找 'flash'，其次是 'pro'
        ms.sort(key=lambda x: 0 if 'flash' in x else (1 if 'pro' in x else 2))
        return ms
    except:
        return []

def init_db():
    with sqlite3.connect('amis_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS amis_sentences (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            amis_text TEXT,
                            chinese_text TEXT,
                            english_text TEXT,
                            pos_tags TEXT,
                            created_at TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pos_tags (
                            tag TEXT PRIMARY KEY,
                            description TEXT)''')
        conn.commit()

# 初始化
init_db()
genai.configure(api_key=api_key)
available_models = get_verified_models(api_key)

# ==========================================
# 側邊欄與功能頁面
# ==========================================
st.sidebar.title("🦅 阿美語 AI 戰略系統")
st.sidebar.caption(f"🔑 已安全連線")
st.sidebar.caption(f"🤖 Model: {available_models[0] if available_models else 'N/A'}")

page = st.sidebar.radio("功能模組", ["🦅 AI 採礦機", "📖 單詞辭典", "🍳 AI 廚師", "🎓 語料匯出"])

# --- 功能 1: AI 採礦機 ---
if page == "🦅 AI 採礦機":
    st.title("🦅 阿美語語料採礦機")
    
    with st.form("mining_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1: amis_input = st.text_area("阿美語 (Amis)")
        with c2: chn_input = st.text_area("中文翻譯")
        
        c3, c4 = st.columns(2)
        with c3: eng_input = st.text_input("英文翻譯 (選填)")
        with c4: pos_input = st.text_input("語法標記 (POS)")
        
        submitted = st.form_submit_button("💾 存入資料庫")
        if submitted:
            if amis_input and chn_input:
                with sqlite3.connect('amis_data.db') as conn:
                    conn.execute("INSERT INTO amis_sentences (amis_text, chinese_text, english_text, pos_tags, created_at) VALUES (?,?,?,?,?)",
                                 (amis_input, chn_input, eng_input, pos_input, datetime.now()))
                st.success("✅ 語料已寫入資料庫！")
            else:
                st.error("⚠️ 阿美語和中文翻譯為必填欄位。")

# --- 功能 2: 單詞辭典 (保留您的 st.data_editor) ---
elif page == "📖 單詞辭典":
    st.title("📖 語法標籤與單詞定義")
    st.info("💡 您可以直接在下方表格中編輯定義，修改後請點擊「儲存變更」。")

    with sqlite3.connect('amis_data.db') as conn:
        df_tags = pd.read_sql("SELECT * FROM pos_tags", conn)

    # 保留您原版的高級編輯功能
    et = st.data_editor(df_tags, num_rows="dynamic", use_container_width=True)

    if st.button("💾 儲存變更 (Save Changes)"):
        with sqlite3.connect('amis_data.db') as conn:
            # 保留您原版的儲存邏輯
            et.to_sql('pos_tags', conn, if_exists='replace', index=False)
        st.success("✅ 辭典已更新！資料庫結構已同步。")

# --- 功能 3: AI 廚師 ---
elif page == "🍳 AI 廚師":
    st.title("🍳 AI 廚師：自動化分析")
    
    selected_model = st.selectbox("選擇模型引擎", available_models) if available_models else None
    
    query = st.text_input("請輸入想分析的阿美語句子：")
    if st.button("執行 AI 分析"):
        if not selected_model:
            st.error("無法偵測到可用的 Gemini 模型，請檢查 API Key。")
        else:
            with st.spinner(f"👨‍🍳 廚師 ({selected_model}) 正在備料分析中..."):
                model = genai.GenerativeModel(selected_model)
                prompt = f"""
                你是阿美語語言學專家。請分析以下句子：'{query}'。
                請提供：
                1. 中文翻譯
                2. 英文翻譯
                3. 構詞分析 (Morphological Analysis) 與語法標籤 (POS)
                請用 Markdown 表格呈現。
                """
                response = model.generate_content(prompt)
                st.markdown(response.text)

# --- 功能 4: 語料匯出 (保留您的 Roadmap 與 Tabs) ---
elif page == "🎓 語料匯出":
    st.title("🎓 語料匯出與戰略進度")
    
    # 保留您原本的戰略 Roadmap 文字
    with st.container():
        st.info("🗺️ **AI 戰略發展路線圖 (Roadmap)**")
        c1, c2, c3 = st.columns(3)
        with c1: 
            st.markdown("### 🚩 第一階段 (目前)")
            st.caption("RAG 檢索增強生成")
            st.write("✅ **Python 採礦機**\n✅ **Gemini 廚師**\n🛠️ **目標**：持續擴充語料庫。")
        with c2: 
            st.markdown("### 🏔️ 第二階段 (1,000+)")
            st.caption("微調 (Fine-tuning)")
            st.write("🛠️ **目標**：初步建立專屬模型。")
        with c3: 
            st.markdown("### 城堡🏰 第三階段 (10,000+)")
            st.caption("原生模型 (Native LLM)")
            st.write("🛠️ **目標**：阿美語原生推理能力。")
    
    st.divider()
    
    # 保留您原本的 Tabs 分頁
    tab1, tab2 = st.tabs(["📝 句型", "📖 單詞"])
    
    with tab1:
        with sqlite3.connect('amis_data.db') as conn: 
            df = pd.read_sql("SELECT * FROM amis_sentences", conn)
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.download_button("📥 下載句型語料 (CSV)", df.to_csv(index=False).encode('utf-8'), "amis_sentences.csv")
            
    with tab2:
        with sqlite3.connect('amis_data.db') as conn: 
            df_tags = pd.read_sql("SELECT * FROM pos_tags", conn)
        st.dataframe(df_tags, use_container_width=True)
        if not df_tags.empty:
            st.download_button("📥 下載語法標籤 (CSV)", df_tags.to_csv(index=False).encode('utf-8'), "pos_tags.csv")

# ==========================================
# GitHub 自動備份 (保留原版邏輯)
# ==========================================
st.sidebar.divider()
st.sidebar.subheader("☁️ GitHub 備份中心")

def backup_to_github():
    # 這裡的 key 設為 sidebar unique key，避免衝突
    token = st.sidebar.text_input("GitHub Token", type="password", key="gh_token_input")
    repo_name = st.sidebar.text_input("Repo (e.g. user/repo)", key="gh_repo_input")
    
    if st.sidebar.button("立即備份至 GitHub"):
        if not token or not repo_name:
            st.sidebar.error("請輸入 Token 與 Repo 名稱")
            return
        
        try:
            g = Github(token)
            repo = g.get_repo(repo_name)
            
            with open('amis_data.db', 'rb') as f:
                db_content = f.read()
            
            file_path = "amis_data.db"
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(file_path, f"Auto-backup {datetime.now()}", db_content, contents.sha)
                st.sidebar.success(f"✅ 更新成功！(Time: {datetime.now().strftime('%H:%M')})")
            except:
                repo.create_file(file_path, "Initial backup", db_content)
                st.sidebar.success("✅ 建立並備份成功！")
                
        except Exception as e:
            st.sidebar.error(f"備份失敗: {e}")

backup_to_github()

# 安全登出功能
if st.sidebar.button("🔒 安全登出"):
    st.session_state.authenticated = False
    st.session_state.api_key = ""
    st.rerun()
