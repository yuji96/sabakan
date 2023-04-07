import json
from pathlib import Path
from pprint import pprint  # noqa

import streamlit as st
from PIL import Image

from plot import plot

DEBUG = True

# read data
# TODO: アプリの中で起動時に読み込む
data = json.loads(Path("sample/multi_gpustat.json").read_text())


# visualize
st.set_page_config(layout="wide")
st.write(
    """<style>
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


col1, col2 = st.columns([1, 8])
with col1:
    st.image(Image.open("logo.png"), width=100)
with col2:
    st.title("サーバー管理モニター")

# FIXME: これを逐次的に溜めていく？
colors = {"free": "gray"}


for i, (hostname, response) in enumerate(data.items()):
    # FIXME: 事前に辞書化
    gpustat = json.loads(response["stdout"])
    gpus = gpustat["gpus"]

    label, *columns = st.columns([1, 3, 3, 3])
    with label:
        st.write(
            f"""<h2 style='vertical-align:middle; font-size:24px;'>
                    {hostname}
                </h2>""",
            unsafe_allow_html=True,
        )
    for gpu, col in zip(gpus, columns):
        with col:
            if i == 0:
                st.write(
                    f"""<h2 style='text-align:center; font-size:24px;'>
                            cuda:{gpu['index']}
                        </h2>""",
                    unsafe_allow_html=True,
                )
            fig = plot(gpu)
            st.plotly_chart(fig, use_container_width=True)

    # st.dataframe(
    #     proc.iloc[:][
    #         ["user", "used_memory", "cpu_usage", "cum_time", "pid", "process_name"]
    #     ].style.background_gradient(
    #         gmap=proc["used_memory_int"], axis="rows", vmin=0, vmax=24000, low=0.5
    #     )
    # )
