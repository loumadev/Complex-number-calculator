from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget
from typing import List, Optional
import Sidebar
from Canvas import Canvas
from CSSPreprocessor import CSS


class Calculator(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None, args: List[str] = []) -> None:
        super().__init__(parent)

        self.css: CSS = CSS.process("./style.qss")
        self.sidebarWidth: int = self.css.var("sidebar_width", int)
        self.itemHeight: int = self.css.var("sidebar_itemHeight", int)
        self.verbose: bool = "-v" in args or "--verbose" in args

        self.setWindowTitle(self.css.var("window_title"))
        self.setWindowIcon(QIcon("./resources/icon512.png"))
        self.setGeometry(0, 0, self.css.var("window_width", int), self.css.var("window_height", int))
        self.setFixedSize(self.size())
        self.setFocusPolicy(Qt.StrongFocus)
        self.move(self.screen().geometry().center() - self.frameGeometry().center())

        self.layout: QHBoxLayout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self._centralWidget: QWidget = QWidget(self)

        self.setCentralWidget(self._centralWidget)
        self._centralWidget.setLayout(self.layout)

        self._setupUI()
        self.show()

    def _setupUI(self) -> None:
        # Setup sidebar
        self.sidebar: Sidebar.Sidebar = Sidebar.Sidebar(self)

        # Setup error bar
        self._errorBarHeight: int = self.css.var("sidebar_errorBarHeight", int)
        self._errorLabel: QLabel = QLabel(self)
        self._errorLabel.setObjectName("errorLabel")
        self._errorLabel.setFixedHeight(self._errorBarHeight)

        # Setup sidebar column (scrollarea + error bar)
        self._sidebarColumn: QWidget = QWidget(self)
        self._sidebarColumnLayout: QVBoxLayout = QVBoxLayout(self._sidebarColumn)
        self._sidebarColumnLayout.setContentsMargins(0, 0, 0, 0)
        self._sidebarColumnLayout.setSpacing(0)
        self._sidebarColumnLayout.addWidget(self.sidebar.scrollArea)
        self._sidebarColumnLayout.addWidget(self._errorLabel)

        # Setup canvas
        self.canvas: Canvas = Canvas(self)

        self.layout.addWidget(self._sidebarColumn)
        self.layout.addWidget(self.canvas.label)

        self._sidebarColumn.setStyleSheet(self.css.content)

    def setErrorMessage(self, message: str) -> None:
        self._errorLabel.setText(message)
