import json
from pathlib import Path
from pprint import pprint  # noqa

import streamlit as st
import yaml
from PIL import Image

from plot import plot
from ssh import ssh

if __name__ == "__main__":
    DEBUG = False

    st.set_page_config(
        page_title="サーバー管理モニター",
        page_icon=Image.open("logo.png"),
        layout="wide",
    )

    # read data
    # TODO: アプリの中で起動時に読み込む
    if DEBUG:
        data = json.loads(Path("sample/multi_gpustat.json").read_text())
    else:
        secret = yaml.safe_load(Path("secret.yaml").read_text())
        with st.spinner(
            "Retrieving server status...\n(Stop if there is no response for 10 seconds.)"
        ):
            data = ssh(secret, "gpustat", "--json", replace_cmd=True)

    # visualize
    # TODO: .host のレスポンシブ化
    css = Path("style.css").read_text()
    st.write(f"<style>{css}</style>", unsafe_allow_html=True)

    graph, table = st.tabs(["Graph", "Table"])
    with graph:
        _, *columns = st.columns([1, 4, 4, 4])
        for i, col in enumerate(columns):
            with col:
                st.write(f"<h2 class='cuda'>cuda:{i}</h2>", unsafe_allow_html=True)

        for i, (hostname, response) in enumerate(data.items()):
            # FIXME: 事前に辞書化

            if response["status"] == "error":
                label, message = st.columns([1, 12])
            else:
                label, *columns = st.columns([1, 4, 4, 4])
            with label:
                st.write(f"<h2 class='host'>{hostname}</h2>", unsafe_allow_html=True)

            if response["status"] == "error":
                with message:
                    st.error("No response.", icon="🚨")
                continue

            # TODO: リストの順序と gpu index が同じなのか確認が必要
            gpustat = json.loads(response["stdout"])
            for gpu, col in zip(gpustat["gpus"], columns):
                with col:
                    fig = plot(gpu)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={
                            "displayModeBar": False,
                        },
                    )

    with table:
        st.header("A cat")
        st.image("https://static.streamlit.io/examples/cat.jpg", width=200)
        # st.dataframe(
        #     proc.iloc[:][
        #         ["user", "used_memory", "cpu_usage", "cum_time", "pid", "process_name"]
        #     ].style.background_gradient(
        #         gmap=proc["used_memory_int"], axis="rows", vmin=0, vmax=24000, low=0.5
        #     )
        # )
