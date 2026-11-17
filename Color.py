import re
from PyQt5.QtGui import QColor
import random
from typing import Optional, Union


class Color(QColor):
    def __init__(self, r: Union[str, int], g: int = 0, b: int = 0, a: int = 255) -> None:
        if(isinstance(r, str)):
            m = re.search(r"rgba?\s*\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})(?:,\s*(\d{1,3}))?\)", r)
            r = int(m[1])
            g = int(m[2])
            b = int(m[3])
            a = int(m[4] or str(a))
        super().__init__(r, g, b, a)

    def copy(self, r: Optional[int] = None, g: Optional[int] = None, b: Optional[int] = None, a: Optional[int] = None) -> "Color":
        return Color(
            r or self.red(),
            g or self.green(),
            b or self.blue(),
            a or self.alpha()
        )

    def __str__(self) -> str:
        return self.name(QColor.HexArgb)

    def __radd__(self, other: str) -> str:
        return other + str(self)

    @staticmethod
    def fromHSL(h: int, l: int, s: int) -> "Color":
        color = QColor.fromHsl(h, l, s)

        return Color(
            color.red(),
            color.green(),
            color.blue()
        )

    @staticmethod
    def random() -> "Color":
        return Color.fromHSL(random.randint(0, 255), 180, 127)
