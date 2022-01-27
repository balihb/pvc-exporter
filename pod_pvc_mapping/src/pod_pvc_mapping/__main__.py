import argparse  # pragma: no cover
import sys  # pragma: no cover

from .main import main  # pragma: no cover


def _main():  # pragma: no cover
    parser = argparse.ArgumentParser(description='Pod to PVC mapping.')
    args = parser.parse_args()
    print(args)
    sys.exit(main(args))


if __name__ == "__main__":  # pragma: no cover
    _main()
