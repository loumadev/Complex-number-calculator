import cmath
import math
from typing import List, Optional, Union
from utils import hideDecimal, rad2deg


class ComplexNumber:
    def __init__(self, number: Union[float, int, List[float]], sign: str = "i") -> None:
        if(isinstance(number, list)):
            self.r: float = float(number[0])
            self.i: float = float(number[1])
        elif(isinstance(number, (float, int))):
            self.r: float = float(number)
            self.i: float = 0.0
        else:
            raise TypeError(f"{number!r} is not a valid complex number")

        self.sign: str = sign
        self.distance: float = math.hypot(self.r, self.i)
        self.angle: float = math.atan2(self.i, self.r)

    def toComplex(self) -> complex:
        return complex(self.r, self.i)

    @staticmethod
    def fromComplex(value: complex) -> "ComplexNumber":
        return ComplexNumber([value.real, value.imag])

    def isZero(self) -> bool:
        return self.r == 0 and self.i == 0

    def add(self, x: "ComplexNumber") -> "ComplexNumber":
        return self._binop(lambda a, b: a + b, x)

    def sub(self, x: "ComplexNumber") -> "ComplexNumber":
        return self._binop(lambda a, b: a - b, x)

    def mult(self, x: "ComplexNumber") -> "ComplexNumber":
        return self._binop(lambda a, b: a * b, x)

    def div(self, x: "ComplexNumber") -> "ComplexNumber":
        if(x.isZero()):
            raise ZeroDivisionError("Division by zero")

        return self._binop(lambda a, b: a / b, x)

    def _binop(self, op, x: "ComplexNumber") -> "ComplexNumber":
        return self.fromComplex(op(self.toComplex(), x.toComplex()))

    def neg(self) -> "ComplexNumber":
        return ComplexNumber([-self.r, -self.i], self.sign)

    def conj(self) -> "ComplexNumber":
        return ComplexNumber([self.r, -self.i], self.sign)

    def reciprocal(self) -> "ComplexNumber":
        return ComplexNumber([0.0, 0.0], self.sign).div(self)

    def pow(self, x: "ComplexNumber") -> "ComplexNumber":
        if(self.isZero()):
            if(x.isZero()):
                return ComplexNumber([1.0, 0.0], self.sign)
            if(x.i == 0 and x.r > 0):
                return ComplexNumber([0.0, 0.0], self.sign)
            raise ZeroDivisionError("Zero cannot be raised to a non-positive power")

        return self.fromComplex(self.toComplex() ** x.toComplex())

    def powInt(self, n: int) -> "ComplexNumber":
        if(self.isZero() and n < 0):
            raise ZeroDivisionError("Zero cannot be raised to a negative power")

        return self.fromComplex(self.toComplex() ** n)

    def exp(self) -> "ComplexNumber":
        return self.fromComplex(cmath.exp(self.toComplex()))

    def log(self) -> "ComplexNumber":
        if(self.isZero()):
            raise ValueError("log(0) is undefined")

        return self.fromComplex(cmath.log(self.toComplex()))

    def log10(self) -> "ComplexNumber":
        return self.log().div(ComplexNumber([math.log(10.0), 0.0], self.sign))

    def logBase(self, base: "ComplexNumber") -> "ComplexNumber":
        if(base.isZero()):
            raise ValueError("Logarithm base cannot be zero")
        if(base.r == 1.0 and base.i == 0.0):
            raise ZeroDivisionError("Logarithm base cannot be one")

        return self.log().div(base.log())

    def sqrt(self) -> "ComplexNumber":
        return self.fromComplex(cmath.sqrt(self.toComplex()))

    def sin(self) -> "ComplexNumber":
        return self.fromComplex(cmath.sin(self.toComplex()))

    def cos(self) -> "ComplexNumber":
        return self.fromComplex(cmath.cos(self.toComplex()))

    def tan(self) -> "ComplexNumber":
        return self.fromComplex(cmath.tan(self.toComplex()))

    def sinh(self) -> "ComplexNumber":
        return self.fromComplex(cmath.sinh(self.toComplex()))

    def cosh(self) -> "ComplexNumber":
        return self.fromComplex(cmath.cosh(self.toComplex()))

    def tanh(self) -> "ComplexNumber":
        return self.fromComplex(cmath.tanh(self.toComplex()))

    def asin(self) -> "ComplexNumber":
        return self.fromComplex(cmath.asin(self.toComplex()))

    def acos(self) -> "ComplexNumber":
        return self.fromComplex(cmath.acos(self.toComplex()))

    def atan(self) -> "ComplexNumber":
        return self.fromComplex(cmath.atan(self.toComplex()))

    def abs(self) -> "ComplexNumber":
        return ComplexNumber([self.distance, 0.0], self.sign)

    def arg(self) -> "ComplexNumber":
        if(self.isZero()):
            raise ValueError("arg(0) is undefined")

        return ComplexNumber([self.angle, 0.0], self.sign)

    def real(self) -> "ComplexNumber":
        return ComplexNumber([self.r, 0.0], self.sign)

    def imag(self) -> "ComplexNumber":
        return ComplexNumber([self.i, 0.0], self.sign)

    def __str__(self, form: str = "r", precision: Optional[int] = None) -> str:
        r: float = self.r
        i: float = self.i

        if(precision is not None):
            r = round(r, precision)
            i = round(i, precision)

            if(r == 0):
                r = 0.0
            if(i == 0):
                i = 0.0

        if(r != 0 and abs(r) < 1e-12 * abs(i)):
            r = 0.0
        elif(i != 0 and abs(i) < 1e-12 * abs(r)):
            i = 0.0

        iAbs = abs(i)
        s = "-" if i < 0 else "+"

        d = hideDecimal(round(self.distance, 2))
        a = hideDecimal(round(rad2deg(self.angle), 2))

        if(form == "r"):
            if(r == 0 and i == 0):
                return "0"

            space = (" " if r and iAbs else "")
            rStr = (hideDecimal(r) if r else "") + space
            iStr = (s if (rStr or s == "-") and iAbs else "") + space + (hideDecimal(iAbs) + self.sign if iAbs else "")
            return rStr + iStr
        elif(form == "a"):
            return f"{d} / {a}°"
        elif(form == "p"):
            return f"{d} * (cos({a}°) + {self.sign} * sin({a}°))"
        elif(form == "e"):
            return f"{d} * e ^ ({self.sign} * {a}°)"
        else:
            raise TypeError("Unknown number form. Supported r = rectangular, a = angle, p = polar, e = exponential")

    def __repr__(self) -> str:
        return f"ComplexNumber {{r: {self.r}, i: {self.i}, sign: {self.sign}, distance: {self.distance}, angle: {self.angle}}}"
