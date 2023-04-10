import subprocess
from pathlib import Path


def main():
    app = Path(__file__).with_name("app.py")
    subprocess.run(f"streamlit run {app}", shell=True)


if __name__ == "__main__":
    main()
