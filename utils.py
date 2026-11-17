from math import floor, pi
from typing import List


def floorMultiple(x: float, n: float) -> float:
    return floor(x / n) * n


def closest(arr: List[float], x: float) -> float:
    return arr[min(range(len(arr)), key=lambda i: abs(arr[i] - x))]


def clamp(x: float, n: float, m: float) -> float:
    return max(n, min(x, m))


def hideDecimal(x: float) -> str:
    return str(x if x % 1 else floor(x))


def rad2deg(rad: float) -> float:
    return (rad * 180) / pi
