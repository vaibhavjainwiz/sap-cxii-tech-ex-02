import pandas as pd

def extract(filepath: str) -> pd.DataFrame:
    """ Load raw csv into a DataFrame. """

    return pd.read_csv(filepath)
