import traceback

import paramiko


def ssh(command, secret):
    rsa_key = paramiko.RSAKey.from_private_key_file(
        secret["ssh"]["secret_key_path"], secret["ssh"]["passphrase"]
    )
    with paramiko.SSHClient() as client:
        try:
            client.load_host_keys(secret["ssh"]["known_hosts_path"])
            client.connect(
                secret["servers"]["name"]["host"],
                username=secret["user"],
                pkey=rsa_key,
                timeout=1,
            )
            stdin, stdout, stderr = client.exec_command(command, timeout=1)
            return stdout.read().decode("utf8"), stderr.read().decode("utf8")
        except Exception:
            print(traceback.format_exc())


if __name__ == "__main__":
    import shutil
    from pathlib import Path

    import yaml

    secret = yaml.safe_load(Path("secret.yaml").read_text())
    command = f"{secret['gpustat_path']} --json"
    stdout, stderr = ssh(command, secret)
    print(stdout)
    print("=" * shutil.get_terminal_size().columns)
    print(stderr)
