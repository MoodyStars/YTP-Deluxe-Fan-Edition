#!/usr/bin/env python3
"""
Entry point with GUI or batch CLI.

This is a small wrapper; batch CLI already supported (see earlier main.py).
No change to CLI semantics here; leaving as-is. Run "python main.py --help" for options.
"""
import sys
from gui import YTPPlusGUI

def main():
    app = YTPPlusGUI()
    app.run()

if __name__ == "__main__":
    main()