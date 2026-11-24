
# Login functionality
# what i need to do next if having time, 
# make it locked after 3 failed attempts, and make it so that the user can only try again after a certain amount of time has passed.
import hmac
import time
#test git
import streamlit as st

st.set_page_config(page_title="売上予測", layout="wide")

#st.session_state.setdefault("attempts", 0) same as this
if "attempts" not in st.session_state:
    st.session_state["attempts"] =0
    

if "lockout_time" not in st.session_state:
    st.session_state["lockout_time"] = 0

MAX_ATTEMPTS = 3
LOCKOUT_DURATION = [60, 120, 300, 600, 3600]  # 60, 120, and 300 seconds

def login():

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.title("ログイン")
        with st.form("login"):
            pw = st.text_input("パスワード", type="password")
            ok = st.form_submit_button("入る", use_container_width=True)
        if ok:
            try:
                correct = st.secrets["APP_PASSWORD"]
            except Exception:
                st.error("パスワード設定（.streamlit/secrets.toml）が見つかりません。")
                return
            if hmac.compare_digest(pw.encode(), str(correct).encode()):
                st.session_state["logged_in"] = True
                st.session_state["attempts"] = 0
                st.rerun()
#hmac.compare_digest is a function that compares two strings in a way that is resistant to timing attacks. It returns True if the strings are equal, and False otherwise. In this case, it is used to compare the entered password (pw) with the correct password stored in st.secrets["APP_PASSWORD"].               
            else:
                st.session_state["attempts"] +=1
                time.sleep(1)
                if st.session_state["attempts"] >= MAX_ATTEMPTS:
                    st.session_state["lockout_time"] = time.time() + LOCKOUT_DURATION[min(st.session_state["attempts"] - MAX_ATTEMPTS, len(LOCKOUT_DURATION) -1)]
                    st.warning("ログイン試行回数が上限に達しました。")  
                    
                else:
                    st.warning(f"パスワードが違います。残り{MAX_ATTEMPTS - st.session_state['attempts']}回")
            
#st.session_state.get("logged_in") means that if the key "logged_in" exists in the session state dictionary, it will return its value (True or False). If the key does not exist, it will return None. This is a way to check if the user is logged in or not.
if st.session_state.get("logged_in"):
    pg = st.navigation([
        st.Page("views/forecast.py", title="売上予測", default=True),
        st.Page("views/stores.py", title="店舗管理"),
    ])
    with st.sidebar:
        if st.button("ログアウト"):
            st.session_state["logged_in"] = False
            st.rerun()
        elif st.session_state["attempts"] >= MAX_ATTEMPTS:
            st.warning("ローグされたため、ログインできません。")
            
    
else:
    pg = st.navigation([st.Page(login, title="ログイン")], position="hidden")
    
#pg.run() is a method that runs the navigation and displays the selected page. It should be called after defining the pages and their titles. In this case, it will either run the forecast and store management pages if the user is logged in, or it will run the login page if the user is not logged in.
pg.run()
