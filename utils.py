from math import floor, pi


def floorMultiple(x: int, n):
    return floor(x / n) * n


def closest(arr, x):
    return arr[min(range(len(arr)), key=lambda i: abs(arr[i] - x))]


def clamp(x, n, m):
    return max(n, min(x, m))


def hideDecimal(x):
    return str(x if x % 1 else floor(x))


def rad2deg(rad):
    return (rad * 180) / pi
