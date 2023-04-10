import json
import socket
from getpass import getpass
from multiprocessing import Pool

import pandas as pd
import paramiko
import streamlit as st


@st.cache_data
def get_passphrase():
    tmp1 = st.warning("ターミナルに戻ってパスフレーズを入力してください。", icon="🔑")
    tmp2 = st.warning("複数のタブで開くとバグるので、ターミナルから再起動する際はこのタブを消してください。")
    passphrase = getpass("passphrase: ")
    tmp1.empty()
    tmp2.empty()
    return passphrase


def run_gpustat(client, config, name, timeout_cmd):
    cmd = config["servers"][name]["gpustat"] + " --json"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout_cmd)
    stdout = json.loads(stdout.read().decode("utf8"))

    pids = [p["pid"] for gpu in stdout["gpus"] for p in gpu["processes"]]

    return stdout, pids


def run_ps(client, pids, timeout_cmd, return_as_dict=False):
    if len(pids) == 0:
        return {"pid": []} if return_as_dict else pd.DataFrame([], columns=["pid"])

    # ps usage: https://linuxjm.osdn.jp/html/procps/man1/ps.1.html
    cmd = f"ps -ww -p {','.join(map(str, pids))} -o pid,cp,time,etime,cmd"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout_cmd)
    stdout = stdout.read().decode("utf8")

    header, *data = [row.split(maxsplit=4) for row in stdout.splitlines()]
    df = pd.DataFrame(
        data,
        columns=["pid", "cpu_usage", "use_time", "elapse_time", "full_command"],
    ).astype({"pid": int, "cpu_usage": float})
    df["cpu_usage"] /= 10  # permille → percent
    df["elapse_time"] = df["elapse_time"].str.replace("-", " days ")
    df["use_time"] = df["use_time"].str.replace("-", " days ")

    return df.to_dict("records") if return_as_dict else df


def worker(args):
    config, name, timeout_client, timeout_cmd, return_as_dict = args
    with paramiko.SSHClient() as client:
        client.load_host_keys(config["ssh"]["known_hosts_path"])
        private_key = paramiko.RSAKey.from_private_key_file(
            config["ssh"]["secret_key_path"], config["ssh"]["passphrase"]
        )

        try:
            client.connect(
                config["servers"][name]["host"],
                username=config["ssh"]["user"],
                pkey=private_key,
                timeout=timeout_client,
            )
            gpustat, pids = run_gpustat(client, config, name, timeout_cmd)
            ps = run_ps(client, pids, timeout_cmd, return_as_dict)

            return {"status": "ok", "gpustat": gpustat, "ps": ps}
        except socket.timeout:
            return {"status": "error", "message": "timeout. check SSH and VPN settings."}


@st.cache_data
def fetch_sever_status(
    config, names=None, timeout_cmd=3, timeout_client=10, return_as_dict=False
):
    if names is None:
        names = config["servers"].keys()
    else:
        # TODO: 要素数変わったら警告
        names = [name for name in names if name in config["servers"]]

    # TODO: ssh を並列実行するライブラリに移行
    with Pool(processes=len(names)) as pool:
        results = pool.map(
            worker,
            [
                (config, name, timeout_client, timeout_cmd, return_as_dict)
                for name in names
            ],
        )
        pool.close()
        pool.join()
    return dict(zip(names, results))


if __name__ == "__main__":
    from pathlib import Path
    from pprint import pprint

    import yaml

    config = yaml.safe_load(Path("config.yaml").read_text())
    res = fetch_sever_status(config, return_as_dict=True)
    Path("sample/gpustat_ps.json").write_text(json.dumps(res, indent=2))
