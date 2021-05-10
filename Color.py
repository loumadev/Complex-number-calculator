import re
from PyQt5.QtGui import QColor
import random


class Color(QColor):
    def __init__(self, r, g=0, b=0, a=255):
        if(isinstance(r, str)):
            m = re.search(r"rgba?\s*\((\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})(?:,\s*(\d{1,3}))?\)", r)
            r = int(m[1])
            g = int(m[2])
            b = int(m[3])
            a = int(m[4] or str(a))
        super().__init__(r, g, b, a)

    def copy(self, r=None, g=None, b=None, a=None):
        return Color(
            r or self.red(),
            g or self.green(),
            b or self.blue(),
            a or self.alpha()
        )

    def __str__(self):
        return self.name(QColor.HexArgb)

    def __radd__(self, other):
        return other + str(self)

    @staticmethod
    def fromHSL(h, l, s):
        color = QColor.fromHsl(h, l, s)

        return Color(
            color.red(),
            color.green(),
            color.blue()
        )

    @staticmethod
    def random():
        return Color.fromHSL(random.randint(0, 255), 180, 127)
