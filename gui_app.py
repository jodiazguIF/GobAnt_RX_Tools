"""Punto de entrada para la interfaz gráfica de generación de licencias."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.gui.main_window import LicenseGeneratorWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = LicenseGeneratorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
