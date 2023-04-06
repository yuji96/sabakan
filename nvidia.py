import json
from pathlib import Path
from pprint import pprint

import xmltodict
from paramiko import SSHClient


def proc_info(pid, ssh: SSHClient):
    # https://linuxjm.osdn.jp/html/procps/man1/ps.1.html
    command = f"ps -ww -p {pid} -o user:20,cp,time,etime,cmd"
    # TODO: srderr について異常系
    stdin, stdout, stderr = ssh.exec_command(command, timeout=1)
    stdin.close()

    header, info = stdout.read().decode("utf8").splitlines()
    return dict(
        zip(["user", "cpu_usage", "cpu_time", "cum_time", "cmd"], info.split(maxsplit=4))
    )


def parse_nvidia_smi(xml, ssh):
    d = xmltodict.parse(xml)
    gpu_info = {}
    for gpu in d["nvidia_smi_log"]["gpu"]:
        gpu_index = int(gpu["minor_number"])
        gpu_info[gpu_index] = {
            # 気になる key
            # fan_speed, fb_memory_usage, utilization, temperature, power_readings
            "info": {"total_memory": gpu["fb_memory_usage"]["total"]},
            "processes": [],
        }

        # FIXME: 空き GPU だと processes の返り値が None らしい
        processes = gpu["processes"]["process_info"]
        if not isinstance(processes, list):
            processes: list[dict] = [processes]
        for proc in processes:
            # TODO: プロセスごとの GPU 使用率も取得したい。
            proc.update(proc_info(proc["pid"], ssh))
            gpu_info[gpu_index]["processes"].append(proc)
    return gpu_info


if __name__ == "__main__":
    xml = Path("sample/nvidia-smi.xml").read_text()
    res = parse_nvidia_smi(xml)
    # pprint(res)
    Path("sample/nvidia-smi.json").write_text(json.dumps(res, indent=2))
