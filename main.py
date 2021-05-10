from Calculator import Calculator
import sys

from PyQt5.QtWidgets import QApplication


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Calculator(args=sys.argv)
    sys.exit(app.exec_())
