import json
from pathlib import Path
from pprint import pprint  # noqa

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from nvidia import parse_nvidia_smi

DEBUG = True

# read data
# TODO: アプリの中で起動時に読み込む
if DEBUG:
    data = json.loads(Path("sample/nvidia-smi.json").read_text())
else:
    # TODO: ssh の組み込みが未実装
    xml = Path("sample/nvidia-smi.xml").read_text()
    data = parse_nvidia_smi(xml)


# visualize
st.set_page_config(layout="wide")

col1, col2 = st.columns([1, 8])
with col1:
    st.image(Image.open("logo.png"), width=100)
with col2:
    st.title("サーバー管理モニター")

# FIXME: これを逐次的に溜めていく？
colors = {"free": "gray"}


columns = st.columns(len(data))
for (gpu_index, proc), col in zip(data.items(), columns):
    with col:
        st.header(f"GPU: {gpu_index}")

        proc = pd.DataFrame(proc)
        proc["used_memory_int"] = proc["used_memory"].str.replace(" MiB", "").astype(int)
        proc.sort_values("used_memory_int", inplace=True, ascending=False)

        # FIXME: ハードコーディング
        free = {
            "user": "free",
            "used_memory_int": 24000 - proc["used_memory_int"].sum(),
        }
        free["used_memory"] = str(free["used_memory_int"]) + " MiB"
        proc = pd.concat([proc, pd.DataFrame([free])], axis="rows", ignore_index=True)

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=proc["user"],
                    values=proc["used_memory_int"],
                    sort=False,
                    direction="clockwise",
                    marker=dict(colors=[colors.get(label) for label in proc["user"]]),
                )
            ],
            layout=dict(legend=dict(orientation="h", xanchor="center", x=0.5)),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            proc.iloc[:][
                ["user", "used_memory", "cpu_usage", "cum_time", "pid", "process_name"]
            ].style.background_gradient(
                gmap=proc["used_memory_int"], axis="rows", vmin=0, vmax=24000, low=0.5
            )
        )
