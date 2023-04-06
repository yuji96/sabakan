import pandas as pd

from ssh import ssh


def proc_info(pids: list, secret):
    # https://linuxjm.osdn.jp/html/procps/man1/ps.1.html
    command = f"ps -ww -p {','.join(map(str, pids))} -o pid,cp,time,etime,cmd"

    stdout, stderr = ssh(command, secret)
    # TODO: srderr について異常系

    header, *data = [row.split(maxsplit=4) for row in stdout.splitlines()]
    info = pd.DataFrame(
        data,
        columns=[
            "pid",
            "cpu_usage",
            "use_time",
            "elapse_time",
            "full_command",
        ],
    ).astype({"pid": int, "cpu_usage": float})
    info["cpu_usage"] /= 10
    info["elapse_time"] = info["elapse_time"].str.replace("-", " days ")
    return info


if __name__ == "__main__":
    import json
    from pathlib import Path

    import yaml

    secret = yaml.safe_load(Path("secret.yaml").read_text())
    gpustat = json.loads(Path("sample/gpustat.json").read_text())

    data = []
    for gpu in gpustat["gpus"]:
        index = gpu["index"]
        for proc in gpu["processes"]:
            proc["gpu"] = index
            data.append(proc)
    proc_df = pd.DataFrame(data)

    new_info = proc_info(proc_df["pid"], secret)
    proc_df = pd.merge(proc_df, new_info, on="pid")
    print(proc_df)
