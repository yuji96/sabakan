import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from PIL import Image
from plot import plot
from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder

from sabakan.ssh import fetch_sever_status, get_passphrase

if __name__ == "__main__":
    DEBUG = False
    root = Path(__file__).parent

    st.set_page_config(
        page_title="サーバー管理モニター",
        page_icon=Image.open(root.joinpath("./assets/logo.png")),
        layout="wide",
    )

    # read data
    if DEBUG:
        server_status = json.loads(
            root.joinpath("../sample/gpustat_ps.json").read_text()
        )
    else:
        secret = yaml.safe_load(Path.home().joinpath(".sabakan/secret.yaml").read_text())
        secret["ssh"]["passphrase"] = get_passphrase()

        # FIXME: 鍵の異常系どこでやろう
        # paramiko.ssh_exception.SSHException

        try:
            server_status = fetch_sever_status(secret)
            print("ブラウザにサーバ情報を表示/更新しました。")
        except Exception:
            st.cache_data.clear()
            raise

    # visualize
    # TODO: .host のレスポンシブ化
    css = root.joinpath("assets/style.css").read_text()
    st.write(f"<style>{css}</style>", unsafe_allow_html=True)

    gpustat_dfs = []
    ps_dfs = []
    overview_tab, gpu_tab, process_tab = st.tabs(["Overview", "GPU", "Process"])
    with overview_tab:
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
                    if gpu["utilization.gpu"] > 0:
                        icon = "⚡️"
                        extra_class = ""
                    else:
                        icon = ""
                        extra_class = "darkgray"
                    st.write(
                        f"""
                        <p class="gpu-usage-wrapper {extra_class}">
                            <span>GPU 使用率: </span>
                            <span class="gpu-usage">
                                {gpu["utilization.gpu"]} % {icon}
                            </span>
                        </p>""",
                        unsafe_allow_html=True,
                    )
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

    with process_tab:
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
            custom_css={
                "#gridToolBar": {"display": "none"},
                ".ag-set-filter-list": {"height": "fit-content"},
            },
        )

    with gpu_tab:
        st.info(
            "ヘッダーをホバーしたときに出てくる ≡ から `Autosize All Columns` を実行すると見やすくなります。",
            icon="👀",
        )

        gpu_df = []
        for i, (hostname, response) in enumerate(server_status.items()):
            gpustat = response["gpustat"]
            for gpu in gpustat["gpus"]:
                gpu["host"] = hostname
                gpu["process_count"] = len(gpu["processes"])
                gpu_df.append(gpu)
        gpu_df = (
            pd.DataFrame(gpu_df)
            .reindex(
                columns=[
                    "host",
                    "index",
                    "memory.total",
                    "memory.used",
                    "utilization.gpu",
                    "process_count",
                    "temperature.gpu",
                    "fan.speed",
                    "enforced.power.limit",
                    "power.draw",
                ]
            )
            .rename({"index": "GPU idx"})
        )
        AgGrid(
            gpu_df,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
            # gridOptions=options.build(),
            custom_css={
                "#gridToolBar": {"display": "none"},
                ".ag-set-filter-list": {"height": "fit-content"},
            },
        )
