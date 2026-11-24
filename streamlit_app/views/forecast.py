from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from xgboost import XGBRegressor

from features import build_features

MODEL_DIR = Path(__file__).parent.parent / 'model'


@st.cache_resource
def load_assets():
    model = XGBRegressor()
    model.load_model(str(MODEL_DIR / 'rossmann_xgb.json'))
    scaler = joblib.load(MODEL_DIR / 'scaler.pkl')
    cols = joblib.load(MODEL_DIR / 'columns.pkl')
    store_info = pd.read_csv(MODEL_DIR / 'store_info.csv')
    acc = pd.read_csv(MODEL_DIR / 'accuracy_per_store_val.csv').set_index('Store').iloc[:, 0]
    return model, scaler, cols, store_info, acc


model, scaler, cols, store_info, acc = load_assets()

st.title("店舗売上予測")


with st.sidebar:
    st.header("予測の設定")
    store = st.selectbox("店舗（ストア番号）", sorted(store_info['Store'].unique()))
    start = st.date_input("開始日", pd.Timestamp('2015-09-18'))
    days = st.slider("予測する日数", 7, 365, 28)
    promo_mode = st.radio("プロモーションの予定", ["プロモなし", "月〜金プロモ", "隔週プロモ"])
    st.caption("実際の予定が分かる場合は、右の表で日ごとに修正してください。")

dates = pd.date_range(pd.Timestamp(start), periods=days)
sched = pd.DataFrame({'Store': store, 'Date': dates})
dow = sched['Date'].dt.dayofweek          # 月曜 = 0
if promo_mode == "月〜金プロモ":
    sched['Promo'] = (dow < 5).astype(int)
elif promo_mode == "隔週プロモ":
    week = sched['Date'].dt.isocalendar().week.astype(int)
    sched['Promo'] = ((dow < 5) & (week % 2 == 0)).astype(int)
else:
    sched['Promo'] = 0
sched['SchoolHoliday'] = 0
sched['StateHoliday'] = '0'
sched['Open'] = (dow != 6).astype(int)    # 日曜は休業にする

st.subheader("スケジュール（編集できます）")
st.caption("プロモ・学校休暇・営業：1 = あり／営業、0 = なし／休業　　祝日区分：0 = なし、a・b・c = 祝日の種類")
edited = st.data_editor(
    sched, hide_index=True, use_container_width=True, height=250,
    disabled=['Store', 'Date'],
    column_config={
        'Store': st.column_config.NumberColumn("店舗"),
        'Date': st.column_config.DateColumn("日付", format="YYYY-MM-DD"),
        'Promo': st.column_config.SelectboxColumn("プロモ", options=[0, 1]),
        'SchoolHoliday': st.column_config.SelectboxColumn("学校休暇", options=[0, 1]),
        'StateHoliday': st.column_config.SelectboxColumn("祝日区分", options=['0', 'a', 'b', 'c']),
        'Open': st.column_config.SelectboxColumn("営業", options=[0, 1]),
    })

# ---------- 予測 ----------
edited['Date'] = pd.to_datetime(edited['Date'])
X = build_features(edited[['Store', 'Date', 'Promo', 'SchoolHoliday', 'StateHoliday']].copy(),
                   store_info, scaler, cols)
pred = np.clip(model.predict(X), 0, None)
pred[edited['Open'].values == 0] = 0
out = pd.DataFrame({'日付': edited['Date'], '予測売上': pred.round(0)})

# ---------- 結果 ----------
open_days = out.loc[out['予測売上'] > 0, '予測売上']
c1, c2, c3 = st.columns(3)
c1.metric("予測売上の合計", f"{out['予測売上'].sum():,.0f}")
c2.metric("営業日の1日平均", f"{open_days.mean():,.0f}" if len(open_days) else "0")
if store in acc.index:
    c3.metric("この店舗の予測精度（検証データ）", f"{acc.loc[store]:.1f}%")
else:
    c3.metric("この店舗の予測精度（検証データ）", "なし")

if store in acc.index and acc.loc[store] < 80:
    st.warning(f"店舗{store}は、検証データでの精度が{acc.loc[store]:.0f}%と低めです。"
               "売上のパターンが特殊なため、この予測は参考程度にしてください。")

st.subheader("日別の予測")
st.line_chart(out.set_index('日付'))

st.subheader("週別の合計（日別より安定しています）")
weekly = out.set_index('日付').resample('W')['予測売上'].sum().round(0)
st.bar_chart(weekly)

if pd.Timestamp(start) > pd.Timestamp('2015-09-17'):
    st.warning("このモデルが学習したデータより先の期間です。先の日付ほど精度は下がり、"
               "プロモの予定が外れると誤差も増えます。日別の数値は目安として見てください。")

st.download_button("予測結果をCSVでダウンロード",
                   out.to_csv(index=False).encode('utf-8-sig'),
                   file_name=f"forecast_store_{store}.csv", mime="text/csv")
