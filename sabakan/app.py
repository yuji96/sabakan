import argparse
import json
import pickle
import socket
from pathlib import Path

import pandas as pd
import pyperclip
import streamlit as st
import yaml
from paramiko import SSHException
from PIL import Image
from plot import plot

from sabakan.ssh import fetch_sever_status, get_passphrase
from sabakan.views.storage import get_top


def color_per_host(df: pd.DataFrame):
    color_row = df["host"].isin(df["host"].unique()[1::2])
    df = df.copy()
    df[:] = "background-color: #2d2d2d;"
    return df.loc[color_row]


def convert_unit(series: pd.Series):
    unit = pd.Categorical(series.str[-1], list("KMGT"))
    digits = series.str.rstrip("KMGT").astype(float)

    digits[unit == "T"] *= 1024**1
    # digits[unit == "G"] *= 1024 ** 0
    digits[unit == "M"] *= 1024**-1
    digits[unit == "K"] *= 1024**-2
    return digits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="description")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).parent

    st.set_page_config(
        page_title="サーバー管理モニター",
        page_icon=Image.open(root.joinpath("./assets/logo.png")),
        layout="wide",
    )
    css = root.joinpath("assets/style.css").read_text()
    st.write(f"<style>{css}</style>", unsafe_allow_html=True)
    config = yaml.safe_load(Path.home().joinpath(".sabakan/config.yaml").read_text())

    # read data
    if args.debug:
        st.warning("🚧 Debug Mode")
        server_status = json.loads(
            root.joinpath("../sample/server_status.json").read_text()
        )
    else:
        config["ssh"]["passphrase"] = get_passphrase()

        # FIXME: 鍵の異常系どこでやろう
        # paramiko.ssh_exception.SSHException

        try:
            server_status = fetch_sever_status(config)
            # uncomment to create sample data
            # Path("sample/server_status.json").write_text(
            #     json.dumps(server_status, indent=2)
            # )
            print("ブラウザにサーバ情報を表示/更新しました。")
        except SSHException as e:
            if e.args == "OpenSSH private key file checkints do not match":
                print("パスフレーズが異なる可能性があります。再入力してください。")
                st.cache_data.clear()
                st.experimental_rerun()
            else:
                raise
        except socket.timeout:
            print("SSH 接続に失敗しました。ネットワークや設定を確認後、ブラウザのページをリロードして再実行してください。")
            st.error("SSH 接続に失敗しました。ネットワークや設定を確認後、このページをリロードして再実行してください。")
            st.cache_data.clear()
            st.stop()
        except pickle.PicklingError:
            print(
                "並列処理が衝突しました。ターミナルで Ctrl+C を実行してアプリを中断し、再起動してください。"
                "（ブラウザでこのアプリが複数タブで開かれていた可能性があります。）"
            )
            st.error(
                "並列処理が衝突しました。"
                "ブラウザにこのアプリのタブが 1 つしか無いことを確認して、そのタブをリロードしてください。"
                "もし、タブが複数あれば 1 つに減らしてください。"
            )
            st.cache_data.clear()
            st.stop()
        except Exception:
            st.cache_data.clear()
            raise

    # visualize
    gpustat_dfs = []
    ps_dfs = []
    overview_tab, gpu_tab, process_tab, storage_tab = st.tabs(
        ["GPU Memory", "GPU Status", "Process", "Storage"]
    )
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
                proc_df["host"] = hostname

                gpustat_dfs.append(proc_df)

            ps_df = pd.DataFrame(response["ps"])
            ps_df["host"] = hostname
            ps_dfs.append(ps_df)

    gpustat_dfs = pd.concat(gpustat_dfs, axis="rows")
    ps_dfs = pd.concat(ps_dfs, axis="rows")

    with gpu_tab:
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
            .rename(
                columns={
                    "index": "GPU",
                    "utilization.gpu": "GPU%",
                    "temperature.gpu": "temp.",
                    "enforced.power.limit": "power.limit",
                }
            )
        )

        copy_button = st.container()
        st.dataframe(
            gpu_df.style.apply(color_per_host, axis=None).format(
                {
                    "memory.total": "{} MiB",
                    "memory.used": "{} MiB",
                    "GPU%": "{}%",
                    "temp.": "{} ℃",
                    "power.limit": "{} W",
                    "power.draw": "{} W",
                }
            ),
            use_container_width=True,
            height=(len(gpu_df) + 1) * 35 + 3,
        )
        if copy_button.button("Copy Table to Clipboard", key="gpu"):
            gpu_df.to_clipboard()

    with process_tab:
        status_df = pd.merge(gpustat_dfs, ps_dfs, on=["host", "pid"], how="outer")

        status_df = status_df.reindex(
            columns=[
                "host",
                "gpu_index",
                "pid",
                "username",
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
                "gpu_index": "GPU",
                "gpu_memory_usage": "gpu.memory",
                "cpu_usage": "CPU%",
            },
            inplace=True,
        )
        # https://github.com/streamlit/streamlit/issues/4489
        # status_df["use_time"] = pd.to_timedelta(status_df["use_time"])
        # status_df["elapse_time"] = pd.to_timedelta(status_df["elapse_time"])

        copy_button = st.container()
        st.dataframe(
            status_df.style.apply(color_per_host, axis=None).format(
                {
                    "CPU%": "{:.1f}%",
                    "gpu.memory": "{} GiB",
                }
            ),
            use_container_width=True,
            height=(len(status_df) + 1) * 35 + 3,
        )
        if copy_button.button("Copy Table to Clipboard", key="proc"):
            status_df[["host", "GPU", "pid", "username", "CPU%", "経過"]].to_clipboard()

    with storage_tab:
        user_dfs = []
        sum_df = []
        for host, response in server_status.items():
            du = response["du"]
            user_df = (
                pd.DataFrame(du.pop("user"))
                .set_index("user")
                .rename(columns={"usage": host})
            )
            user_dfs.append(user_df)

            du["host"] = host
            sum_df.append(du)

        user_df = pd.concat(user_dfs, axis="columns")
        sum_df = (
            pd.DataFrame(sum_df)
            .reindex(columns=["host", "full", "used", "avail", "used_rate", "run_at"])
            .set_index("host")
        )

        sum_copy, uesr_radio, user_copy = st.columns([4, 3, 2])

        col1, col2 = st.columns([4, 5])
        with col1:
            st.dataframe(
                sum_df, height=(len(sum_df) + 1) * 35 + 3, use_container_width=True
            )
            if sum_copy.button("Copy Table to Clipboard", key="sum"):
                sum_df.to_clipboard()
        with col2:
            user_df = (
                user_df.apply(convert_unit, axis="rows").drop(index="/home").fillna(0)
            )

            unit = uesr_radio.radio("単位:", ["GiB", "%"], horizontal=True)
            n = 5
            if user_copy.button(f"Copy Top {n} to Clipboard", key="storage"):
                pyperclip.copy(get_top(user_df, n))
            if unit == "GiB":
                st.dataframe(
                    user_df.style.background_gradient(axis="rows").format("{:.1f} GiB"),
                    height=(len(user_df) + 1) * 35 + 3,
                    use_container_width=True,
                )
            else:
                user_df /= convert_unit(sum_df["full"])
                st.dataframe(
                    user_df.style.background_gradient(axis="rows").format("{:.1%}"),
                    height=(len(user_df) + 1) * 35 + 3,
                    use_container_width=True,
                )
