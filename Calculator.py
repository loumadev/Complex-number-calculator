from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QWidget
import Sidebar
from Canvas import Canvas
from CSSPreprocessor import CSS


class Calculator(QMainWindow):
    def __init__(self, parent=None, args=[]):
        super().__init__(parent)

        self.css = CSS.process("./style.qss")
        self.sidebarWidth = self.css.var("sidebar_width", int)
        self.itemHeight = self.css.var("sidebar_itemHeight", int)
        self.verbose = "-v" in args or "--verbose" in args

        self.setWindowTitle(self.css.var("window_title"))
        self.setWindowIcon(QIcon("./resources/icon512.png"))
        self.setGeometry(0, 0, self.css.var("window_width", int), self.css.var("window_height", int))
        self.setFixedSize(self.size())
        self.setFocusPolicy(Qt.StrongFocus)
        self.move(self.screen().geometry().center() - self.frameGeometry().center())

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self._centralWidget = QWidget(self)

        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.layout)

        self._setupUI()
        self.show()

    def _setupUI(self):
        # Setup sidebar
        self.sidebar = Sidebar.Sidebar(self)

        # Setup canvas
        self.canvas = Canvas(self)

        self.layout.addWidget(self.sidebar.scrollArea)
        self.layout.addWidget(self.canvas.label)

        self.sidebar.setStyleSheet(self.css.content)
