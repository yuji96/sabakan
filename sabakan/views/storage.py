import pandas as pd


def get_top(df: pd.DataFrame, n):
    text = ""
    for host in df.columns:
        text += host + "\n"

        top = df[host].nlargest(n).astype(str) + " GiB"
        text += top.rename_axis(None, axis="index").to_string() + "\n\n"
    return text
