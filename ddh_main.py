import ddh_app as run_app


def ensure_only_one_process():
    from os import remove
    from os.path import splitext
    import fcntl
    lock_filename = '{}.lock'.format(splitext(__file__)[0])
    with open(lock_filename, 'w') as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            return
        else:
            main()
    remove(lock_filename)


def main():
    run_app.run_app()


if __name__ == "__main__":
    ensure_only_one_process()
