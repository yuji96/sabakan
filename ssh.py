import traceback
from pathlib import Path

import paramiko
import yaml

secret = yaml.safe_load(Path("secret.yaml").read_text())

rsa_key = paramiko.RSAKey.from_private_key_file(
    secret["ssh"]["secret_key_path"], secret["ssh"]["passphrase"]
)
with paramiko.SSHClient() as ssh:
    try:
        ssh.load_host_keys(secret["ssh"]["known_hosts_path"])
        ssh.connect(
            secret["servers"]["name"]["host"],
            username=secret["user"],
            pkey=rsa_key,
            timeout=1,
        )
        stdin, stdout, stderr = ssh.exec_command(
            f"{secret['gpustat_path']} --json", timeout=1
        )
        stdin.close()

        print(stdout.read().decode("utf8"))
        print(stderr.read().decode("utf8"))

    except Exception:
        print(traceback.format_exc())
