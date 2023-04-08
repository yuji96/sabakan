import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from PIL import Image
from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder

from plot import plot
from ssh import fetch_sever_status

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
        server_status = json.loads(Path("sample/gpustat_ps.json").read_text())
    else:
        secret = yaml.safe_load(Path("secret.yaml").read_text())
        with st.spinner(
            "Retrieving server status...\n(Stop if there is no response for 10 seconds.)"
        ):
            server_status = fetch_sever_status(secret)

    # visualize
    # TODO: .host のレスポンシブ化
    css = Path("style.css").read_text()
    st.write(f"<style>{css}</style>", unsafe_allow_html=True)

    gpustat_dfs = []
    ps_dfs = []
    graph, table = st.tabs(["Graph", "Table"])
    with graph:
        _, *columns = st.columns([1, 4, 4, 4])
        for i, col in enumerate(columns):
            with col:
                st.write(f"<h2 class='cuda'>cuda:{i}</h2>", unsafe_allow_html=True)

        for i, (hostname, response) in enumerate(server_status.items()):
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

            gpustat = response["gpustat"]
            for gpu in gpustat["gpus"]:
                with columns[gpu["index"]]:
                    fig, proc_df = plot(gpu)
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        config={
                            "displayModeBar": False,
                        },
                    )
                proc_df["gpu_index"] = gpu["index"]
                proc_df["hostname"] = hostname
                gpustat_dfs.append(proc_df)

            ps_df = pd.DataFrame(response["ps"])
            ps_df["hostname"] = hostname
            ps_dfs.append(ps_df)

    gpustat_dfs = pd.concat(gpustat_dfs, axis="rows")
    ps_dfs = pd.concat(ps_dfs, axis="rows")
    status_df = pd.merge(gpustat_dfs, ps_dfs, on=["hostname", "pid"], how="outer")
    status_df = status_df.reindex(
        columns=[
            "pid",
            "username",
            "hostname",
            "gpu_index",
            "gpu_memory_usage",
            "cpu_usage",
            "use_time",
            "elapse_time",
            "command",
            "full_command",
        ]
    )
    status_df.rename(
        columns={
            "gpu_index": "GPU idx",
            "gpu_memory_usage": "Memory (MiB)",
            "cpu_usage": "CPU usage (%)",
        },
        inplace=True,
    )

    with table:
        st.info(
            "ヘッダーをホバーしたときに出てくる ≡ から `Autosize All Columns` を実行すると見やすくなります。",
            icon="👀",
        )

        options = GridOptionsBuilder.from_dataframe(status_df)
        options.configure_default_column(min_column_width=100)
        options.configure_columns(
            ["use_time", "elapse_time"], cellStyle={"text-align": "right"}
        )
        AgGrid(
            status_df,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            gridOptions=options.build(),
            custom_css={"#gridToolBar": {"display": "none"}},
        )
