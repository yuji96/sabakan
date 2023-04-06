import traceback

import paramiko


def ssh(
    secret,
    command: str,
    args="",
    names=None,
    timeout_cmd=3,
    timeout_client=10,
    replace_cmd=False,
):
    rsa_key = paramiko.RSAKey.from_private_key_file(
        secret["ssh"]["secret_key_path"], secret["ssh"]["passphrase"]
    )
    if names is None:
        names = secret["servers"].keys()

    with paramiko.SSHClient() as client:
        try:
            client.load_host_keys(secret["ssh"]["known_hosts_path"])

            res = {}
            for name in names:
                info = secret["servers"].get(name)
                if info is None:
                    # TODO: warning?
                    continue
                client.connect(
                    info["host"],
                    username=secret["user"],
                    pkey=rsa_key,
                    timeout=timeout_client,
                )

                if replace_cmd:
                    replaced = info[command]
                stdin, stdout, stderr = client.exec_command(
                    f"{replaced} {args}", timeout=timeout_cmd
                )
                res[name] = {
                    "stdout": stdout.read().decode("utf8"),
                    "stderr": stderr.read().decode("utf8"),
                }
            return res
        except Exception:
            # TODO
            print(traceback.format_exc())


if __name__ == "__main__":
    from pathlib import Path
    from pprint import pprint

    import yaml

    secret = yaml.safe_load(Path("secret.yaml").read_text())
    res = ssh(secret, "gpustat", "--json", replace_cmd=True)
    pprint(res, sort_dicts=False)
