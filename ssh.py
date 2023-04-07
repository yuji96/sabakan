import traceback
from multiprocessing import Pool

import paramiko


def worker(args):
    secret, command, cmd_args, name, timeout_client, timeout_cmd, replace_cmd = args
    with paramiko.SSHClient() as client:
        client.load_host_keys(secret["ssh"]["known_hosts_path"])
        private_key = paramiko.RSAKey.from_private_key_file(
            secret["ssh"]["secret_key_path"], secret["ssh"]["passphrase"]
        )

        try:
            client.connect(
                secret["servers"][name]["host"],
                username=secret["user"],
                pkey=private_key,
                timeout=timeout_client,
            )
            if replace_cmd:
                replaced = secret["servers"][name][command]
            stdin, stdout, stderr = client.exec_command(
                f"{replaced} {cmd_args}", timeout=timeout_cmd
            )
            return {
                "stdout": stdout.read().decode("utf8"),
                "stderr": stderr.read().decode("utf8"),
            }
        except Exception:
            # TODO
            print(traceback.format_exc())


def ssh(
    secret,
    command: str,
    args="",
    names=None,
    timeout_cmd=3,
    timeout_client=10,
    replace_cmd=False,
):
    if names is None:
        names = secret["servers"].keys()
    else:
        # TODO: 要素数変わったら警告
        names = [name for name in names if name in secret["servers"]]

    # TODO: ssh を並列実行するライブラリに移行
    with Pool(processes=len(names)) as pool:
        results = pool.map(
            worker,
            [
                (secret, command, args, name, timeout_client, timeout_cmd, replace_cmd)
                for name in names
            ],
        )
    return dict(zip(names, results))


if __name__ == "__main__":
    from pathlib import Path
    from pprint import pprint

    import yaml

    secret = yaml.safe_load(Path("secret.yaml").read_text())
    res = ssh(secret, "gpustat", "--json", replace_cmd=True)
    pprint(res, sort_dicts=False)
