import random
import re
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple
from Color import Color
from ComplexNumber import ComplexNumber
from ExpressionParser import ASTNode, InterpretError, Interpreter, ParseError, Parser, TokenizeError, Tokenizer, builtinContext, referencesOf
from utils import clamp, hideDecimal
from PyQt5.QtCore import QEvent, QObject, QPointF, Qt, QSize, QTimer
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QPaintEvent, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLayout, QLineEdit, QMenu, QScrollArea, QSizePolicy, QStyle, QStyleOption, QVBoxLayout, QWidget

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

        # Right-side reservation: a 1px separator line plus the vertical
        # scrollbar, so the items are never covered by the scrollbar
        self.separatorWidth: int = 1
        self.scrollbarWidth: int = self.style().pixelMetric(QStyle.PM_ScrollBarExtent)
        self.reservedWidth: int = self.scrollbarWidth + self.separatorWidth

        # Setup scrollarea
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setFixedSize(self.parent.sidebarWidth, self.parent.height())
        self.scrollArea.setStyleSheet(
            f"border: none; border-right: {self.separatorWidth}px solid {self.parent.css.var('sidebar_borderColor')};"
        )
        self.scrollArea.setWidget(self)

        # Setup sidebar itself
        self.setFixedWidth(self.parent.sidebarWidth)
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, self.reservedWidth, 0)
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

    def refreshScrollHeight(self) -> None:
        # The scroll area (and thus its viewport) is pinned to the window
        # height, so that is the baseline the sidebar must at least fill
        total = sum(item.rowHeight for item in self.items)
        desired = max(self.parent.height(), total)

        # Pin both bounds so the sidebar actually shrinks back when the
        # content gets smaller (minimum alone leaves the old height in place)
        self.setMinimumHeight(desired)
        self.setMaximumHeight(desired)
        self.scrollArea.verticalScrollBar().setValue(total)

    def showTypeMenu(self, item: "Item", pos) -> None:
        c = self.parent.css
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {c.var('sidebar_backgroundColor')}; border: 1px solid {c.var('sidebar_borderColor')};"
            f" font-family: {c.var('sidebar_fontFamily')}; font-size: 13px; color: {c.var('sidebar_color')}; }}"
            f"QMenu::item {{ padding: 4px 20px 4px 10px; }}"
            f"QMenu::item:selected {{ background-color: {c.var('sidebar_borderColor')}; }}"
        )

        textAct = menu.addAction("Text")
        sliderAct = menu.addAction("Slider")
        textAct.setCheckable(True)
        sliderAct.setCheckable(True)

        (textAct if(item.type == "text") else sliderAct).setChecked(True)
        chosen = menu.exec_(pos)

        if(chosen is None):
            return

        if(chosen is textAct):
            if(item.type != "text"):
                item.setType("text")

            item.input.setFocus()
        else:
            item.setType("slider")

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
            if(item.type == "slider"):
                item.values = [ComplexNumber([item.slider.value, 0.0])]
            elif(item.ast is not None):
                try:
                    item.values = Interpreter(context, self.maxValues).interpret(item.ast)
                except InterpretError as err:
                    item.evalError = str(err)

            if(item.name and nameToItem.get(item.name) is item):
                context[item.name] = item.values

        # Propagate breakage down the dependency chain. An item whose
        # dependency is invalid silently evaluates to nothing, so it must be
        # reported as invalid too (processed in topological order, so every
        # dependency is already classified).
        broken: Dict["Item", bool] = {}

        for item in order:
            hasError = item.evalError is not None or item.parseError is not None
            brokenDep = next((dep for dep in dependencies[item] if broken.get(dep, False)), None)
            broken[item] = hasError or brokenDep is not None

            if(brokenDep is not None and not hasError):
                item.evalError = f"Dependency '{brokenDep.name}' is invalid"

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

        # The name always tracks the text: removing the "[id]=" prefix clears it
        item.name = name

        expression = expression.strip()

        # A truly empty row is a valid blank state; a named row with no
        # expression ("A=") is an incomplete input and must surface an error
        if(not expression and name is None):
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
                sidebar.refreshScrollHeight()
            else:
                item.showIcon(item.icon.plus)
            return

        self.parseExpression()

        if(isPlaceholder):
            sidebar.placeholder = Item(sidebar)
            sidebar.placeholder.input.setFocus()

        # Only brand-new rows get an autogenerated id; a row the user stripped
        # of its id stays anonymous (and stops being referenceable)
        if(isPlaceholder and not item.name):
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


class SliderWidget(QWidget):
    def __init__(self, parent: Optional["Item"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.min: float = self.parent.parent.parent.css.var("slider_defaultMin", float)
        self.max: float = self.parent.parent.parent.css.var("slider_defaultMax", float)
        self.step: float = self.parent.parent.parent.css.var("slider_defaultStep", float)
        self.value: float = self.min
        self._dragging: bool = False

        self.trackWidth: int = self.parent.parent.parent.css.var("slider_trackWidth", int)
        self.handleRadius: int = self.parent.parent.parent.css.var("slider_handleRadius", int)
        self.trackColor: Color = self.parent.parent.parent.css.var("slider_trackColor", Color)
        self.handleColor: Color = self.parent.parent.parent.css.var("slider_handleColor", Color)

        self.setFixedHeight(self.handleRadius * 2 + 4)
        self.setMinimumWidth(40)
        self.setCursor(Qt.PointingHandCursor)

    def setRange(self, lo: float, hi: float) -> None:
        if(lo > hi):
            lo, hi = hi, lo

        self.min, self.max = lo, hi
        self.setValue(self.value)

    def setStep(self, step: float) -> None:
        self.step = step if(step > 0) else self.parent.parent.parent.css.var("slider_defaultStep", float)
        self.setValue(self.value)

    def setValue(self, v: float, snap: bool = True) -> None:
        self.value = clamp(v, self.min, self.max)

        if(snap and self.step > 0 and self.max > self.min):
            self.value = self.min + round((self.value - self.min) / self.step) * self.step

        self.value = round(clamp(self.value, self.min, self.max), 10)
        self.update()
        self.parent._syncSlider()

    def _padding(self) -> float:
        return self.handleRadius + 1

    def _xToValue(self, x: float) -> float:
        pad = self._padding()
        frac = clamp((x - pad) / max(1.0, self.width() - 2 * pad), 0.0, 1.0)
        return self.min + frac * (self.max - self.min)

    def _valueToX(self, v: float) -> float:
        pad = self._padding()
        frac = 0.0 if(self.max == self.min) else clamp((v - self.min) / (self.max - self.min), 0.0, 1.0)
        return pad + frac * max(1.0, self.width() - 2 * pad)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._dragging = True
        self.setValue(self._xToValue(event.x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if(self._dragging):
            self.setValue(self._xToValue(event.x()))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cy = self.height() / 2
        x0 = self._padding()
        x1 = self.width() - self._padding()
        xv = self._valueToX(self.value)

        p.setPen(QPen(self.trackColor, self.trackWidth, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(x0), int(cy), int(x1), int(cy))

        p.setPen(QPen(self.parent.color, self.trackWidth, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(x0), int(cy), int(xv), int(cy))

        p.setPen(QPen(self.parent.color, 2))
        p.setBrush(self.handleColor)
        p.drawEllipse(QPointF(xv, cy), self.handleRadius, self.handleRadius)


class PlayPauseIcon(QWidget):
    def __init__(self, parent: Optional["Item"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        size = self.parent.parent.parent.css.var("sidebar_playButtonSize", int)
        self.play: SVGIcon = SVGIcon("resources/play.svg", 0.6)
        self.pause: SVGIcon = SVGIcon("resources/pause.svg", 0.6)

        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.play)
        self.layout.addWidget(self.pause)

        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setPlaying(False)

    def setPlaying(self, playing: bool) -> None:
        self.play.setVisible(not playing)
        self.pause.setVisible(playing)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.parent._toggleAnimation()


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

        # Let clicks on the passive icons fall through to the type menu
        self.plus.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.alert.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.parent.parent.showTypeMenu(self.parent, event.globalPos())

    def paintEvent(self, event: QPaintEvent) -> None:
        o = QStyleOption()
        o.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, o, p, self)


class Item(QWidget):
    def __init__(self, parent: Optional["Sidebar"] = None) -> None:
        super().__init__(parent)
        self.parent = parent

        self.type: str = "text"
        self.name: Optional[str] = None
        self.ast: Optional[ASTNode] = None
        self.values: List[ComplexNumber] = []
        self.parseError: Optional[str] = None
        self.evalError: Optional[str] = None
        self.error: Optional[str] = None
        self.color: Color = self.parent.generateColor()
        self.rowHeight: int = self._heightFor(self.type)
        self.layout: QHBoxLayout = QHBoxLayout(self)
        self.icon: Icon = Icon(self)

        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self.setFixedSize(self.parent.parent.sidebarWidth - self.parent.reservedWidth, self.rowHeight)
        self.layout.setAlignment(Qt.AlignLeft)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.icon)

        self._buildContent()

        self.parent.layout.addWidget(self)
        self.parent.items.append(self)
        self.parent.refreshScrollHeight()

    def _heightFor(self, t: str) -> int:
        return self.parent.parent.css.var("sidebar_sliderItemHeight", int) if(t == "slider") else self.parent.parent.itemHeight

    # Content (re)building
    def _buildContent(self) -> None:
        if(getattr(self, "content", None) is not None):
            self.layout.removeWidget(self.content)
            self.content.setParent(None)
            self.content.deleteLater()
            self.content = None

        self.content: QWidget = QWidget(self)
        self.layout.addWidget(self.content, 1)

        if(self.type == "slider"):
            self._buildSliderContent()
        else:
            self._buildTextContent()

    def _buildTextContent(self) -> None:
        lay = QHBoxLayout(self.content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.input: Input = Input(self)
        lay.addWidget(self.input)

    def _buildSliderContent(self) -> None:
        if(not self.name):
            self.name = self.parent.generateName()

        outer = QVBoxLayout(self.content)
        outer.setContentsMargins(8, 4, 8, 6)
        outer.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.playPause: PlayPauseIcon = PlayPauseIcon(self)
        self.nameLabel: QLabel = QLabel(self.name + " =", self.content)
        self.slider: SliderWidget = SliderWidget(self)
        self.valueLabel: QLabel = QLabel(self.content)
        self.valueLabel.setMinimumWidth(34)
        self.valueLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.nameLabel.setStyleSheet(f"font-family: {self.parent.parent.css.var('sidebar_fontFamily')}; font-size: 15px; color: {self.parent.parent.css.var('sidebar_color')};")
        self.valueLabel.setStyleSheet(self.nameLabel.styleSheet())
        row1.addWidget(self.playPause)
        row1.addWidget(self.nameLabel)
        row1.addWidget(self.slider, 1)
        row1.addWidget(self.valueLabel)
        outer.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(3)
        self.minInput: QLineEdit = self._boundInput("min", self.slider.min)
        self.maxInput: QLineEdit = self._boundInput("max", self.slider.max)
        self.stepInput: QLineEdit = self._boundInput("step", self.slider.step)
        row2.addWidget(self._boundLabel("min"))
        row2.addWidget(self.minInput)
        row2.addSpacing(6)
        row2.addWidget(self._boundLabel("max"))
        row2.addWidget(self.maxInput)
        row2.addSpacing(6)
        row2.addWidget(self._boundLabel("step"))
        row2.addWidget(self.stepInput)
        row2.addStretch(1)
        outer.addLayout(row2)

        self.animating: bool = False
        self.animDir: int = 1
        self.animTimer: QTimer = QTimer(self.content)
        self.animTimer.setInterval(self.parent.parent.css.var("sidebar_animInterval", int))
        self.animTimer.timeout.connect(self._animateTick)

        self._syncSliderLabel()

    def _boundLabel(self, text: str) -> QLabel:
        c = self.parent.parent.css
        lab = QLabel(text, self.content)
        lab.setStyleSheet(f"font-family: {c.var('sidebar_fontFamily')}; font-size: 11px; color: {c.var('sidebar_color')};")
        return lab

    def _boundInput(self, placeholder: str, initial: float) -> QLineEdit:
        c = self.parent.parent.css
        inp = QLineEdit(self.content)
        inp.setPlaceholderText(placeholder)
        inp.setToolTip(placeholder)
        inp.setText(self._fmt(initial))
        inp.setFixedWidth(40)
        inp.setAlignment(Qt.AlignCenter)
        inp.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {c.var('sidebar_borderColor')}; border-radius: 4px; background: transparent;"
            f" font-family: {c.var('sidebar_fontFamily')}; font-size: 12px; color: {c.var('sidebar_color')}; padding: 1px 3px; }}"
        )
        inp.editingFinished.connect(self._applyBounds)
        return inp

    def _applyBounds(self) -> None:
        def read(inp: QLineEdit, fallback: float) -> float:
            try:
                return float(inp.text().strip())
            except ValueError:
                return fallback

        self.slider.setRange(read(self.minInput, self.slider.min), read(self.maxInput, self.slider.max))
        self.slider.setStep(read(self.stepInput, self.slider.step))

        for inp, value in [(self.minInput, self.slider.min), (self.maxInput, self.slider.max), (self.stepInput, self.slider.step)]:
            inp.blockSignals(True)
            inp.setText(self._fmt(value))
            inp.blockSignals(False)

        self._syncSlider()

    # Type switching
    def setType(self, t: str) -> None:
        if(t == self.type):
            return

        self._stopAnimation()
        self.type = t
        self.rowHeight = self._heightFor(t)
        self.ast = None
        self.parseError = None
        self.evalError = None
        self.error = None
        self.values = []

        self.setFixedSize(self.parent.parent.sidebarWidth - self.parent.reservedWidth, self.rowHeight)
        self.icon.setFixedSize(self.parent.parent.itemHeight, self.rowHeight)
        self._buildContent()
        self.parent.refreshScrollHeight()
        self.parent.recompute()

        # Converting the "add new" row into a slider leaves a fresh row behind
        if(t == "slider" and self is self.parent.placeholder):
            self.parent.placeholder = Item(self.parent)
            self.parent.placeholder.input.setFocus()

    # Slider helpers
    def _fmt(self, v: float) -> str:
        return hideDecimal(round(v, 6))

    def _syncSliderLabel(self) -> None:
        self.valueLabel.setText(self._fmt(self.slider.value))

    def _syncSlider(self) -> None:
        if(self.type != "slider"):
            return

        self._syncSliderLabel()
        self.parent.recompute()

    def _stopAnimation(self) -> None:
        if(getattr(self, "animTimer", None) is not None):
            self.animTimer.stop()

    def _toggleAnimation(self) -> None:
        if(self.type != "slider"):
            return

        self.animating = not self.animating
        self.playPause.setPlaying(self.animating)

        if(self.animating):
            self.animTimer.start()
        else:
            self.animTimer.stop()

    def _animateTick(self) -> None:
        if(self.type != "slider" or not self.animating):
            return

        s = self.slider
        step = s.step if(s.step > 0 and s.max > s.min) else (s.max - s.min) / 100
        v = s.value + self.animDir * step

        if(v >= s.max):
            v = s.max
            self.animDir = -1
        elif(v <= s.min):
            v = s.min
            self.animDir = 1

        s.setValue(v, snap=False)

    def refreshIcon(self) -> None:
        if(self.values):
            self.showIcon(self.icon.circle)
        elif(self.error):
            self.showIcon(self.icon.alert)
        else:
            self.showIcon(self.icon.plus)

    def refreshErrorDisplay(self) -> None:
        self.setToolTip(self.error or "")

        if(self.type != "text"):
            return

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
