import random
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple
from Color import Color
from ComplexNumber import ComplexNumber
from ExpressionParser import ASTNode, InterpretError, Interpreter, ParseError, Parser, TokenizeError, Tokenizer, builtinContext, referencesOf
from PyQt5.QtCore import QEvent, QObject, Qt, QSize
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QPaintEvent, QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout, QLineEdit, QScrollArea, QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from Calculator import Calculator


class Sidebar(QWidget):
    def __init__(self, parent: Optional["Calculator"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.items: List["Item"] = []
        self.activeItem: Optional["Item"] = None
        self.color: int = random.randint(0, 255)
        self.colorStep: int = self.parent.css.var("sidebar_colorStep", int)
        self.colorOffset: int = self.parent.css.var("sidebar_colorOffset", int)
        self.maxValues: int = self.parent.css.var("maxValues", int)
        self.layout: QVBoxLayout = QVBoxLayout(self)
        self.scrollArea: QScrollArea = QScrollArea(self.parent)

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
        self.shadow: QGraphicsDropShadowEffect = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(10)
        self.shadow.setOffset(0)
        self.shadow.setColor(Color(28, 28, 28))
        self.scrollArea.setGraphicsEffect(self.shadow)

        # Create placeholder item
        self.placeholder: Item = Item(self)

    def findItemByName(self, name: str) -> Optional["Item"]:
        return next((item for item in self.items if item.name and item.name == name), None)

    def generateName(self) -> str:
        name = 65

        while self.findItemByName(chr(name)):
            name += 1

        return chr(name)

    def generateColor(self) -> Color:
        self.color += self.colorStep + self.colorOffset

        return Color.fromHSL(self.color % 255, 180, 127)

    def updateCanvas(self) -> None:
        self.parent.canvas.update()

    def recompute(self) -> None:
        items = self.items

        nameToItem: Dict[str, "Item"] = {}
        for item in items:
            if(item.name and item.name not in nameToItem):
                nameToItem[item.name] = item

        dependencies: Dict["Item", Set["Item"]] = {}
        dependents: Dict["Item", List["Item"]] = {item: [] for item in items}

        for item in items:
            deps: Set["Item"] = set()

            for name in referencesOf(item.ast) if(item.ast is not None) else []:
                target = nameToItem.get(name)

                if(target is not None):
                    deps.add(target)

            dependencies[item] = deps

            for dep in deps:
                dependents[dep].append(item)

        indegree = {item: len(deps) for item, deps in dependencies.items()}
        queue = [item for item in items if indegree[item] == 0]
        order: List["Item"] = []

        while(queue):
            item = queue.pop(0)
            order.append(item)

            for dependent in dependents[item]:
                indegree[dependent] -= 1

                if(indegree[dependent] == 0):
                    queue.append(dependent)

        unresolved = [item for item in items if indegree[item] > 0]
        unresolvedSet = set(unresolved)

        for item in items:
            item.values = []
            item.evalError = None

        for item in unresolved:
            cycle = self._findCycleFrom(item, dependencies, unresolvedSet)
            item.evalError = ("Circular reference detected: " + " → ".join([dep.name for dep in cycle])) if(cycle) else "Circular reference detected"

        context = builtinContext()
        for name in nameToItem:
            context[name] = []

        for item in order:
            if(item.ast is None):
                continue

            try:
                item.values = Interpreter(context, self.maxValues).interpret(item.ast)
            except InterpretError as err:
                item.evalError = str(err)

            if(item.name and nameToItem.get(item.name) is item):
                context[item.name] = item.values

        for item in items:
            item.error = item.parseError or item.evalError
            item.refreshIcon()
            item.refreshErrorDisplay()

        self.updateCanvas()

    def _findCycleFrom(self, start: "Item", dependencies: Dict["Item", Set["Item"]], unresolvedSet: Set["Item"]) -> Optional[List["Item"]]:
        state: Dict["Item", int] = {start: 1}
        path: List["Item"] = [start]
        stack: List[Tuple["Item", List["Item"]]] = [(start, list(dependencies[start]))]

        while(stack):
            item, deps = stack[-1]
            advanced = False

            for dep in deps:
                if(dep not in unresolvedSet):
                    continue

                if(dep not in state):
                    state[dep] = 1
                    stack[-1] = (item, [d for d in deps if d is not dep])
                    stack.append((dep, list(dependencies[dep])))
                    path.append(dep)
                    advanced = True
                    break

                if(state[dep] == 1):
                    idx = path.index(dep)
                    return path[idx:] + [dep]

            if(not advanced):
                stack.pop()
                path.pop()
                state[item] = 2

        return None

    def paintEvent(self, event: QPaintEvent) -> None:
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Input(QLineEdit):
    def __init__(self, parent: Optional["Item"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.setPlaceholderText(self.parent.parent.parent.css.var("sidebar_itemPlaceholder"))
        self.clearFocus()
        self.installEventFilter(self)
        self.returnPressed.connect(self.onInput)

    # Expression processing
    def parseInput(self) -> Tuple[Optional[str], str]:
        text = self.text()
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\Z", text, re.DOTALL)

        if(match):
            return (match[1], match[2])

        return (None, text)

    def parseExpression(self) -> None:
        item = self.parent
        sidebar = item.parent
        sidebar.activeItem = item

        name, expression = self.parseInput()

        if(name):
            item.name = name

        expression = expression.strip()

        if(not expression):
            item.ast = None
            item.parseError = None

            sidebar.recompute()
            return

        try:
            tokenizer = Tokenizer(expression)
            item.ast = Parser(tokenizer).parse()
            item.parseError = None
        except(TokenizeError, ParseError) as err:
            item.ast = None
            item.parseError = str(err)

        sidebar.recompute()

    def processExpression(self) -> None:
        item = self.parent
        sidebar = item.parent
        isPlaceholder = sidebar.placeholder == item

        if(not self.text().strip()):
            if(not isPlaceholder and item in sidebar.items):
                sidebar.items.remove(item)
                sidebar.layout.removeWidget(item)
                item.setParent(None)
                item.icon.setParent(None)

                if(sidebar.activeItem is item):
                    sidebar.activeItem = None

                sidebar.recompute()
            else:
                item.showIcon(item.icon.plus)
            return

        self.parseExpression()

        if(isPlaceholder):
            sidebar.placeholder = Item(sidebar)
            sidebar.placeholder.input.setFocus()

        if(not item.name):
            item.name = sidebar.generateName()
            self.setText(item.name + "=" + self.text())
            self.parseExpression()

    # Event emitter
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        type = event.type()

        if(type == QEvent.FocusIn):
            self.onFocus(event)

        if(type == QEvent.FocusOut):
            self.onBlur(event)

        return False

    # Event handlers
    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self.parseExpression()

    def onInput(self) -> None:
        self.processExpression()
        self.clearFocus()

    def onFocus(self, event: QEvent) -> None:
        pass

    def onBlur(self, event: QEvent) -> None:
        self.processExpression()


class SVGIcon(QLabel):
    def __init__(self, file: str, scale: float = 1) -> None:
        super().__init__()

        self.file: str = file
        self.image: QImage = QImage(file)

        self.size: QSize = self.image.size() * scale
        self.image = self.image.scaled(self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.setPixmap(QPixmap.fromImage(self.image))
        self.setFixedSize(self.size)
        self.setStyleSheet("border: none")

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(self.rect(), self.image, self.rect())


class Icon(QWidget):
    def __init__(self, parent: Optional["Item"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.plus: SVGIcon = SVGIcon("resources/plus.svg", 0.05)
        self.alert: SVGIcon = SVGIcon("resources/alert.svg", 0.05)
        self.circle: Circle = Circle(self)

        self.setFixedSize(self.parent.parent.parent.itemHeight, self.parent.parent.parent.itemHeight)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.plus)
        self.layout.addWidget(self.alert)
        self.layout.addWidget(self.circle)

        self.alert.hide()
        self.circle.hide()

    def paintEvent(self, event: QPaintEvent) -> None:
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Item(QWidget):
    def __init__(self, parent: Optional["Sidebar"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.name: Optional[str] = None
        self.ast: Optional[ASTNode] = None
        self.values: List[ComplexNumber] = []
        self.parseError: Optional[str] = None
        self.evalError: Optional[str] = None
        self.error: Optional[str] = None
        self.color: Color = self.parent.generateColor()
        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.icon: Icon = Icon(self)
        self.input: Input = Input(self)

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

    def refreshIcon(self) -> None:
        if(self.values):
            self.showIcon(self.icon.circle)
        elif(self.error):
            self.showIcon(self.icon.alert)
        else:
            self.showIcon(self.icon.plus)

    def refreshErrorDisplay(self) -> None:
        self.setToolTip(self.error or "")

        if(self.error):
            self.input.setStyleSheet(f"color: {self.parent.parent.css.var('sidebar_errorColor')};")
        else:
            self.input.setStyleSheet("")

    def showIcon(self, icon: SVGIcon) -> None:
        icon != self.icon.plus and self.icon.plus.hide()
        icon != self.icon.alert and self.icon.alert.hide()
        icon != self.icon.circle and self.icon.circle.hide()

        icon.show()

    def paintEvent(self, event: QPaintEvent) -> None:
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Circle(QWidget):
    def __init__(self, parent: Optional["Icon"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.isVisible: bool = True
        self.color: Color = self.parent.parent.color.copy(a=127)
        self.border: Color = self.parent.parent.color
        self.radius: int = self.parent.parent.parent.parent.css.var("sidebar_circleRadius", int)

        self.setFixedSize(self.radius * 2, self.radius * 2)
        self.setCursor(Qt.PointingHandCursor)
        self.toggleVisibility(True)

    def toggleVisibility(self, state: bool = True) -> None:
        color = self.color if state else self.color.copy(a=26)

        self.isVisible = state
        self.setStyleSheet(f"background-color: {color}; border-radius: {self.radius}px; border: 1px solid {self.border};")
        self.parent.parent.values and self.parent.parent.parent.updateCanvas()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.toggleVisibility(not self.isVisible)

    def paintEvent(self, event: QPaintEvent) -> None:
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)
