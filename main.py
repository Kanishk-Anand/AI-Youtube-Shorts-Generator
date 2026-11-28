"""Entry point for running straight from a source checkout: `python main.py ...`.

The real CLI lives in shorts_generator/cli.py (also installed as the `shorts` command).
"""
import sys

from shorts_generator.cli import main

if __name__ == "__main__":
    sys.exit(main())
