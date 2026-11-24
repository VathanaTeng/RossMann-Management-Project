"""Feature building for the Rossmann app. Reproduces the notebook's X_train columns."""
import pandas as pd

MONTH_MAP = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
             7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

# Fallback if the scaler was fit on a numpy array (same order as X_train)
NUMERIC_COLS = ['Store', 'Promo', 'SchoolHoliday', 'CompetitionDistance',
                'Num_Month_CompetitionOpen', 'Promo2', 'Promo2Open',
                'IsPromo2Active', 'Day', 'Month', 'Year', 'WeekOfYear']


def add_store_date_features(df):
    yr, mo = df['CompetitionOpenSinceYear'], df['CompetitionOpenSinceMonth']
    months = (df['Year'] - yr) * 12 + (df['Month'] - mo)
    df['Num_Month_CompetitionOpen'] = months.where(yr.notna() & (months > 0), 0)

    start = df['Promo2SinceYear'] + (df['Promo2SinceWeek'] - 1) / 52
    cur = df['Year'] + (df['WeekOfYear'] - 1) / 52
    df['Promo2Open'] = ((cur - start) * 12).where(df['Promo2'] == 1, 0).clip(lower=0).fillna(0)

    df['IsPromo2Active'] = [
        int(isinstance(iv, str) and MONTH_MAP[m] in iv.split(','))
        for iv, m in zip(df['PromoInterval'], df['Month'])
    ]
    return df


def build_features(df, store_info, scaler, final_cols):
    """df needs: Store, Date (datetime), Promo, SchoolHoliday, StateHoliday."""
    numeric_cols = list(getattr(scaler, 'feature_names_in_', NUMERIC_COLS))
    df = df.merge(store_info, on='Store', how='left')
    df['Day'] = df['Date'].dt.day
    df['Month'] = df['Date'].dt.month
    df['Year'] = df['Date'].dt.year
    df['WeekOfYear'] = df['Date'].dt.isocalendar().week.astype(int)
    df['DayOfWeek'] = df['Date'].dt.dayofweek + 1
    df = add_store_date_features(df)
    # The notebook filled the 3 missing distances with the max before scaling
    df['CompetitionDistance'] = df['CompetitionDistance'].fillna(
        store_info['CompetitionDistance'].max())
    df['StateHoliday'] = df['StateHoliday'].astype(str)
    df = pd.get_dummies(df, columns=['DayOfWeek', 'StateHoliday', 'StoreType', 'Assortment'])
    df[numeric_cols] = scaler.transform(df[numeric_cols])
    return df.reindex(columns=final_cols, fill_value=0).astype(float)
