import pandas as pd
from orders.config import EXCHANGE_RATE

def transform(df: pd.DataFrame) -> pd.DataFrame:
    """ Transform the dataframe. """

    df = _drop_invalid_rows(df)
    df = _fill_default(df)
    df = _convert_curency(df)
    df = _normalize_date(df)
    return df

def _drop_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows missing order_id or customer_id."""
    return df.dropna(subset=["order_id", "customer_id"])

def _fill_default(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing amount and currency with defaults."""
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["currency"] = df["currency"].fillna("USD")
    return df

def _convert_curency(df: pd.DataFrame) -> pd.DataFrame:
    """Convert all amounts to USD using exchange rates."""
    df["amount"] = (df["amount"] * df["currency"].map(EXCHANGE_RATE).fillna(1.0)).round(2)
    return df

def _normalize_date(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize order_date to ISO 8601 format."""
    df["order_date"] = pd.to_datetime(
        df["order_date"], format="mixed", dayfirst=False, errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    return df
