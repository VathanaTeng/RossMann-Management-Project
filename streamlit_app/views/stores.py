import pandas as pd
import requests
import streamlit as st

API = "http://localhost:8000"
st.title("店舗情報管理")

#method is what you want to do: "GET" (read), "POST" (add), "PUT" (edit), "DELETE"
#path is which data, such as "/stores" or "/stores/453".    
#**kw passes along any extra items, such as json=body (the data to save).
def api(method, path, **kw):
    try:
        r = requests.request(method, API + path, timeout=10, **kw)
    except requests.ConnectionError:
        st.error("バックエンドに接続できません。backendフォルダでuvicorn を起動してください。")
        st.stop()
    if r.status_code >= 400:
        st.error(r.json().get("detail", "エラーが発生しました"))
        return None
    return r.json()


def num(v):                      # 0 = 未設定 として扱う
    return None if not v else float(v)


stores = api("GET", "/stores") or []
df = pd.DataFrame(stores)
LABELS = {'Store': '店舗番号', 'StoreName': '店舗名', 'StoreType': 'タイプ', 'Assortment': '品揃え',
          'CompetitionDistance': '競合までの距離', 'Promo2': 'Promo2', 'Memo': 'メモ'}

tab1, tab2, tab3 = st.tabs(["一覧", "編集・削除", "新規追加"])

with tab1:
    c1, c2 = st.columns(2)
    q = c1.text_input("店舗番号,店舗名で検索")
    types = c2.multiselect("タイプ", sorted(df['StoreType'].dropna().unique()) if len(df) else [])
    view = df.copy()
    if q:
        view = view[view['Store'].astype(str).str.contains(q) | view['StoreName'].fillna('').str.contains(q)]
    if types:
        view = view[view['StoreType'].isin(types)]
    st.caption(f"{len(view)} / {len(df)} 店舗")
    st.dataframe(view.rename(columns=LABELS), hide_index=True, use_container_width=True)

with tab2:
    if not stores:
        st.info("店舗がありません。")
    else:
        sid = st.selectbox("店舗を選ぶ", df['Store'].tolist(), key="edit_sid")
        s = next(x for x in stores if x['Store'] == sid)
        with st.form("edit"):
            name = st.text_input("店舗名", s['StoreName'] or "")
            a, b = st.columns(2)
            stype = a.selectbox("タイプ", list("abcd"), index=list("abcd").index(s['StoreType'] or 'a'))
            assort = b.selectbox("品揃え", list("abc"), index=list("abc").index(s['Assortment'] or 'a'))
            st.caption("数値は 0 = 未設定 です")
            c, d, e = st.columns(3)
            dist = c.number_input("競合までの距離(m)", value=float(s['CompetitionDistance'] or 0))
            cm = d.number_input("競合の開店月", 0, 12, int(s['CompetitionOpenSinceMonth'] or 0))
            cy = e.number_input("競合の開店年", 0, 2100, int(s['CompetitionOpenSinceYear'] or 0))
            p2 = st.checkbox("Promo2に参加", value=bool(s['Promo2']))
            f, g, h = st.columns(3)
            pw = f.number_input("Promo2開始週", 0, 53, int(s['Promo2SinceWeek'] or 0))
            py = g.number_input("Promo2開始年", 0, 2100, int(s['Promo2SinceYear'] or 0))
            pint = h.text_input("Promo2の月（例 Jan,Apr,Jul,Oct）", s['PromoInterval'] or "")
            memo = st.text_area("メモ", s['Memo'] or "")
            if st.form_submit_button("保存"):
                body = dict(StoreName=name, StoreType=stype, Assortment=assort,
                            CompetitionDistance=num(dist), CompetitionOpenSinceMonth=num(cm),
                            CompetitionOpenSinceYear=num(cy), Promo2=int(p2),
                            Promo2SinceWeek=num(pw), Promo2SinceYear=num(py),
                            PromoInterval=pint or None, Memo=memo)
                if api("PUT", f"/stores/{sid}", json=body):
                    st.success("保存しました")
        with st.expander("この店舗を削除する"):
            ok = st.checkbox(f"店舗{sid}を削除してよい")
            if st.button("削除", disabled=not ok):
                if api("DELETE", f"/stores/{sid}"):
                    st.success("削除しました。画面を更新してください。")

with tab3:
    with st.form("new"):
        n_id = st.number_input("店舗番号", 1, 100000, int(df['Store'].max() + 1) if len(df) else 1)
        n_name = st.text_input("店舗名")
        a, b = st.columns(2)
        n_type = a.selectbox("タイプ", list("abcd"))
        n_assort = b.selectbox("品揃え", list("abc"))
        n_dist = st.number_input("競合までの距離(m)（0 = 未設定）", value=0.0)
        n_memo = st.text_area("メモ")
        if st.form_submit_button("追加"):
            body = dict(Store=int(n_id), StoreName=n_name, StoreType=n_type, Assortment=n_assort,
                        CompetitionDistance=num(n_dist), Promo2=0, Memo=n_memo)
            if api("POST", "/stores", json=body):
                st.success("追加しました。画面を更新してください。")
