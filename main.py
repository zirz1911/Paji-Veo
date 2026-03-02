"""Paji-Veo — KIE.AI VEO3 video generation desktop app."""
import sys
from pathlib import Path

# Make sure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import MainApp


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
