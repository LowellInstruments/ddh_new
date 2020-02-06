import ddh_app as run_app
import subprocess
import sys


def ensure_only_one_process():
    try:
        rv = subprocess.check_output(["pgrep", "-f", "ddh_main.py"])
        rv = rv.split()
        if len(rv) > 1:
            print('python --> some ddh_main.py already running')
        sys.exit(1)
    except subprocess.CalledProcessError:
        # pgrep failed, so no process ddh_main.py detected
        main()


def main():
    run_app.run_app()


if __name__ == "__main__":
    ensure_only_one_process()
