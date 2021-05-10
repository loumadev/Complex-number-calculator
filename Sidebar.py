import random
import re
from Color import Color
from ComplexNumber import ComplexNumber
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QFont, QImage, QPainter, QPixmap, QRegion
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout, QLineEdit, QScrollArea, QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.items = []
        self.color = random.randint(0, 255)
        self.colorStep = self.parent.css.var("sidebar_colorStep", int)
        self.colorOffset = self.parent.css.var("sidebar_colorOffset", int)
        self.layout = QVBoxLayout(self)
        self.scrollArea = QScrollArea(self.parent)

        # Setup scrollarea
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setFixedSize(self.parent.sidebarWidth, self.parent.height())
        self.scrollArea.setStyleSheet("border: none;")
        self.scrollArea.setWidget(self)

        # Setup sidebar itself
        self.setFixedWidth(self.parent.sidebarWidth)
        self.setMinimumHeight(self.parent.height() - 2)  # 2 to fix scroll height
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Shadow is not visible due to it's z-index. Maybe another stacking context?
        # I didn't figure out how to fix it :/
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0)
        self.shadow.setColor(Color(28, 28, 28))
        self.scrollArea.setGraphicsEffect(self.shadow)

        # Create placeholder item
        self.placeholder = Item(self)

    def findItemByName(self, name):
        return next((item for item in self.items if item.name and item.name == name), None)

    def generateName(self):
        name = 65

        while self.findItemByName(chr(name)):
            name += 1

        return chr(name)

    def generateColor(self):
        self.color += self.colorStep + self.colorOffset

        return Color.fromHSL(self.color % 255, 180, 127)

    def updateCanvas(self):
        self.parent.canvas.update()

    def paintEvent(self, event):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Input(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setPlaceholderText(self.parent.parent.parent.css.var("sidebar_itemPlaceholder"))
        self.clearFocus()
        self.installEventFilter(self)
        self.returnPressed.connect(self.onInput)

    # Expression processing
    def parseExpression(self):
        input = self.text().replace(" ", "")
        name = (re.search(r"^[a-zA-Z]+(?==)", input) or [None])[0]
        value = input.replace(name + "=", "") if name else input

        if(not value):
            return self.parent.showIcon(self.parent.icon.plus)

        if(name):
            self.parent.name = name

        try:
            self.parent.number = ComplexNumber(value)
            self.parent.showIcon(self.parent.icon.circle)
        except Exception as err:
            self.parent.parent.parent.verbose and print(err)

            try:
                expr = re.search(r"([a-zA-Z]+)([+\-*\/])([a-zA-Z]+)", value)

                num1 = self.parent.parent.findItemByName(expr[1]).number
                num2 = self.parent.parent.findItemByName(expr[3]).number
                operator = expr[2]

                if(operator == "+"):
                    self.parent.number = num1.add(num2)
                elif(operator == "-"):
                    self.parent.number = num1.sub(num2)
                elif(operator == "*"):
                    self.parent.number = num1.mult(num2)
                elif(operator == "/"):
                    self.parent.number = num1.div(num2)
                else:
                    raise Exception("Invalid expression operator")

                self.parent.showIcon(self.parent.icon.circle)
            except Exception as err:
                self.parent.parent.parent.verbose and print(err)
                self.parent.number = None
                self.parent.showIcon(self.parent.icon.alert)

        self.parent.parent.updateCanvas()

    def processExpression(self):
        isPlaceholder = self.parent.parent.placeholder == self.parent
        input = self.text().replace(" ", "")

        if(not input):
            if(not isPlaceholder and self.parent in self.parent.parent.items):
                self.parent.parent.items.remove(self.parent)
                self.parent.parent.layout.removeWidget(self.parent)
                self.parent.setParent(None)
                self.parent.icon.setParent(None)
                self.parent.parent.updateCanvas()
            else:
                self.parent.showIcon(self.parent.icon.plus)
            return

        self.parseExpression()

        if(isPlaceholder):
            self.parent.parent.placeholder = Item(self.parent.parent)
            self.parent.parent.placeholder.input.setFocus()

        if(not self.parent.name):
            self.parent.name = self.parent.parent.generateName()
            self.setText(self.parent.name + "=" + input)

    # Event emitter
    def eventFilter(self, watched, event):
        type = event.type()

        if(type == QEvent.FocusIn):
            self.onFocus(event)

        if(type == QEvent.FocusOut):
            self.onBlur(event)

        return False

    # Event handlers
    def keyReleaseEvent(self, event):
        self.parseExpression()

    def onInput(self):
        self.processExpression()
        self.clearFocus()

    def onFocus(self, event):
        pass

    def onBlur(self, event):
        self.processExpression()


class SVGIcon(QLabel):
    def __init__(self, file, scale=1):
        super().__init__()

        self.file = file
        self.image = QImage(file)

        self.size = self.image.size() * scale
        self.image = self.image.scaled(self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.setPixmap(QPixmap.fromImage(self.image))
        self.setFixedSize(self.size)
        self.setStyleSheet("border: none")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(self.rect(), self.image, self.rect())


class Icon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QHBoxLayout(self)
        self.plus = SVGIcon("resources/plus.svg", 0.05)
        self.alert = SVGIcon("resources/alert.svg", 0.05)
        self.circle = Circle(self)
        self.number = None

        self.setFixedSize(self.parent.parent.parent.itemHeight, self.parent.parent.parent.itemHeight)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.plus)
        self.layout.addWidget(self.alert)
        self.layout.addWidget(self.circle)

        self.alert.hide()
        self.circle.hide()

    def paintEvent(self, event):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Item(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.name = None
        self.number = None
        self.color = self.parent.generateColor()
        self.layout = QHBoxLayout(self)
        self.icon = Icon(self)
        self.input = Input(self)

        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.setFixedSize(self.parent.parent.sidebarWidth, self.parent.parent.itemHeight)
        self.layout.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.icon)
        self.layout.addWidget(self.input)

        self.parent.layout.addWidget(self)
        self.parent.items.append(self)

        scrollHeight = len(self.parent.items) * self.parent.parent.itemHeight
        self.parent.setMinimumHeight(scrollHeight)
        self.parent.scrollArea.verticalScrollBar().setValue(scrollHeight)

    def showIcon(self, icon: Icon):
        icon != self.icon.plus and self.icon.plus.hide()
        icon != self.icon.alert and self.icon.alert.hide()
        icon != self.icon.circle and self.icon.circle.hide()

        icon.show()

    def paintEvent(self, event):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Circle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.isVisible = True
        self.color = self.parent.parent.color.copy(a=127)
        self.border = self.parent.parent.color
        self.radius = self.parent.parent.parent.parent.css.var("sidebar_circleRadius", int)

        self.setFixedSize(self.radius * 2, self.radius * 2)
        self.setCursor(Qt.PointingHandCursor)
        self.toggleVisibility(True)

    def toggleVisibility(self, state=True):
        color = self.color if state else "transparent"

        self.isVisible = state
        self.setStyleSheet(f"background-color: {color}; border-radius: {self.radius}px; border: 1px solid {self.border};")
        self.parent.parent.number and self.parent.parent.parent.updateCanvas()

    def mousePressEvent(self, event):
        self.toggleVisibility(not self.isVisible)

    def paintEvent(self, event):
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)
