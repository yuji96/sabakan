import json
import os
from getpass import getpass
from multiprocessing import Pool

import pandas as pd
import paramiko
import streamlit as st


@st.cache_data(show_spinner="🔑 ターミナルに戻ってパスフレーズを入力してください。")
def get_passphrase():
    return getpass("passphrase: ")


def run_gpustat(client, host_config, timeout_cmd):
    cmd = host_config["gpustat"] + " --json"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout_cmd)
    stdout = stdout.read().decode("utf8")
    stderr = stderr.read().decode("utf8")
    print(stdout, stderr, sep="\n")

    stdout = json.loads(stdout)
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


def get_du(client: paramiko.SSHClient, host_config, timeout_cmd, return_as_dict=False):
    cmd = f"cat {host_config['du_path']}"
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout_cmd)
    run_at, full_disk, *disk_usages = stdout = stdout.read().decode("utf8").splitlines()
    fs, full, used, avail, used_rate, moun = full_disk.split()
    df = pd.DataFrame(
        [line.split() for line in disk_usages],
        columns=["usage", "user"],
        dtype="object",
    )
    return {
        "run_at": run_at,
        "full": full,
        "used": used,
        "avail": avail,
        "used_rate": used_rate,
        "user": df.to_dict(orient="records") if return_as_dict else df,
    }


def worker(args):
    config, host, timeout_client, timeout_cmd, return_as_dict = args
    with paramiko.SSHClient() as client:
        client.load_host_keys(os.path.expanduser(config["ssh"]["known_hosts_path"]))
        client.set_missing_host_key_policy(paramiko.WarningPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(
            os.path.expanduser(config["ssh"]["secret_key_path"]),
            (config["ssh"]["passphrase"] or None),
        )

        print("connecting", host)
        host_config = config["servers"][host]
        client.connect(
            host_config["host"],
            username=config["ssh"]["user"],
            pkey=private_key,
            timeout=timeout_client,
        )
        gpustat, pids = run_gpustat(client, host_config, timeout_cmd)
        ps = run_ps(client, pids, timeout_cmd, return_as_dict)
        disk_usage = get_du(client, host_config, timeout_cmd, return_as_dict)

        return {"status": "ok", "gpustat": gpustat, "ps": ps, "du": disk_usage}


@st.cache_data(show_spinner="📡 サーバ情報を取得しています。（最大 10 秒間）")
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
