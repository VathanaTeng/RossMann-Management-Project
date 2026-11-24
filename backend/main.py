#One analogy for the whole file: the backend is a records office. The SQLite file is the filing cabinet, FastAPI is the clerk at the counter, and Streamlit is the customer who comes with requests.


"""店舗情報管理API (FastAPI + SQLite)"""
import sqlite3
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
#base set up where the data is stored ('backend' folder) and the database file is 'stores.db'. The seed data is in 'store_info.csv'. The columns of the store data are defined in COLS.
BASE = Path(__file__).parent
#In pathlib, the / operator joins path pieces. This gives /project/backend/stores.db.
DB = BASE / 'stores.db'
SEED = BASE / 'store_info.csv'      

COLS = ['Store', 'StoreName', 'StoreType', 'Assortment', 'CompetitionDistance',
        'CompetitionOpenSinceMonth', 'CompetitionOpenSinceYear', 'Promo2',
        'Promo2SinceWeek', 'Promo2SinceYear', 'PromoInterval', 'Memo']

#This function opens a connection to the SQLite database and returns it
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c
#c.row_factory = sqlite3.Row changes how rows come back from the database.
#By default, a row is a plain tuple like (1, 'Shop A', 'a', ...). You can only get values by position: row[0], row[1].
#With sqlite3.Row, you can also get values by column name: row['StoreName']. You can even convert it with dict(row) to make the dictionary that FastAPI sends back as JSON.


#
def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS stores(
            Store INTEGER PRIMARY KEY, StoreName TEXT, StoreType TEXT, Assortment TEXT,
            CompetitionDistance REAL, CompetitionOpenSinceMonth REAL,
            CompetitionOpenSinceYear REAL, Promo2 INTEGER, Promo2SinceWeek REAL,
            Promo2SinceYear REAL, PromoInterval TEXT, Memo TEXT)""") #if the table does not exist, create it with the specified columns and types. Store is the primary key, which means it must be unique and not null.
        empty = c.execute("SELECT COUNT(*) FROM stores").fetchone()[0] == 0  #Check whether the table is empty
        if empty and SEED.exists():
            df = pd.read_csv(SEED)  #
            df['StoreName'] = df['Store'].map(lambda s: f"店舗{s}")  #creates a name for every store from its number. Store 1 becomes "店舗1"
            df['Memo'] = ''  #adds an empty memo to every row.
            df = df[COLS].astype(object)  #changes the table's data type to "anything". This is needed so the next line can really put None in number columns. Without it, pandas would turn None back into NaN.
            df = df.where(df.notna(), None) #keep the value where it is not missing, otherwise use None
            c.executemany(f"INSERT INTO stores VALUES ({','.join('?' * len(COLS))})",
                          df.values.tolist())

#StoreIn is a Pydantic model. It describes what a store's data must look like when it arrives at the backend (for example from your Streamlit PUT request)
class StoreIn(BaseModel):
    StoreName: Optional[str] = None  #StoreName: Optional[str] means the value must be text or None.
    StoreType: Optional[str] = None
    Assortment: Optional[str] = None
    CompetitionDistance: Optional[float] = None
    CompetitionOpenSinceMonth: Optional[float] = None
    CompetitionOpenSinceYear: Optional[float] = None
    Promo2: Optional[int] = None
    Promo2SinceWeek: Optional[float] = None
    Promo2SinceYear: Optional[float] = None
    PromoInterval: Optional[str] = None
    Memo: Optional[str] = None


class StoreNew(StoreIn):
    Store: int #Store: int means the value must be an integer.


app = FastAPI(title="Store Management API")  # Creates a FastAPI instance with a title
init_db() # Calls the init_db() function to create the database and seed it with initial data if necessary.


@app.get("/stores") # Defines a GET endpoint at /stores that returns a list of all stores in the database as json.
def list_stores():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM stores ORDER BY Store")]

# Defines a GET endpoint at /stores/{store_id} that returns a specific store by its ID.
@app.get("/stores/{store_id}")
def get_store(store_id: int):
    with conn() as c:
        r = c.execute("SELECT * FROM stores WHERE Store=?", (store_id,)).fetchone()
    if not r:
        raise HTTPException(404, "店舗が見つかりません")
    return dict(r)

# Defines a POST endpoint at /stores that creates a new store in the database. It takes a StoreNew object as input and returns the created store as json.
@app.post("/stores", status_code=201)
def create_store(s: StoreNew):
    data = s.model_dump()
    with conn() as c:
        if c.execute("SELECT 1 FROM stores WHERE Store=?", (s.Store,)).fetchone():
            raise HTTPException(409, "この店舗番号はすでにあります")
        c.execute(f"INSERT INTO stores VALUES ({','.join('?' * len(COLS))})",
                  [data.get(k) for k in COLS])
    return data

# Defines a PUT endpoint at /stores/{store_id} that updates an existing store in the database. It takes a StoreIn object as input and returns the updated store as json.
@app.put("/stores/{store_id}")
def update_store(store_id: int, s: StoreIn):
    data = s.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "更新する項目がありません")
    sets = ", ".join(f"{k}=?" for k in data)          # キーはStoreInの項目名だけ
    with conn() as c:
        cur = c.execute(f"UPDATE stores SET {sets} WHERE Store=?", [*data.values(), store_id])
        if cur.rowcount == 0:
            raise HTTPException(404, "店舗が見つかりません")
    return get_store(store_id)

# Defines a DELETE endpoint at /stores/{store_id} that deletes an existing store from the database. It returns a json object with the deleted store ID.
@app.delete("/stores/{store_id}")
def delete_store(store_id: int):
    with conn() as c:
        cur = c.execute("DELETE FROM stores WHERE Store=?", (store_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "店舗が見つかりません")
    return {"deleted": store_id}
