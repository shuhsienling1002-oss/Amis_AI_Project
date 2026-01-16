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
# 🔒 安全閘門
# ==========================================
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if not st.session_state.auth_status:
    st.title("🔒 系統鎖定保護")
    st.markdown("### 'Amis/Pangcah AI 核心系統")
    st.info("請輸入系統密碼以解除鎖定並存取完整功能。")
    
    input_key = st.text_input("系統密碼", type="password", help="請輸入訪問密碼")
    
    if st.button("🚀 解鎖進入"):
        if input_key == "836489":
            st.session_state.auth_status = True
            # 解鎖後先嘗試載入 secrets 中的 key，若無則留空讓側邊欄處理
            st.session_state.api_key = st.secrets.get("GOOGLE_API_KEY", "")
            st.success("✅ 驗證成功！正在啟動核心引擎...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 密碼錯誤，拒絕存取。")
    st.divider()
    st.caption("🔒 Unauthorized Access Prohibited.")
    st.stop() 

# ==========================================
# 1. 核心引擎 (物理鎖定)
# ==========================================

@st.cache_resource(show_spinner=False)
def get_verified_models(api_key):
    if not api_key: return []
    try:
        genai.configure(api_key=api_key)
        ms = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        ms.sort(key=lambda x: 0 if 'flash' in x else (1 if 'pro' in x else 2))
        return ms if ms else ["models/gemini-1.5-flash"]
    except: return ["models/gemini-1.5-flash"]

def run_query(sql, params=(), fetch=False):
    try:
        with sqlite3.connect('amis_data.db', timeout=30) as conn:
            c = conn.cursor()
            c.execute(sql, params)
            if fetch: return c.fetchall()
            conn.commit()
            return True
    except: return [] if fetch else False

def reorder_ids(table):
    rows = run_query(f"SELECT rowid FROM {table} ORDER BY created_at ASC", fetch=True)
    if not rows: return 0
    for idx, (rid,) in enumerate(rows):
        run_query(f"UPDATE {table} SET id = ? WHERE rowid = ?", (idx + 1, rid))
    run_query(f"DELETE FROM sqlite_sequence WHERE name=?", (table,))
    run_query(f"INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, len(rows)))
    return len(rows)

def sync_vocabulary(sentence):
    words = re.findall(r"\w+", sentence.lower())
    for word in words:
        exists = run_query("SELECT id FROM vocabulary WHERE LOWER(amis) = ?", (word,), fetch=True)
        if not exists:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run_query("INSERT INTO vocabulary (amis, note, created_at) VALUES (?, ?, ?)", (word, f"來自句型: {sentence}", now))

def is_linguistically_relevant(keyword, target_word):
    k = keyword.lower().strip()
    t = target_word.lower().strip()
    if k == t: return True
    if len(k) == 1: return False 
    if t.startswith(k) or t.endswith(k): return True
    if k in t and len(k) > 2: return True
    return False

def backup_to_github():
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

# ==========================================
# 核心修改區：資料讀取優化 (壓縮 + Note)
# ==========================================

def get_full_database_context():
    """
    【Layer 2 優化：極限壓縮模式】
    為了避免 429 Quota Exceeded，我們將資料格式壓縮為類 CSV 格式。
    格式定義：
    單詞區：Amis,Chinese,POS|Note
    句型區：Amis||Chinese|Note
    """
    ctx = "Dataset:Amis-Note-Compressed\n"
    
    # 1. 讀取單詞 (含 Note)
    vocab = run_query("SELECT amis, chinese, part_of_speech, note FROM vocabulary", fetch=True)
    if vocab:
        ctx += "==V==\n" # V = Vocabulary
        for v in vocab:
            a = v[0] if v[0] else ""
            c = v[1] if v[1] else ""
            p = v[2] if v[2] else ""
            n = v[3] if v[3] else ""
            
            # 壓縮邏輯：若無 note，省去分隔符
            line = f"{a},{c},{p}"
            if n:
                line += f"|{n}"
            ctx += line + "\n"
                
    # 2. 讀取句型 (含 Note)
    sents = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese, note FROM sentence_pairs", fetch=True)
    if sents:
        ctx += "==S==\n" # S = Sentences
        for s in sents:
            sa = s[0] if s[0] else ""
            sc = s[1] if s[1] else ""
            sn = s[2] if s[2] else ""
            
            # 壓縮邏輯
            line = f"{sa}||{sc}"
            if sn:
                line += f"|{sn}"
            ctx += line + "\n"
            
    return ctx

def get_expert_knowledge(query_text, direction="AtoZ"):
    """
    【標準 RAG 模式】
    這裡也必須加入 Note 的讀取，讓一般查詢也能看到備註。
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
                
                # 修改：SQL 加入 note
                if direction == "AtoZ":
                    res_vocab = run_query("SELECT amis, chinese, part_of_speech, note FROM vocabulary WHERE LOWER(amis) LIKE ? LIMIT 100", (f"%{word}%",), fetch=True)
                else:
                    res_vocab = run_query("SELECT amis, chinese, part_of_speech, note FROM vocabulary WHERE chinese LIKE ? LIMIT 100", (f"%{word}%",), fetch=True)
                
                valid_vocab_count = 0
                for w in res_vocab:
                    if direction == "AtoZ" and not is_linguistically_relevant(word, w[0]): continue 
                    if valid_vocab_count >= 50: break 
                    
                    note_content = w[3] if w[3] else ""
                    words_data.append({"amis": w[0], "chinese": w[1], "pos": w[2]})
                    
                    # 提示詞包含備註
                    rag_str = f"[單詞] {w[0]} : {w[1]} ({w[2]})"
                    if note_content:
                        rag_str += f" [備註: {note_content}]"
                    rag_context_parts.append(rag_str)
                    
                    if w[1] and should_use_semantic: matched_definitions.append(w[1])
                    if note_content and should_use_semantic: matched_definitions.append(note_content)
                    valid_vocab_count += 1
                
                # 句型檢索 (維持原樣，但增加數量限制以防爆掉)
                if direction == "AtoZ":
                    res_sent_direct = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE LOWER(output_sentencepattern_amis) LIKE ? LIMIT 20", (f"%{word}%",), fetch=True)
                else:
                    res_sent_direct = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE output_sentencepattern_chinese LIKE ? LIMIT 20", (f"%{word}%",), fetch=True)
                
                res_sent_semantic = []
                # ... (語意搜尋邏輯) ...
                if direction == "AtoZ" and matched_definitions and should_use_semantic:
                    for distinct_def in list(set(matched_definitions))[:2]: # 限制語意搜尋次數
                        core_def = distinct_def.split('(')[0].split('（')[0].strip()
                        if len(core_def) > 0:
                            found = run_query("SELECT output_sentencepattern_amis, output_sentencepattern_chinese FROM sentence_pairs WHERE output_sentencepattern_chinese LIKE ? LIMIT 10", (f"%{core_def}%",), fetch=True)
                            res_sent_semantic.extend(found)
                            
                all_raw_sents = res_sent_direct + res_sent_semantic
                valid_sent_count, processed_sents = 0, set()
                for s in all_raw_sents:
                    amis_s, chinese_s = s[0], s[1]
                    if (amis_s, chinese_s) in processed_sents: continue
                    processed_sents.add((amis_s, chinese_s))
                    # ... (相關性檢查邏輯略，保持簡潔) ...
                    
                    # 直接加入
                    if {"amis": amis_s, "chinese": chinese_s} not in sentences_data:
                        if valid_sent_count >= 15: break
                        sentences_data.append({"amis": amis_s, "chinese": chinese_s})
                        rag_context_parts.append(f"[例句] {amis_s} || {chinese_s}")
                        valid_sent_count += 1
    except: pass
    
    # RAG 結果截斷保護
    if len(rag_context_parts) > 60:
        rag_context_parts = rag_context_parts[:60]
        rag_context_parts.append("(System: 參考資料過多，已智慧截取)")
    rag_prompt = "\n【檢索結果 (RAG)】:\n" + "\n".join(set(rag_context_parts)) if rag_context_parts else ""
    return full_trans, words_data, sentences_data, rag_prompt

# ==========================================
# 2. 介面模組 (包含 429 錯誤處理)
# ==========================================

def assistant_system(api_key, model_selection):
    st.title("◎ AI 智慧翻譯機")
    DREAM_MODEL_NAME = "🧬 Pangcah/'Amis_language_mode"
    available_models = get_verified_models(api_key)
    is_pangcah_mode = (model_selection == DREAM_MODEL_NAME)
    
    missing_word_protocol = """
    【特殊協議】
    1. 僅限使用提供的資料庫。
    2. 資料格式為壓縮版：
       - 單詞區 (==V==): 阿美語,中文,詞性|備註
       - 句型區 (==S==): 阿美語||中文|備註
    3. 若無對應詞，請保留原文。
    """
    
    if is_pangcah_mode:
        flash_models = [m for m in available_models if 'flash' in m]
        if flash_models: proxy_model = flash_models[0]
        else: proxy_model = available_models[0] if available_models else "models/gemini-1.5-flash"
        
        st.info(f"🦅 **Pangcah 模式 (全庫思維)**：正在使用 **{proxy_model}**。(已啟用極限資料壓縮技術)")
        
        if "pangcah_ready" not in st.session_state: st.session_state.pangcah_ready = False
        if "pangcah_context" not in st.session_state: st.session_state.pangcah_context = ""
        if "last_translation" not in st.session_state: st.session_state.last_translation = ""
        if "last_input_text" not in st.session_state: st.session_state.last_input_text = ""

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
            if st.button("🔄 重新分析資料庫 (新增資料後請按此)"):
                st.session_state.pangcah_ready = False
                st.rerun()
            
            st.divider()
            st.markdown("#### 2. 測試與互動")
            
            user_input = st.text_area("在此輸入您要翻譯或分析的阿美語/中文內容：", height=150)
            
            # --- 翻譯按鈕 (含 Error Handling) ---
            if st.button("🦅 執行翻譯 (不含分析)", type="primary"):
                if not user_input:
                    st.warning("請輸入內容")
                elif not api_key:
                    st.warning("請設定 Google API Key")
                else:
                    try:
                        with st.spinner(f"Pangcah AI 正在翻譯 (Core: {proxy_model})..."):
                            genai.configure(api_key=api_key)
                            m = genai.GenerativeModel(proxy_model)
                            formatting_instruction = """
                            【排版指令】
                            1. 使用 `### 🦅 翻譯結果` 作為標題。
                            2. 關鍵句請用 `### :blue[...]` 包裹。
                            3. 請參考資料庫中的 '備註' (|Note) 來增強翻譯準確度，但不一定要顯示出來。
                            """
                            full_prompt = f"{st.session_state.pangcah_context}\n\n{missing_word_protocol}\n\n{formatting_instruction}\n\n使用者輸入: {user_input}"
                            
                            try:
                                response = m.generate_content(full_prompt)
                            except Exception as e:
                                # 429 錯誤處理：自動冷卻 60 秒
                                if "429" in str(e):
                                    wait_time = 60
                                    st.toast(f"⏳ 流量滿載 (429)，系統自動冷卻 {wait_time} 秒...", icon="🧊")
                                    with st.spinner(f"引擎降溫中... 請稍候 {wait_time} 秒"):
                                        time.sleep(wait_time)
                                    response = m.generate_content(full_prompt)
                                else:
                                    raise e

                            if response:
                                st.session_state.last_translation = response.text
                                st.session_state.last_input_text = user_input
                    except Exception as e: st.error(f"AI 錯誤：{e}")

            if st.session_state.last_translation:
                st.markdown("---")
                st.write(st.session_state.last_translation)
                
                st.markdown("#### 🧠 進階指令")
                
                # --- 對話按鈕 (含 Error Handling) ---
                if st.button("💬 模擬對話回應", use_container_width=True):
                    try:
                        with st.spinner("Pangcah AI 正在思考回應..."):
                            genai.configure(api_key=api_key)
                            m = genai.GenerativeModel(proxy_model)
                            chat_prompt = f"""
                            {st.session_state.pangcah_context}
                            【指令】
                            使用者: "{st.session_state.last_input_text}"
                            意思: "{st.session_state.last_translation}"
                            請扮演阿美族耆老(Faki/Fayi)用阿美語回應(附中文)。
                            排版：阿美語請用 `###` 加大。
                            """
                            try:
                                response_chat = m.generate_content(chat_prompt)
                            except Exception as e:
                                if "429" in str(e):
                                    wait_time = 60
                                    st.toast(f"⏳ 流量滿載 (429)，系統自動冷卻 {wait_time} 秒...", icon="🧊")
                                    with st.spinner(f"引擎降溫中... 請稍候 {wait_time} 秒"):
                                        time.sleep(wait_time)
                                    response_chat = m.generate_content(chat_prompt)
                                else:
                                    raise e

                            if response_chat:
                                st.markdown("### 💬 AI 對話回應：")
                                st.write(response_chat.text)
                    except Exception as e: st.error(f"對話錯誤：{e}")

    else:
        # --- 一般模式 (Standard RAG) ---
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
                            final_prompt = f"{r}\n\n{missing_word_protocol}\n\n請根據以上提供的【阿美語語料庫】，對以下句子進行詳細語法與語意分析。\n\n使用者輸入: {st.session_state.last_query}"
                            try:
                                response = m.generate_content(final_prompt)
                            except Exception as e:
                                if "429" in str(e):
                                    time.sleep(60) # 簡易冷卻
                                    response = m.generate_content(final_prompt)
                                else: raise e

                            if response:
                                st.markdown("#### 🦅 AI 分析報告：")
                                st.write(response.text)
                    except Exception as e: st.error(f"⚠️ AI 錯誤：{e}")

# ==========================================
# 3. 主控台
# ==========================================

def main():
    with sqlite3.connect('amis_data.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS sentence_pairs (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TIMESTAMP, output_sentencepattern_amis TEXT, output_sentencepattern_chinese TEXT, note TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS vocabulary (id INTEGER PRIMARY KEY AUTOINCREMENT, amis TEXT, chinese TEXT, english TEXT, part_of_speech TEXT, note TEXT, created_at TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS pos_tags (tag_name TEXT PRIMARY KEY, sort_order INTEGER DEFAULT 0)')
    st.sidebar.title("🦅 系統選單")
    
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
    
    default_key = st.secrets.get("GOOGLE_API_KEY", "")
    key = st.sidebar.text_input("Google API Key", type="password", value=st.session_state.get("api_key", default_key))
    
    if key != st.session_state.get("api_key"): 
        st.session_state["api_key"] = key; st.cache_resource.clear(); st.rerun()
    
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
            c1, c2, c3 = st.columns(3)
            a, c, n = c1.text_input("阿美語"), c2.text_input("中文"), c3.text_input("備註")
            if st.form_submit_button("➕ 儲存新句型"):
                if a and c: 
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    run_query("INSERT INTO sentence_pairs (output_sentencepattern_amis, output_sentencepattern_chinese, note, created_at) VALUES (?,?,?,?)", (a, c, n, now))
                    sync_vocabulary(a); reorder_ids("sentence_pairs"); backup_to_github(); st.rerun()
        with sqlite3.connect('amis_data.db') as conn: df = pd.read_sql("SELECT * FROM sentence_pairs ORDER BY id DESC", conn)
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True)
        
        col_save, col_download = st.columns([1, 4])
        with col_save:
            if st.button("💾 儲存修改"):
                with sqlite3.connect('amis_data.db') as conn: edited_df.to_sql('sentence_pairs', conn, if_exists='replace', index=False)
                reorder_ids("sentence_pairs"); backup_to_github(); st.rerun()
        with col_download:
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 Excel/CSV", csv_data, f'amis_sentences_{datetime.now().strftime("%Y%m%d")}.csv', 'text/csv')

        # --- 新增區塊：上傳覆蓋 ---
        st.markdown("---")
        with st.expander("📂 批次匯入/還原 (上傳 CSV)", expanded=False):
            st.error("⚠️ 危險操作：上傳 CSV 將會【完全覆蓋】並刪除現有的句型資料！")
            uploaded_csv = st.file_uploader("請選擇要上傳的 CSV 檔 (句型)", type=["csv"])
            if uploaded_csv is not None:
                if st.button("🚨 確認覆蓋並匯入句型", type="primary"):
                    try:
                        df_upload = pd.read_csv(uploaded_csv)
                        # 檢查必要欄位
                        required = ['output_sentencepattern_amis', 'output_sentencepattern_chinese']
                        if not all(col in df_upload.columns for col in required):
                            st.error(f"❌ 格式錯誤！CSV 必須包含這些欄位: {required}")
                        else:
                            # 補齊欄位
                            if 'note' not in df_upload.columns: df_upload['note'] = ""
                            if 'created_at' not in df_upload.columns: df_upload['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            with sqlite3.connect('amis_data.db') as conn:
                                df_upload.to_sql('sentence_pairs', conn, if_exists='replace', index=False)
                            reorder_ids("sentence_pairs")
                            backup_to_github()
                            st.success(f"✅ 成功匯入 {len(df_upload)} 筆句型！(舊資料已覆蓋)")
                            time.sleep(2); st.rerun()
                    except Exception as e:
                        st.error(f"匯入失敗: {e}")

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
        
        col_save, col_download = st.columns([1, 4])
        with col_save:
            if st.button("💾 儲存修改"):
                with sqlite3.connect('amis_data.db') as conn: edited_df.to_sql('vocabulary', conn, if_exists='replace', index=False)
                reorder_ids("vocabulary"); backup_to_github(); st.rerun()
        with col_download:
            csv_data = edited_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 Excel/CSV", csv_data, f'amis_vocabulary_{datetime.now().strftime("%Y%m%d")}.csv', 'text/csv')

        # --- 新增區塊：上傳覆蓋 ---
        st.markdown("---")
        with st.expander("📂 批次匯入/還原 (上傳 CSV)", expanded=False):
            st.error("⚠️ 危險操作：上傳 CSV 將會【完全覆蓋】並刪除現有的單詞資料！")
            uploaded_csv_v = st.file_uploader("請選擇要上傳的 CSV 檔 (單詞)", type=["csv"])
            if uploaded_csv_v is not None:
                if st.button("🚨 確認覆蓋並匯入單詞", type="primary"):
                    try:
                        df_upload = pd.read_csv(uploaded_csv_v)
                        # 檢查必要欄位
                        required = ['amis', 'chinese', 'part_of_speech']
                        if not all(col in df_upload.columns for col in required):
                            st.error(f"❌ 格式錯誤！CSV 必須包含這些欄位: {required}")
                        else:
                            # 補齊欄位
                            if 'note' not in df_upload.columns: df_upload['note'] = ""
                            if 'created_at' not in df_upload.columns: df_upload['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            with sqlite3.connect('amis_data.db') as conn:
                                df_upload.to_sql('vocabulary', conn, if_exists='replace', index=False)
                            reorder_ids("vocabulary")
                            backup_to_github()
                            st.success(f"✅ 成功匯入 {len(df_upload)} 筆單詞！(舊資料已覆蓋)")
                            time.sleep(2); st.rerun()
                    except Exception as e:
                        st.error(f"匯入失敗: {e}")

    elif page == "🏷️ 語法標籤管理":
        st.title("🏷️ 標籤管理 (Tag Alignment)")
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
        with st.form("t"):
            nt = st.text_input("新增標籤名稱")
            if st.form_submit_button("新增"): 
                run_query("INSERT OR REPLACE INTO pos_tags (tag_name) VALUES (?)", (nt,)) 
                backup_to_github(); st.rerun()
        with sqlite3.connect('amis_data.db') as conn: 
            df_tags = pd.read_sql("SELECT * FROM pos_tags", conn)
        if "description" not in df_tags.columns: df_tags["description"] = "" 
        cols_order = ["tag_name", "description", "sort_order"]
        existing_cols = [c for c in cols_order if c in df_tags.columns]
        remaining_cols = [c for c in df_tags.columns if c not in existing_cols]
        df_tags = df_tags[existing_cols + remaining_cols]
        et = st.data_editor(
            df_tags, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "tag_name": st.column_config.TextColumn("語法標籤名稱", disabled=True), 
                "description": st.column_config.TextColumn("備註 (LLM 定義校準)", help="在此說明此標籤與大語言模型通用定義的差異", width="large"),
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
            c1, c2 = st.columns(2)
            with c1: st.download_button("📥 下載 JSONL", df.to_json(orient="records", lines=True, force_ascii=False), "amis_sentences.jsonl")
            with c2: st.download_button("📊 下載 CSV (Excel)", df.to_csv(index=False).encode('utf-8-sig'), "amis_sentences.csv", "text/csv")
        with tab2:
            with sqlite3.connect('amis_data.db') as conn: df_v = pd.read_sql("SELECT * FROM vocabulary", conn)
            st.dataframe(df_v, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1: st.download_button("📥 下載 JSONL", df_v.to_json(orient="records", lines=True, force_ascii=False), "amis_vocabulary.jsonl")
            with c2: st.download_button("📊 下載 CSV (Excel)", df_v.to_csv(index=False).encode('utf-8-sig'), "amis_vocabulary.csv", "text/csv")

if __name__ == "__main__": main()
