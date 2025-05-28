#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from gui.interface import ApplicationGUI

def main():
    root = tk.Tk()
    app = ApplicationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()