#!/usr/bin/env python3
"""
Entrypoint for YTP+ Deluxe Edition prototype.
"""
import sys
from gui import YTPPlusGUI

def main():
    app = YTPPlusGUI()
    app.run()

if __name__ == "__main__":
    main()