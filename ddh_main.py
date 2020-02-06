import ddh_app as run_app
import subprocess
import sys


def ensure_only_one_process():
    rv = subprocess.check_output(["pgrep", "-f", "ddh_main.py"])
    rv = rv.split()
    if len(rv) > 1:
        print('one ddh_main already present')
        sys.exit(1)


def main():
    run_app.run_app()


if __name__ == "__main__":
    ensure_only_one_process()
