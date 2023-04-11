import subprocess
import sys
from pathlib import Path


def main():
    app = Path(__file__).with_name("app.py")
    cmd = f"streamlit run {app} -- {' '.join(sys.argv[1:])}"
    print(cmd)
    subprocess.run(cmd, shell=True)


if __name__ == "__main__":
    main()
