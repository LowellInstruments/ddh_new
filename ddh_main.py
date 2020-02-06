import ddh_app as run_app
import subprocess
import sys


def main():
    run_app.run_app()


def ensure_only_one_process():
    rv = subprocess.run(['pgrep', '-f', 'ddh_main.py'])
    if rv.returncode == 0:
        print('python --> some ddh_main.py already running')
        sys.exit(1)
    main()


if __name__ == "__main__":
    ensure_only_one_process()
