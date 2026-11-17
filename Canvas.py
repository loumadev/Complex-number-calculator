# importing modules
from Color import Color
from math import floor

from utils import clamp, closest, floorMultiple
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPen, QPixmap, QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QLabel
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from Calculator import Calculator


class Canvas(QPixmap):
    def __init__(self, parent: Optional["Calculator"] = None) -> None:
        super().__init__(parent.width() - parent.sidebarWidth, parent.height())
        self.parent = parent

        # Internal
        self.label: QLabel = QLabel()
        self.label.setPixmap(self)
        self.label.stackUnder(self.parent)

        # Properties
        self.parent = parent
        self.origin: List[float] = [0, 0]
        self.prev: List[float] = [0, 0]
        self.scale: float = 1

        # Settings
        self.pixelRatio: int = self.parent.css.var("canvas_pixelRatio", int)
        self.scaleRate: int = self.parent.css.var("canvas_scaleRate", int)
        self.scaleMax: float = self.parent.css.var("canvas_scaleMax", float)
        self.scaleMin: float = self.parent.css.var("canvas_scaleMin", float)
        self.pointRadius: int = self.parent.css.var("canvas_pointRadius", int)
        self.originRadius: int = self.parent.css.var("canvas_originRadius", int)
        self.connectionLineWidth: float = self.parent.css.var("canvas_connectionLineWidth", float)
        self.backgroundColor: Color = self.parent.css.var("canvas_backgroundColor", Color)
        self.gridColor: Color = self.parent.css.var("canvas_gridColor", Color)
        self.axisColor: Color = self.parent.css.var("canvas_axisColor", Color)
        self.helperColor: Color = self.parent.css.var("canvas_helperColor", Color)
        self.textColor: Color = self.parent.css.var("canvas_textColor", Color)
        self.helperAxis: int = self.parent.css.var("canvas_helperAxis", int)
        self.axisFontSize: float = self.parent.css.var("canvas_axisFontSize", float)
        self.axisFontFamily: str = self.parent.css.var("canvas_axisFontFamily")
        self.numberFontSize: float = self.parent.css.var("canvas_numberFontSize", float)
        self.numberFontFamily: str = self.parent.css.var("canvas_numberFontFamily")
        self.numberPrecision: int = self.parent.css.var("canvas_numberPrecision", int)

        # Precomputing values
        self.axisFont: QFont = QFont(self.axisFontFamily, int(self.axisFontSize))
        self.axisMetrics: QFontMetrics = QFontMetrics(self.axisFont)
        self.numberFont: QFont = QFont(self.numberFontFamily, int(self.numberFontSize))
        self.numberMetrics: QFontMetrics = QFontMetrics(self.numberFont)

        self._generateScaleRange()
        self.updateScale()

        # Setup
        self.update()

        self.label.wheelEvent = self.wheelEvent
        self.label.mouseMoveEvent = self.mouseMoveEvent
        self.label.mousePressEvent = self.mousePressEvent
        self.label.mouseReleaseEvent = self.mouseReleaseEvent

    # Util functions

    # Clears the canvas
    def clear(self) -> None:
        self.fill(Qt.transparent)

    # Renders the updated values
    def update(self) -> None:
        self.clear()

        self.renderGrid()
        self.renderPoints()

        background = QImage(self.size(), QImage.Format_ARGB32)
        background.fill(self.backgroundColor)
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationAtop)
        painter.drawImage(0, 0, background)

        self.refresh()

    # Repaints the canvas
    def refresh(self) -> None:
        self.label.setPixmap(self)  # Dumb way, but whatever... Performance is sufficient
        # self.parent.update()

    # Generates scaling range array used for the axis scaling steps
    def _generateScaleRange(self) -> None:
        self.scaleRange: List[float] = [1]

        # Converted from C-style for loop because Python doesn't know the for loop :D The best language ever...

        i = 1
        while(self.scaleRange[-1] < (1/self.scaleMin)):
            self.scaleRange.append(self.scaleRange[-1] * (2 if (i + 1) % 3 else 2.5))
            i += 1

        i = 1
        while(self.scaleRange[0] > (1/self.scaleMax)):
            self.scaleRange.insert(0, self.scaleRange[0] / (2 if (i + 1) % 3 else 2.5))
            i += 1

    # Rendering

    # Updates the scale values
    def updateScale(self) -> None:
        self.unit: float = self.scale * self.pixelRatio

        self.axisStep: float = closest(self.scaleRange, 1 / self.scale)
        self.unitStep: float = self.unit * self.axisStep

    # Renders the points (numbers)
    def renderPoints(self) -> None:
        painter = QPainter(self)
        painter.setFont(self.numberFont)

        originX = self.origin[0] * self.scale + self.width() / 2
        originY = self.origin[1] * self.scale + self.height() / 2

        for item in self.parent.sidebar.items:
            circle = item.icon.circle

            if(not item.values or not circle.isVisible):
                continue

            points = []

            for value in item.values:
                x = originX + value.r * self.pixelRatio * self.scale
                y = originY - value.i * self.pixelRatio * self.scale
                points.append((x, y))

            if(len(points) > 1):
                painter.setPen(QPen(circle.border, self.connectionLineWidth, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin))

                for (x1, y1), (x2, y2) in zip(points, points[1:]):
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            for value, (x, y) in zip(item.values, points):
                label = value.__str__("r", self.numberPrecision)

                self.drawCircle(
                    painter,
                    x,
                    y,
                    self.pointRadius,
                    circle.color,
                    circle.border
                )

                painter.setPen(circle.border)

                painter.drawText(
                    int(x - self.numberMetrics.boundingRect(label).width()/2),
                    int(y - 10),
                    label
                )

    # Renders the grid (this was the tricky part)
    def renderGrid(self) -> None:
        # Prepare painter
        painter = QPainter(self)
        painter.setPen(self.gridColor)
        painter.setFont(self.axisFont)

        # Calculate origin position after scaling (translated to the center of the canvas)
        originX = self.origin[0] * self.scale + self.width() / 2
        originY = self.origin[1] * self.scale + self.height() / 2

        # Calculate offset for first line to start, based on origin position
        offX = originX % self.unitStep
        offY = originY % self.unitStep

        # Used to fix some numbering issues
        axisOffsetX = self.axisStep if originX % self.unitStep else 0
        axisOffsetY = self.axisStep if originY % self.unitStep else 0

        # Render vertical axis
        for i in range(-(self.helperAxis + 1), round(self.width() / self.unitStep) * self.helperAxis + 1):
            x = offX + i * self.unitStep / self.helperAxis  # X coord of the line
            isAxis = floor(x) == floor(originX)             # true if the line is origin axis (0)
            isHelper = i % self.helperAxis                  # true if the line is a helper line

            # Calculate number for the axis
            number = round(floorMultiple((i / self.helperAxis - originX / self.unitStep) * self.axisStep, self.axisStep) + axisOffsetX, 10)
            numberStr = str(number if self.axisStep < 1 and number % 1 else floor(number))

            # Setup a pen
            painter.setPen(self.axisColor if isAxis else (self.helperColor if isHelper else self.gridColor))

            # Draw line (if the line is a helper line, draw it behind everything else)
            isHelper and painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            painter.drawLine(int(x), 0, int(x), self.height())
            isHelper and painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw number for axis
            if(not isHelper):
                rect = self.axisMetrics.boundingRect(numberStr)
                w = rect.width()
                h = rect.height() - self.axisFontSize / 2

                painter.setPen(self.textColor)
                painter.drawText(
                    int(x - w - 4),
                    int(clamp(originY + h + 2, h + 2, self.height() - 3)),
                    numberStr
                )

        # Render horizontal axis
        for i in range(-(self.helperAxis + 1), round(self.height() / self.unitStep) * self.helperAxis + 1):
            y = offY + i * self.unitStep / self.helperAxis  # Y coord of the line
            isAxis = floor(y) == floor(originY)             # true if the line is origin axis (0)
            isHelper = i % self.helperAxis                  # true if the line is a helper line

            # Calculate number for the axis
            number = round(floorMultiple((i / self.helperAxis - originY / self.unitStep) * self.axisStep, self.axisStep) + axisOffsetY, 10)
            numberStr = str(number if self.axisStep < 1 and number % 1 else floor(number))

            # Setup a pen
            painter.setPen(self.axisColor if isAxis else (self.helperColor if isHelper else self.gridColor))

            # Draw line (if the line is a helper line, draw it behind everything else)
            isHelper and painter.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            painter.drawLine(0, int(y), self.width(), int(y))
            isHelper and painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw number for axis (and prevent from drawing the "0" two times)
            if(not isHelper and numberStr != "0"):
                rect = self.axisMetrics.boundingRect(numberStr)
                w = rect.width()
                h = rect.height() - self.axisFontSize / 2

                painter.setPen(self.textColor)
                painter.drawText(
                    int(clamp(originX - w - 4, 3, self.width() - w - 4)),
                    int(y + h + 2),
                    numberStr
                )

        # Draw dot at the origin center
        painter.setPen(QPen(Qt.black, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.black)

        # Render origin
        self.drawCircle(
            painter,
            originX,
            originY,
            self.originRadius,
            self.axisColor
        )

    def drawCircle(self, painter: QPainter, x: float, y: float, r: int, fill: Optional[QColor] = None, stroke: Optional[QColor] = None, strokeWidth: int = 1) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        stroke and painter.setPen(QPen(stroke, strokeWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        fill and painter.setBrush(fill)

        painter.drawEllipse(int(x) - r, int(y) - r, r * 2, r * 2)
        painter.setRenderHint(QPainter.Antialiasing, False)

    # Events

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.prev[0] = event.x()
        self.prev[1] = event.y()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.parent.setCursor(Qt.ArrowCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self.parent.setCursor(Qt.ClosedHandCursor)

        x = event.x()
        y = event.y()

        dx = x - self.prev[0]
        dy = y - self.prev[1]

        self.origin[0] += dx * (1 / self.scale)
        self.origin[1] += dy * (1 / self.scale)

        self.prev[0] = x
        self.prev[1] = y

        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        d = 1 if event.angleDelta().y() > 0 else -1

        self.scale += d * self.scale / self.scaleRate
        self.scale = clamp(self.scale, self.scaleMin, self.scaleMax)

        self.updateScale()
        self.update()
