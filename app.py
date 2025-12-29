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
# 0. 頁面配置 (物理鎖定樣式)
# ==========================================
st.set_page_config(page_title="'Amis/Pangcah AI", layout="wide", page_icon="🦅")

# ==========================================
# 🔒 安全閘門 (這是唯一新增的區塊)
# ==========================================
# 說明：這段程式碼會阻擋後續所有內容的載入，直到驗證通過。
# 通過後，它會設定 session_state.api_key，這樣您原本的程式碼就能直接抓到 key。

if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if not st.session_state.auth_status:
    st.title("🔒 系統鎖定保護")
    st.markdown("### 'Amis/Pangcah AI 核心系統")
    st.info("請輸入 Google API Key 以解除鎖定並存取完整功能。")
    
    input_key = st.text_input("API Key", type="password", help="輸入您的 Gemini API Key")
    
    if st.button("🚀 解鎖進入"):
        if not input_key:
            st.warning("請輸入金鑰。")
        else:
            try:
                # 測試金鑰是否有效
                genai.configure(api_key=input_key)
                genai.list_models() 
                
                # 驗證成功：存入狀態並重整
                st.session_state.auth_status = True
                st.session_state.api_key = input_key # 這會自動對應到您原版程式碼的 sidebar value
                st.success("✅ 驗證成功！正在啟動核心引擎...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ 金鑰無效或連線失敗: {e}")
    
    st.divider()
    st.caption("🔒 Unauthorized Access Prohibited.")
    st.stop() # ⛔ 【關鍵指令】這裡會強制停止程式，保護下方程式碼不被執行

# ==========================================
# ⬇️ 以下是您上傳的 100% 原版程式碼 (未做任何修改) ⬇️
# ==========================================

# ==========================================
# 1. 核心引擎 (物理鎖定)
# ==========================================

@st.cache_resource(show_spinner=False)
def get_verified_models(api_key):
    """
    自動偵測使用者帳號可用的模型列表，並優先排序 Flash 版本
    """
    if not api_key: return []
    try:
        genai.configure(api_key=api_key)
        # 取得所有支援 generateContent 的模型
        ms = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 排序邏輯：優先找 'flash'，其次是 'pro'
        # 這樣可以確保自動選到 gemini-1.5-flash 或 gemini-flash-latest 等存在於列表中的模型
        ms.sort(key=lambda x: 0 if 'flash' in x else (1 if 'pro' in x else 2))
        
        return ms if ms else ["models/gemini-1.5-flash"]
    except: return ["models/gemini-1.5-flash"]

def run_query(sql, params=(), fetch=False):
    """資料庫執行引擎"""
    try:
        with sqlite3.connect('amis_data.db', timeout=30) as conn:
            c = conn.cursor()
            c.execute(sql, params)
            if fetch: return c.fetchall()
            conn.commit()
            return True
    except: return [] if fetch else False

def reorder_ids(table):
    """物理 ID 防撞重編"""
    rows = run_query(f"SELECT rowid FROM {table} ORDER BY created_at ASC", fetch=True)
    if not rows: return 0
    for idx, (rid,) in enumerate(rows):
        run_query(f"UPDATE {table} SET id = ? WHERE rowid = ?", (idx + 1, rid))
    run_query(f"DELETE FROM sqlite_sequence WHERE name=?", (table,))
    run_query(f"INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, len(rows)))
    return len(rows)

def sync_vocabulary(sentence):
    """自動單字同步"""
    words = re.findall(r"\w+", sentence.lower())
    for word in words:
        exists = run_query("SELECT id FROM vocabulary WHERE LOWER(amis) = ?", (word,), fetch=True)
        if not exists:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_query("INSERT INTO vocabulary (amis, note, created_at) VALUES (?, ?, ?)", (word, f"來自句型: {sentence}", now))

def is_linguistically_relevant(keyword, target_word):
    """
    [絕對防禦版] 詞法過濾器 (2025-12-20 Final Fix)
    """
    k = keyword.lower().strip()
    t = target_word.lower().strip()
    if k == t: return True
    if len(k) == 1: return False 
    if t.startswith(k) or t.endswith(k): return True
    if k in t and len(k) > 2: return True
    return False

# [終極修復] 導航版雲端備份功能
def backup_to_github():
    """終極導航版：精準連線倉庫並備份"""
    token = st.secrets.get("general", {}).get("GITHUB_TOKEN") or st.secrets.get("GITHUB_TOKEN")
    if not token:
        st.error("❌ 未偵測到 GitHub Token。")
        return False
    try:
        g = Github(token)
        user_name = "shuhsienling1002-oss"
        repo_name = "Amis_AI_Project"
        repo = g.get_user(user_name).get_repo(repo_name)
        file_path = "amis_data.db"
        with open(file_path, "rb") as f:
            content = f.read()
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, f"Mobile update: {datetime.now()}", content, contents.sha)
            st.toast("☁️ 雲端備份成功！資料已回傳 GitHub。", icon="✅")
            return True
        except Exception:
            repo.create_file(file_path, f"Initial DB: {datetime.now()}", content)
            st.toast("☁️ 雲端備份成功！(已建立新資料檔)", icon="✅")
            return True
    except Exception as e:
        st.error(f"⚠️ 連線失敗。請確認 Token 權限。錯誤: {str(e)}")
        return False

# [資料瘦身術] 改用精簡格式，大幅減少 Token 消耗
def get_full_database_context():
    """
    讀取整個資料庫，但使用 '資料瘦身術' (CSV style) 來節省 Token。
    讓 AI 即使讀取大量資料也不容易爆額度。
    """
    ctx = "【全量阿美語資料庫 (Compact Mode)】\n"
    
    # 1. 提取所有詞彙 (精簡版)
    # 格式：阿美語,中文,詞性 (去除冗言贅字)
    vocab = run_query("SELECT amis, chinese, part_of_speech FROM vocabulary", fetch=True)
    if vocab:
        ctx += "==VOCABULARY==\n"
        for v in vocab:
            # 如果欄位是 None，轉為空字串
            a = v[0] if v[0] else ""
            c = v[1] if v[1] else ""
            p = v[2] if v[2] else ""
            ctx += f"{a},{c},{p}\n"
    
    # 2. 提取所有句型 (精簡版)
    sents = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs", fetch=True)
    if sents:
        ctx += "\n==SENTENCES==\n"
        for s in sents:
            sa = s[0] if s[0] else ""
            sc = s[1] if s[1] else ""
            ctx += f"{sa} || {sc}\n"
            
    return ctx

def get_expert_knowledge(query_text, direction="AtoZ"):
    """
    雙向 RAG 檢索邏輯
    """
    if not query_text: return None, [], [], "" 
    clean_q = query_text.strip().rstrip('.?!')
    
    if direction == "AtoZ":
        sql = "SELECT output_sentencepattern_chinese FROM sentence_pairs WHERE LOWER(REPLACE(output_sentencepattern_amis, '.', '')) = ? LIMIT 1"
    else:
        sql = "SELECT output_sentencepattern_amis FROM sentence_pairs WHERE LOWER(output_sentencepattern_chinese) = ? LIMIT 1"
    sentence_match = run_query(sql, (clean_q.lower(),), fetch=True)
    full_trans = sentence_match[0][0] if sentence_match else None
    
    query_words = re.findall(r"\w+", query_text.lower())
    words_data, sentences_data, rag_context_parts = [], [], []
    
    try:
        with sqlite3.connect('amis_data.db') as conn:
            for word in query_words:
                matched_definitions = [] 
                should_use_semantic = True
                if len(word) == 1: should_use_semantic = False

                if direction == "AtoZ":
                    res_vocab = run_query("SELECT amis, chinese, part_of_speech FROM vocabulary WHERE LOWER(amis) LIKE ? LIMIT 100", (f"%{word}%",), fetch=True)
                else:
                    res_vocab = run_query("SELECT amis, chinese, part_of_speech FROM vocabulary WHERE chinese LIKE ? LIMIT 100", (f"%{word}%",), fetch=True)
                
                valid_vocab_count = 0
                for w in res_vocab:
                    if direction == "AtoZ" and not is_linguistically_relevant(word, w[0]): continue 
                    if valid_vocab_count >= 50: break 
                    words_data.append({"amis": w[0], "chinese": w[1], "pos": w[2]})
                    rag_context_parts.append(f"[阿美語資料庫] 阿美語: {w[0]} | 中文: {w[1]} (詞性: {w[2]})")
                    if w[1] and should_use_semantic: matched_definitions.append(w[1])
                    valid_vocab_count += 1
                
                if direction == "AtoZ":
                    res_sent_direct = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE LOWER(output_sentencepattern_amis) LIKE ? LIMIT 30", (f"%{word}%",), fetch=True)
                else:
                    res_sent_direct = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE output_sentencepattern_chinese LIKE ? LIMIT 30", (f"%{word}%",), fetch=True)
                
                res_sent_semantic = []
                if direction == "AtoZ" and matched_definitions and should_use_semantic:
                    for distinct_def in list(set(matched_definitions))[:3]:
                        core_def = distinct_def.split('(')[0].split('（')[0].strip()
                        if len(core_def) > 0:
                            found = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE output_sentencepattern_chinese LIKE ? LIMIT 20", (f"%{core_def}%",), fetch=True)
                            res_sent_semantic.extend(found)
                
                all_raw_sents = res_sent_direct + res_sent_semantic
                valid_sent_count, processed_sents = 0, set()
                
                for s in all_raw_sents:
                    amis_s, chinese_s = s[0], s[1]
                    if (amis_s, chinese_s) in processed_sents: continue
                    processed_sents.add((amis_s, chinese_s))
                    pass_check = False
                    sent_words = re.findall(r"\w+", amis_s.lower())
                    for sw in sent_words:
                        if is_linguistically_relevant(word, sw): pass_check = True; break
                    if not pass_check and direction == "AtoZ" and should_use_semantic:
                        for distinct_def in list(set(matched_definitions))[:3]:
                             core_def = distinct_def.split('(')[0].split('（')[0].strip()
                             if core_def and core_def in chinese_s: pass_check = True; break
                    if not pass_check: continue
                    if {"amis": amis_s, "chinese": chinese_s} not in sentences_data:
                        if valid_sent_count >= 20: break
                        sentences_data.append({"amis": amis_s, "chinese": chinese_s})
                        rag_context_parts.append(f"[阿美語資料庫] 例句(阿美語): {amis_s} | (中文): {chinese_s}")
                        valid_sent_count += 1
    except: pass
    
    if len(rag_context_parts) > 80:
        rag_context_parts = rag_context_parts[:80]
        rag_context_parts.append("(System: 參考資料過多，已截取前 80 筆)")
    rag_prompt = "\n【阿美語語料庫檢索結果 (Amis Corpus)】:\n" + "\n".join(set(rag_context_parts)) if rag_context_parts else ""
    return full_trans, words_data, sentences_data, rag_prompt

# ==========================================
# 2. 介面模組 (還原所有說明文字)
# ==========================================

def assistant_system(api_key, model_selection):
    st.title("◎ AI 智慧翻譯機")
    
    DREAM_MODEL_NAME = "🧬 Pangcah/'Amis_language_mode"
    # [更新] 在這裡動態獲取模型列表
    available_models = get_verified_models(api_key)
    is_pangcah_mode = (model_selection == DREAM_MODEL_NAME)
    
    missing_word_protocol = """
    【特殊翻譯模式：缺詞標記 (Missing Word Protocol)】
    1. 僅限使用提供的資料庫內容。
    2. **關鍵規則**：若中文詞彙（如地名、名詞）在資料庫中找不到對應阿美語，請**直接保留中文**，不要自行翻譯或用拼音。
    3. 輸出範例：若無 '花蓮'，翻譯 '我在花蓮' -> 'I 花蓮 kako'。
    """
    
    # [模式分流]
    if is_pangcah_mode:
        # ==========================================
        # 模式 A: Pangcah 全庫分析模式
        # ==========================================
        
        # [關鍵修正] 自動挑選最佳的 Flash 模型 (Auto-Select)
        # 邏輯：從 available_models 裡找出名字含 'flash' 的，選第一個。
        # 這樣不管 Google 叫它 'gemini-1.5-flash' 還是 'gemini-flash-latest'，我們都抓得到。
        flash_models = [m for m in available_models if 'flash' in m]
        if flash_models:
            proxy_model = flash_models[0] # 自動選第一個 Flash 模型
        else:
            proxy_model = available_models[0] if available_models else "models/gemini-1.5-flash" # 備案
        
        st.info(f"🦅 **Pangcah 模式 (全庫思維)**：正在使用 **{proxy_model}** 進行深度分析。(已啟用資料瘦身技術以節省流量)")
        
        if "pangcah_ready" not in st.session_state: st.session_state.pangcah_ready = False
        if "pangcah_context" not in st.session_state: st.session_state.pangcah_context = ""

        if not st.session_state.pangcah_ready:
            st.markdown("#### 1. 準備階段")
            st.write("請先讓模型進行資料庫深度掃描。")
            if st.button("🚀 執行 Pangcah 資料分析 (讀取全庫)", type="primary"):
                with st.spinner("正在閱讀並壓縮資料庫..."):
                    ctx = get_full_database_context()
                    st.session_state.pangcah_context = ctx
                    st.session_state.pangcah_ready = True
                st.rerun()
        
        else:
            st.success("✅ 資料庫分析完成！Pangcah 模型已就緒。")
            if st.button("🔄 重新分析資料庫"):
                st.session_state.pangcah_ready = False
                st.rerun()
            
            st.divider()
            st.markdown("#### 2. 測試與互動")
            
            user_input = st.text_area("在此輸入您要翻譯或分析的阿美語/中文內容：", height=150)
            
            if st.button("🦅 送出測試 (執行翻譯或語法分析)", type="primary"):
                if not user_input:
                    st.warning("請輸入內容")
                elif not api_key:
                    st.warning("請設定 Google API Key")
                else:
                    try:
                        with st.spinner(f"Pangcah AI 正在思考 (Core: {proxy_model})..."):
                            genai.configure(api_key=api_key)
                            m = genai.GenerativeModel(proxy_model)
                            
                            formatting_instruction = """
                            【排版特別指令 (Visual Formatting)】
                            1. 使用 `### 🦅 阿美語翻譯` 作為小標題。
                            2. **關鍵翻譯句子**：請使用 `#` (H1) 加上 `:blue[...]` (藍色) 將整句包起來，使其最大最顯眼。
                            3. 範例：
                               ### 🦅 阿美語翻譯
                               # :blue[I 花蓮 kako.]
                               
                               ### 📊 語法分析
                               ...
                            """
                            
                            full_prompt = f"{st.session_state.pangcah_context}\n\n{missing_word_protocol}\n\n{formatting_instruction}\n\n【指令】\n你現在是 Pangcah/'Amis 原生語言模型。已閱讀上方【全量資料庫(Compact)】。\n請對使用者輸入進行精確翻譯與分析。\n若資料庫無此詞，請保留中文。\n\n使用者輸入: {user_input}"
                            
                            # 自動重試機制
                            try:
                                response = m.generate_content(full_prompt)
                            except Exception as e:
                                if "429" in str(e):
                                    st.toast("⏳ 流量調節中 (429)，系統休息 10 秒後自動重試...", icon="🛡️")
                                    time.sleep(10)
                                    response = m.generate_content(full_prompt)
                                else:
                                    raise e

                            if response:
                                st.markdown("### 🦅 Pangcah 模型分析結果：")
                                st.write(response.text)
                    except Exception as e: st.error(f"AI 錯誤：{e}")

    else:
        # ==========================================
        # 模式 B: 標準 RAG 模式
        # ==========================================
        actual_model = model_selection
        mode = st.radio("翻譯方向", ["阿美語 ⮕ 中文", "中文 ⮕ 阿美語"], horizontal=True)
        direction = "AtoZ" if mode == "阿美語 ⮕ 中文" else "ZtoA"
        if "rag_result" not in st.session_state: st.session_state.rag_result = None
        if "last_query" not in st.session_state: st.session_state.last_query = ""
        
        st.subheader("輸入文字")
        with st.form("translation_search"):
            q = st.text_area(f"在此輸入句子", height=150)
            submit_search = st.form_submit_button("🚀 1. 查詢語料庫", type="primary")
        if submit_search and q:
            f, w, s, r = get_expert_knowledge(q, direction)
            st.session_state.rag_result = (f, w, s, r)
            st.session_state.last_query = q
        st.divider()
        if st.session_state.rag_result:
            f, w, s, r = st.session_state.rag_result
            if f: st.success(f"### 🏆 專家翻譯：\n**{f}**")
            if w:
                with st.expander(f"📚 相關單詞 ({len(w)} 筆)", expanded=True):
                    for item in w: st.markdown(f"- **{item['amis']}** ⮕ {item['chinese']} ({item['pos']})")
            if s:
                with st.expander(f"🗣️ 相關例句 ({len(s)} 筆)", expanded=True):
                    for item in s: st.markdown(f"> **{item['amis']}**\n> ({item['chinese']})")
            st.divider()
            st.markdown("### 🤖 AI 協同分析")
            if st.button("🦅 執行 AI 語法分析"):
                if not api_key: st.warning("請設定 API Key")
                else:
                    try:
                        with st.spinner(f"正在呼叫 {actual_model} ..."):
                            genai.configure(api_key=api_key)
                            m = genai.GenerativeModel(actual_model)
                            final_prompt = f"{r}\n\n{missing_word_protocol}\n\n請根據以上提供的【阿美語語料庫】(Amis Corpus)，對以下句子進行詳細語法與語意分析。\n若遇到資料庫沒有的詞，請依據【缺詞標記協議】保留中文。\n\n使用者輸入: {st.session_state.last_query}"
                            response = m.generate_content(final_prompt)
                            if response:
                                st.markdown("#### 🦅 AI 分析報告：")
                                st.write(response.text)
                    except Exception as e: st.error(f"⚠️ AI 錯誤：{e}")

# ==========================================
# 3. 主控台
# ==========================================

def main():
    with sqlite3.connect('amis_data.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS sentence_pairs (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP, output_sentencepattern_amis TEXT, output_sentencepattern_chinese TEXT, output_sentencepattern_english TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS vocabulary (id INTEGER PRIMARY KEY AUTOINCREMENT, amis TEXT, chinese TEXT, english TEXT, part_of_speech TEXT, note TEXT, created_at TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS pos_tags (tag_name TEXT PRIMARY KEY, sort_order INTEGER DEFAULT 0)')
    st.sidebar.title("🦅 系統選單")
    
    # [新增] 資料庫救援中心
    with st.sidebar.expander("📂 資料庫救援中心", expanded=True):
        st.warning("⚠️ 警告：若雲端資料遺失，請在此上傳本機備份檔 (.db) 進行還原。")
        uploaded_db = st.file_uploader("上傳 amis_data.db", type=["db"])
        if uploaded_db is not None:
            if st.button("🚨 確認覆蓋並還原資料庫"):
                with open("amis_data.db", "wb") as f:
                    f.write(uploaded_db.getbuffer())
                st.success("✅ 資料庫還原成功！請重新整理頁面。")
                time.sleep(2)
                st.rerun()

    with st.sidebar.container():
        st.info("☁️ **行動同步中心**")
        if st.sidebar.button("🔄 立即將資料備份回 GitHub", type="primary"):
            backup_to_github()
    
    # [新增] 嘗試從 Secrets 讀取 GOOGLE_API_KEY
    default_key = st.secrets.get("GOOGLE_API_KEY", "")
    key = st.sidebar.text_input("Google API Key", type="password", value=st.session_state.get("api_key", default_key))
    
    if key != st.session_state.get("api_key"): 
        st.session_state["api_key"] = key; st.cache_resource.clear(); st.rerun()
    
    # 這裡會自動去 Google 查詢可用的模型，所以不管叫什麼名字都能抓到
    raw_ms = get_verified_models(key)
    ms = []
    if raw_ms:
        ms = raw_ms.copy()
        DREAM_MODEL = "🧬 Pangcah/'Amis_language_mode"
        ms.insert(0, DREAM_MODEL)
    model = st.sidebar.selectbox("請選擇 AI 模型", ms, index=0) if ms else None
    
    st.sidebar.divider()
    page = st.sidebar.radio("功能模式", ["🏠 系統首頁", "◎ AI 智慧助理", "🔐 句型：專家資料庫", "📖 單詞：語料庫管理", "🏷️ 語法標籤管理", "🎓 語料匯出"])
    
    if page == "🏠 系統首頁":
        st.markdown("<h1 style='text-align: center; font-size: 5rem;'>🦅</h1>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>'Amis / Pangcah AI</h1>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<p style='text-align: center;'>歡迎回來，船長。系統已就緒。</p>", unsafe_allow_html=True)

    elif page == "◎ AI 智慧助理": assistant_system(key, model)

    elif page == "🔐 句型：專家資料庫":
        st.title("🔐 專家句型資料庫")
        with st.form("add_new_s"):
            c1, c2, c3 = st.columns(3); a, c, e = c1.text_input("阿美語"), c2.text_input("中文"), c3.text_input("英語")
            if st.form_submit_button("➕ 儲存新句型"):
                if a and c: 
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    run_query("INSERT INTO sentence_pairs (output_sentencepattern_amis, output_sentencepattern_chinese, output_sentencepattern_english, created_at) VALUES (?,?,?,?)", (a, c, e, now))
                    sync_vocabulary(a); reorder_ids("sentence_pairs"); backup_to_github(); st.rerun()
        with sqlite3.connect('amis_data.db') as conn: df = pd.read_sql("SELECT * FROM sentence_pairs ORDER BY id DESC", conn)
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True)
        if st.button("💾 儲存修改"):
            with sqlite3.connect('amis_data.db') as conn: edited_df.to_sql('sentence_pairs', conn, if_exists='replace', index=False)
            reorder_ids("sentence_pairs"); backup_to_github(); st.rerun()

    elif page == "📖 單詞：語料庫管理":
        st.title("📖 單詞語料庫管理")
        raw_tags = [r[0] for r in run_query("SELECT tag_name FROM pos_tags", fetch=True) if r[0]]
        with st.form("add_new_vocab"):
            c1, c2, c4 = st.columns([2, 2, 3])
            a_in, c_in = c1.text_input("阿美語"), c2.text_input("中文")
            p_in = c4.selectbox("詞類", options=raw_tags)
            if st.form_submit_button("➕ 儲存新單詞"):
                if a_in:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    run_query("INSERT INTO vocabulary (amis, chinese, part_of_speech, created_at) VALUES (?,?,?,?)", (a_in, c_in, p_in, now))
                    reorder_ids("vocabulary"); backup_to_github(); st.rerun()
        st.divider()
        with sqlite3.connect('amis_data.db') as conn: df = pd.read_sql("SELECT * FROM vocabulary ORDER BY id DESC", conn)
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic",
            column_config={"part_of_speech": st.column_config.SelectboxColumn("詞類 (搜尋選單)", options=raw_tags, required=True)})
        if st.button("💾 儲存修改"):
            with sqlite3.connect('amis_data.db') as conn: edited_df.to_sql('vocabulary', conn, if_exists='replace', index=False)
            reorder_ids("vocabulary"); backup_to_github(); st.rerun()

    elif page == "🏷️ 語法標籤管理":
        st.title("🏷️ 標籤管理 (Tag Alignment)")
        
        # [智慧更名工具]
        with st.expander("⚡ 智慧更名工具 (連動更新單詞)", expanded=True):
            current_tags = [r[0] for r in run_query("SELECT tag_name FROM pos_tags", fetch=True) if r[0]]
            c1, c2 = st.columns(2)
            old_tag = c1.selectbox("選擇要修改的舊標籤", options=current_tags)
            new_tag_name = c2.text_input("輸入新名稱")
            if st.button("🔄 執行更名與連動更新"):
                if old_tag and new_tag_name and old_tag != new_tag_name:
                    try:
                        with sqlite3.connect('amis_data.db') as conn:
                            conn.execute("UPDATE vocabulary SET part_of_speech = ? WHERE part_of_speech = ?", (new_tag_name, old_tag))
                            conn.execute("INSERT OR IGNORE INTO pos_tags (tag_name) VALUES (?)", (new_tag_name,))
                            conn.execute("DELETE FROM pos_tags WHERE tag_name = ?", (old_tag,))
                        st.success(f"✅ 成功將 '{old_tag}' 更名為 '{new_tag_name}'，並更新了相關單詞！")
                        backup_to_github(); time.sleep(1.5); st.rerun()
                    except Exception as e: st.error(f"更新失敗: {e}")
        st.divider()

        # [新增標籤]
        with st.form("t"):
            nt = st.text_input("新增標籤名稱")
            if st.form_submit_button("新增"): 
                run_query("INSERT OR REPLACE INTO pos_tags (tag_name) VALUES (?)", (nt,)) 
                backup_to_github(); st.rerun()

        # ==========================================
        # 🔥 自適應新增「備註」欄位 + 排序控制
        # ==========================================
        with sqlite3.connect('amis_data.db') as conn: 
            df_tags = pd.read_sql("SELECT * FROM pos_tags", conn)

        # 1. 自適應結構：補上 description 欄位
        if "description" not in df_tags.columns:
            df_tags["description"] = "" 

        # 2. 欄位排序：確保備註在右側
        cols_order = ["tag_name", "description", "sort_order"]
        existing_cols = [c for c in cols_order if c in df_tags.columns]
        remaining_cols = [c for c in df_tags.columns if c not in existing_cols]
        df_tags = df_tags[existing_cols + remaining_cols]

        # 3. 編輯器配置
        et = st.data_editor(
            df_tags, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "tag_name": st.column_config.TextColumn("語法標籤名稱", disabled=True), 
                "description": st.column_config.TextColumn(
                    "備註 (LLM 定義校準)", 
                    help="在此說明此標籤與大語言模型通用定義的差異",
                    width="large" 
                ),
                "sort_order": st.column_config.NumberColumn("排序權重")
            }
        )

        if st.button("💾 儲存標籤與備註"):
            with sqlite3.connect('amis_data.db') as conn: 
                et.to_sql('pos_tags', conn, if_exists='replace', index=False)
            backup_to_github(); st.success("已存檔！資料庫結構已自動更新。"); st.rerun()

    elif page == "🎓 語料匯出":
        st.title("🎓 語料匯出與戰略進度")
        with st.container():
            st.info("🗺️ **AI 戰略發展路線圖 (Roadmap)**")
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown("### 🚩 第一階段 (目前)"); st.caption("RAG 檢索增強生成"); st.write("✅ **Python 採礦機**\n✅ **Gemini 廚師**\n🛠️ **目標**：持續擴充語料庫。")
            with c2: st.markdown("### 🏔️ 第二階段 (1,000+)"); st.caption("微調 (Fine-tuning)"); st.write("🛠️ **目標**：初步建立專屬模型。")
            with c3: st.markdown("### 城堡🏰 第三階段 (10,000+)"); st.caption("原生模型 (Native LLM)"); st.write("🛠️ **目標**：阿美語原生推理能力。")
        st.divider()
        tab1, tab2 = st.tabs(["📝 句型", "📖 單詞"])
        with tab1:
            with sqlite3.connect('amis_data.db') as conn: df = pd.read_sql("SELECT * FROM sentence_pairs", conn)
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 下載 JSONL", df.to_json(orient="records", lines=True, force_ascii=False), "amis_sentences.jsonl")
        with tab2:
            with sqlite3.connect('amis_data.db') as conn: df_v = pd.read_sql("SELECT * FROM vocabulary", conn)
            st.dataframe(df_v, use_container_width=True)
            st.download_button("📥 下載 JSONL", df_v.to_json(orient="records", lines=True, force_ascii=False), "amis_vocabulary.jsonl")

if __name__ == "__main__": main()
