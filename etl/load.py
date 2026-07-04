import sqlite3
import pandas as pd
from etl.config import DB_PATH, TABLE_NAME

def load(df: pd.DataFrame, db_path: str = DB_PATH):
    """ Load data into database. """
    
    conn = sqlite3.connect(db_path)
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
    conn.close()
