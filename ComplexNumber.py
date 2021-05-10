import re
import math
from typing import List, Union
from utils import hideDecimal, rad2deg


class ComplexNumber:
    def __init__(self, number: Union[str, List[float]], sign: str = "i"):
        r = i = "0"

        # parse
        if(isinstance(number, str) and number):
            number = re.sub(r"\s", "", number.replace("−", "-"))
            match = re.search(rf"[+\\-]?(?:[0-9.,]*[{sign}](?![0-9a-z.,])|[{sign}][0-9.,]+)", number)

            i = match[0] if match else "0"
            r = float(number.replace(str(i), "") or "0")
            i = "1" if i == sign else i.replace(sign, "")
            i = float(i + "1" if i == "+" or i == "-" else i)

        elif (isinstance(number, list)):
            r = float(number[0])
            i = float(number[1])
        else:
            raise TypeError(number + " is not a valid complex number")

        # init
        self.r = r
        self.i = i
        self.sign = sign

        self.distance = math.hypot(self.r, self.i)
        self.angle = math.atan2(self.i, self.r)

    def add(self, x: "ComplexNumber") -> "ComplexNumber":
        if(self.sign != x.sign):
            raise TypeError("Cannot add two numbers with different imaginary parts")

        r = self.r + x.r
        c = self.i + x.i

        return ComplexNumber([r, c], self.sign)

    def sub(self, x: "ComplexNumber") -> "ComplexNumber":
        if(self.sign != x.sign):
            raise TypeError("Cannot subtract two numbers with different imaginary parts")

        r = self.r - x.r
        c = self.i - x.i

        return ComplexNumber([r, c], self.sign)

    def mult(self, x: "ComplexNumber") -> "ComplexNumber":
        if(self.sign != x.sign):
            raise TypeError("Cannot multiply two numbers with different imaginary parts")

        r = self.r * x.r - self.i * x.i
        c = self.r * x.i + x.r * self.i

        return ComplexNumber([r, c], self.sign)

    def div(self, x: "ComplexNumber") -> "ComplexNumber":
        if(self.sign != x.sign):
            raise TypeError("Cannot divide two numbers with different imaginary parts")

        r = self.r * x.r + self.i * x.i
        c = self.i * x.r - self.r * x.i
        d = x.r * x.r + x.i * x.i

        return ComplexNumber([r / d, c / d], self.sign)

    def __str__(self, form: str = "r") -> "ComplexNumber":
        i = float(re.sub(r"^[+\-]", "", str(self.i)))
        s = "-" if self.i < 0 else "+"

        d = hideDecimal(round(self.distance, 2))
        a = hideDecimal(round(rad2deg(self.angle), 2))

        if(form == "r"):
            space = (" " if self.r and i else "")
            r = (hideDecimal(self.r) if self.r else "") + space
            i = (s if (r or s == "-") and i else "") + space + (hideDecimal(i) + self.sign if i else "")
            return r + i
        elif(form == "a"):
            return f"{d} / {a}°"
        elif(form == "p"):
            return f"{d} * (cos({a}°) + {self.sign} * sin({a}°))"
        elif(form == "e"):
            return f"{d} * e ^ ({self.sign} * {a}°)"
        else:
            raise TypeError("Unknown number form. Supported r = rectangular, a = angle, p = polar, e = exponential")

    def __repr__(self):
        return f"ComplexNumber {{r: {self.r}, i: {self.i}, sign: {self.sign}, distance: {self.distance}, angle: {self.angle}}}"
