import itertools
import math
import re
from enum import Enum, auto
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union

from ComplexNumber import ComplexNumber

MAX_VALUES: int = 8
BRANCH_TOLERANCE: float = 1e-9
_TWO_PI: float = 2.0 * math.pi


class ExpressionError(Exception):
    def __init__(self, message: str, position: Optional[int] = None, source: Optional[str] = None) -> None:
        super().__init__(message)
        self.message: str = message
        self.position: Optional[int] = position
        self.source: Optional[str] = source

    def __str__(self) -> str:
        if(self.position is None or not self.source):
            return self.message

        return f"{self.message} at position {self.position}: {self.source}"


class TokenizeError(ExpressionError):
    pass


class ParseError(ExpressionError):
    pass


class InterpretError(ExpressionError):
    pass


class TokenType(Enum):
    NUMBER = auto()
    IDENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    DSTAR = auto()
    SLASH = auto()
    CARET = auto()
    LPAR = auto()
    RPAR = auto()
    COMMA = auto()
    PIPE = auto()
    END = auto()


class Token:
    def __init__(self, type: TokenType, text: str, position: int, source: str, previewRadius: int = 8) -> None:
        self.type: TokenType = type
        self.text: str = text
        self.position: int = position
        self.end: int = position + len(text)
        self.source: str = source

        start = max(0, position - previewRadius)
        stop = min(len(source), self.end + previewRadius)
        self.preview: str = source[start:stop]

    def describe(self) -> str:
        if(self.type is TokenType.END):
            return "end of input"

        return f"'{self.text}' ({self.type.name})"

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.text!r}, pos={self.position}, preview={self.preview!r})"


_NUMBER_RE = re.compile(r"(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SINGLE_CHARS: Dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "^": TokenType.CARET,
    "(": TokenType.LPAR,
    ")": TokenType.RPAR,
    ",": TokenType.COMMA,
    "|": TokenType.PIPE
}


class Tokenizer:
    def __init__(self, source: str) -> None:
        self.source: str = source.replace("\u2212", "-")
        self._tokens: List[Token] = []
        self._index: int = 0
        self._cursor: int = 0
        self._exhausted: bool = False

    def peekToken(self, offset: int = 0) -> Token:
        offset = max(offset, 0)
        self._ensure(self._index + offset + 1)

        return self._tokens[min(self._index + offset, len(self._tokens) - 1)]

    def nextToken(self) -> Token:
        token = self.peekToken(0)

        if(token.type is not TokenType.END):
            self._index += 1

        return token

    def isAtEnd(self) -> bool:
        return self.peekToken(0).type is TokenType.END

    def save(self) -> Tuple[int, int, int, bool]:
        return (self._index, self._cursor, len(self._tokens), self._exhausted)

    def restore(self, state: Tuple[int, int, int, bool]) -> None:
        self._index, self._cursor, size, self._exhausted = state
        del self._tokens[size:]

    def _ensure(self, count: int) -> None:
        while(len(self._tokens) < count and not self._exhausted):
            self._tokens.append(self._tokenizeNext())

    def _tokenizeNext(self) -> Token:
        source = self.source
        pos = self._cursor

        while(pos < len(source) and source[pos].isspace()):
            pos += 1

        if(pos >= len(source)):
            self._cursor = pos
            self._exhausted = True
            return Token(TokenType.END, "", pos, source)

        ch = source[pos]

        if(ch.isdigit() or (ch == "." and pos + 1 < len(source) and source[pos + 1].isdigit())):
            token = Token(TokenType.NUMBER, _NUMBER_RE.match(source, pos)[0], pos, source)

            if(not math.isfinite(float(token.text))):
                self._cursor = pos
                raise TokenizeError(f"Numeric value '{token.text}' is out of range", pos, source)
        elif(ch.isalpha() or ch == "_"):
            token = Token(TokenType.IDENT, _IDENT_RE.match(source, pos)[0], pos, source)
        elif(source.startswith("**", pos)):
            token = Token(TokenType.DSTAR, "**", pos, source)
        elif(ch in _SINGLE_CHARS):
            token = Token(_SINGLE_CHARS[ch], ch, pos, source)
        else:
            self._cursor = pos
            raise TokenizeError(f"Unexpected character '{ch}'", pos, source)

        self._cursor = pos + len(token.text)
        return token


class ASTOperator(Enum):
    ADD = auto()
    SUB = auto()
    MULT = auto()
    DIV = auto()
    POW = auto()
    POS = auto()
    NEG = auto()


class ASTNode:
    def __init__(self, token: Token) -> None:
        self.token: Token = token
        self.position: int = token.position

    def __repr__(self) -> str:
        return f"{type(self).__name__}(pos={self.position})"


class ExpressionASTNode(ASTNode):
    pass


class LiteralASTNode(ASTNode):
    def __init__(self, value: float, token: Token) -> None:
        super().__init__(token)
        self.value: float = value

    def __repr__(self) -> str:
        return f"LiteralASTNode(value={self.value}, pos={self.position})"


class IdentifierASTNode(ASTNode):
    def __init__(self, name: str, token: Token) -> None:
        super().__init__(token)
        self.name: str = name

    def __repr__(self) -> str:
        return f"IdentifierASTNode(name={self.name!r}, pos={self.position})"


class BinaryExpressionASTNode(ExpressionASTNode):
    def __init__(self, operator: ASTOperator, left: ASTNode, right: ASTNode, token: Token) -> None:
        super().__init__(token)
        self.operator: ASTOperator = operator
        self.left: ASTNode = left
        self.right: ASTNode = right

    def __repr__(self) -> str:
        return f"BinaryExpressionASTNode(op={self.operator.name}, left={self.left!r}, right={self.right!r})"


class UnaryExpressionASTNode(ExpressionASTNode):
    def __init__(self, operator: ASTOperator, operand: ASTNode, token: Token) -> None:
        super().__init__(token)
        self.operator: ASTOperator = operator
        self.operand: ASTNode = operand

    def __repr__(self) -> str:
        return f"UnaryExpressionASTNode(op={self.operator.name}, operand={self.operand!r})"


class CallExpressionASTNode(ExpressionASTNode):
    def __init__(self, name: str, arguments: List[ExpressionASTNode], token: Token) -> None:
        super().__init__(token)
        self.name: str = name
        self.arguments: List[ExpressionASTNode] = arguments

    def __repr__(self) -> str:
        return f"CallExpressionASTNode(name={self.name!r}, args={self.arguments!r})"


class Parser:
    def __init__(self, tokenizer: Tokenizer) -> None:
        self.t: Tokenizer = tokenizer

    def parse(self) -> ASTNode:
        try:
            node = self.parseExpression()
        except RecursionError:
            raise ParseError("Expression is too deeply nested", None, self.t.source)

        token = self.t.peekToken(0)

        if(not self.t.isAtEnd()):
            raise ParseError(f"Unexpected {token.describe()}", token.position, self.t.source)

        return node

    def parseExpression(self) -> ExpressionASTNode:
        left = self.parseTerm()

        while(True):
            token = self.t.peekToken(0)

            if(token.type is TokenType.PLUS):
                self.t.nextToken()
                left = BinaryExpressionASTNode(ASTOperator.ADD, left, self.parseTerm(), token)
            elif(token.type is TokenType.MINUS):
                self.t.nextToken()
                left = BinaryExpressionASTNode(ASTOperator.SUB, left, self.parseTerm(), token)
            else:
                return left

    def parseTerm(self) -> ExpressionASTNode:
        left = self.parseUnary()

        while(True):
            token = self.t.peekToken(0)

            if(token.type is TokenType.STAR):
                self.t.nextToken()
                left = BinaryExpressionASTNode(ASTOperator.MULT, left, self.parseUnary(), token)
            elif(token.type is TokenType.SLASH):
                self.t.nextToken()
                left = BinaryExpressionASTNode(ASTOperator.DIV, left, self.parseUnary(), token)
            elif(token.type in (TokenType.LPAR, TokenType.IDENT, TokenType.NUMBER)):
                left = BinaryExpressionASTNode(ASTOperator.MULT, left, self.parseUnary(), token)
            elif(token.type is TokenType.PIPE):
                state = self.t.save()

                try:
                    right = self.parseUnary()
                    left = BinaryExpressionASTNode(ASTOperator.MULT, left, right, token)
                except ParseError:
                    self.t.restore(state)
                    return left
            else:
                return left

    def parseUnary(self) -> ExpressionASTNode:
        token = self.t.peekToken(0)

        if(token.type is TokenType.PLUS):
            self.t.nextToken()
            return UnaryExpressionASTNode(ASTOperator.POS, self.parseUnary(), token)
        if(token.type is TokenType.MINUS):
            self.t.nextToken()
            return UnaryExpressionASTNode(ASTOperator.NEG, self.parseUnary(), token)

        return self.parsePower()

    def parsePower(self) -> ExpressionASTNode:
        base = self.parsePrimary()
        token = self.t.peekToken(0)

        if(token.type is TokenType.DSTAR or token.type is TokenType.CARET):
            self.t.nextToken()
            return BinaryExpressionASTNode(ASTOperator.POW, base, self.parseUnary(), token)

        return base

    def parsePrimary(self) -> ExpressionASTNode:
        token = self.t.peekToken(0)

        if(token.type is TokenType.NUMBER):
            self.t.nextToken()
            return LiteralASTNode(float(token.text), token)

        if(token.type is TokenType.IDENT):
            if(self.t.peekToken(1).type is TokenType.LPAR):
                state = self.t.save()

                try:
                    return self.parseCall(token)
                except ParseError:
                    self.t.restore(state)

            self.t.nextToken()
            return IdentifierASTNode(token.text, token)

        if(token.type is TokenType.LPAR):
            return self.parseParen()

        if(token.type is TokenType.PIPE):
            return self.parseAbs(token)

        raise ParseError(f"Expected an expression, got {token.describe()}", token.position, self.t.source)

    def parseCall(self, ident: Token) -> CallExpressionASTNode:
        self.t.nextToken()
        self.t.nextToken()

        arguments: List[ExpressionASTNode] = []

        if(self.t.peekToken(0).type is TokenType.RPAR):
            self.t.nextToken()
        else:
            while(True):
                arguments.append(self.parseExpression())
                token = self.t.peekToken(0)

                if(token.type is TokenType.COMMA):
                    self.t.nextToken()
                    continue
                if(token.type is TokenType.RPAR):
                    self.t.nextToken()
                    break

                raise ParseError(f"Expected ',' or ')', got {token.describe()}", token.position, self.t.source)

        return CallExpressionASTNode(ident.text, arguments, ident)

    def parseAbs(self, lpipe: Token) -> CallExpressionASTNode:
        self.t.nextToken()
        node = self.parseExpression()
        token = self.t.peekToken(0)

        if(token.type is not TokenType.PIPE):
            raise ParseError(f"Expected '|', got {token.describe()}", token.position, self.t.source)

        self.t.nextToken()
        return CallExpressionASTNode("abs", [node], lpipe)

    def parseParen(self) -> ExpressionASTNode:
        self.t.nextToken()
        node = self.parseExpression()
        token = self.t.peekToken(0)

        if(token.type is not TokenType.RPAR):
            raise ParseError(f"Expected ')', got {token.describe()}", token.position, self.t.source)

        self.t.nextToken()
        return node


def referencesOf(node: ASTNode) -> List[str]:
    names: List[str] = []

    def walk(n: ASTNode) -> None:
        if(isinstance(n, IdentifierASTNode)):
            names.append(n.name)
        elif(isinstance(n, CallExpressionASTNode)):
            names.append(n.name)
            for arg in n.arguments:
                walk(arg)
        elif(isinstance(n, BinaryExpressionASTNode)):
            walk(n.left)
            walk(n.right)
        elif(isinstance(n, UnaryExpressionASTNode)):
            walk(n.operand)

    walk(node)
    return names


def _branchSequence() -> Iterator[int]:
    yield 0

    k = 1
    while(True):
        yield k
        yield -k
        k += 1


def _valuesClose(a: ComplexNumber, b: ComplexNumber) -> bool:
    return (
        math.isclose(a.r, b.r, rel_tol=BRANCH_TOLERANCE, abs_tol=BRANCH_TOLERANCE)
        and math.isclose(a.i, b.i, rel_tol=BRANCH_TOLERANCE, abs_tol=BRANCH_TOLERANCE)
    )


def _isIntegerValue(x: ComplexNumber) -> bool:
    return x.i == 0.0 and float(x.r).is_integer()


def _logBranch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.log()
    return ComplexNumber([value.r, value.i + _TWO_PI * k], z.sign)


def _logBaseBranch(z: ComplexNumber, base: ComplexNumber, k: int) -> ComplexNumber:
    numerator = z.log()
    numerator = ComplexNumber([numerator.r, numerator.i + _TWO_PI * k], z.sign)
    return numerator.div(base.log())


def _log10Branch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.log()
    return ComplexNumber([value.r / math.log(10.0), (value.i + _TWO_PI * k) / math.log(10.0)], z.sign)


def _sqrtBranch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.sqrt()
    return value.neg() if k % 2 else value


def _powBranch(a: ComplexNumber, b: ComplexNumber, k: int) -> ComplexNumber:
    if(_isIntegerValue(b)):
        return a.powInt(int(b.r))

    if(a.isZero()):
        raise ZeroDivisionError("Zero cannot be raised to a non-integer power")

    logK = ComplexNumber([math.log(a.distance), a.angle + _TWO_PI * k], a.sign)
    return b.mult(logK).exp()


def _asinBranch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.asin()

    if(value.i == 0.0 and abs(abs(value.r) - math.pi / 2.0) < BRANCH_TOLERANCE):
        return ComplexNumber([value.r, value.i + _TWO_PI * k], z.sign)

    if(k % 2 == 0):
        return ComplexNumber([value.r, value.i + _TWO_PI * (k // 2)], z.sign)

    return ComplexNumber([math.pi - value.r, -value.i + _TWO_PI * ((k - 1) // 2)], z.sign)


def _acosBranch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.acos()

    if(value.i == 0.0 and (abs(value.r) < BRANCH_TOLERANCE or abs(value.r - math.pi) < BRANCH_TOLERANCE)):
        return ComplexNumber([value.r, value.i + _TWO_PI * k], z.sign)

    if(k % 2 == 0):
        return ComplexNumber([value.r, value.i + _TWO_PI * (k // 2)], z.sign)

    return ComplexNumber([-value.r, -value.i + _TWO_PI * ((k - 1) // 2)], z.sign)


def _atanBranch(z: ComplexNumber, k: int) -> ComplexNumber:
    value = z.atan()
    return ComplexNumber([value.r + math.pi * k, value.i], z.sign)


class ComplexFunction:
    def __init__(
        self,
        name: str,
        arity: Union[int, Tuple[int, int]],
        fn: Callable[[List[ComplexNumber], int], ComplexNumber],
        multi: bool = False,
        period: Optional[int] = None
    ) -> None:
        self.name: str = name
        self.arity: Union[int, Tuple[int, int]] = arity
        self.fn: Callable[[List[ComplexNumber], int], ComplexNumber] = fn
        self.multi: bool = multi
        self.period: Optional[int] = period

    def arityError(self, count: int) -> Optional[str]:
        if(isinstance(self.arity, int)):
            if(count != self.arity):
                plural = "s" if(self.arity != 1) else ""
                return f"Function '{self.name}' expects {self.arity} argument{plural}, got {count}"
            return None

        low, high = self.arity

        if(count < low or count > high):
            return f"Function '{self.name}' expects {low} or {high} arguments, got {count}"

        return None


def _buildFunctionRegistry() -> Dict[str, ComplexFunction]:
    functions: Dict[str, ComplexFunction] = {
        "exp": ComplexFunction("exp", 1, lambda args, k: args[0].exp()),
        "sin": ComplexFunction("sin", 1, lambda args, k: args[0].sin()),
        "cos": ComplexFunction("cos", 1, lambda args, k: args[0].cos()),
        "tan": ComplexFunction("tan", 1, lambda args, k: args[0].tan()),
        "sinh": ComplexFunction("sinh", 1, lambda args, k: args[0].sinh()),
        "cosh": ComplexFunction("cosh", 1, lambda args, k: args[0].cosh()),
        "tanh": ComplexFunction("tanh", 1, lambda args, k: args[0].tanh()),
        "abs": ComplexFunction("abs", 1, lambda args, k: args[0].abs()),
        "arg": ComplexFunction("arg", 1, lambda args, k: args[0].arg()),
        "conj": ComplexFunction("conj", 1, lambda args, k: args[0].conj()),
        "re": ComplexFunction("re", 1, lambda args, k: args[0].real()),
        "im": ComplexFunction("im", 1, lambda args, k: args[0].imag()),
        "log": ComplexFunction(
            "log",
            (1, 2),
            lambda args, k: _logBaseBranch(args[0], args[1], k) if(len(args) == 2) else _logBranch(args[0], k),
            multi=True
        ),
        "log10": ComplexFunction("log10", 1, lambda args, k: _log10Branch(args[0], k), multi=True),
        "sqrt": ComplexFunction("sqrt", 1, lambda args, k: _sqrtBranch(args[0], k), multi=True, period=2),
        "pow": ComplexFunction("pow", 2, lambda args, k: _powBranch(args[0], args[1], k), multi=True),
        "asin": ComplexFunction("asin", 1, lambda args, k: _asinBranch(args[0], k), multi=True),
        "acos": ComplexFunction("acos", 1, lambda args, k: _acosBranch(args[0], k), multi=True),
        "atan": ComplexFunction("atan", 1, lambda args, k: _atanBranch(args[0], k), multi=True)
    }

    for name, function in list(functions.items()):
        if(not function.multi):
            continue

        arity: Union[int, Tuple[int, int]]
        if(isinstance(function.arity, int)):
            arity = function.arity + 1
        else:
            arity = (function.arity[0] + 1, function.arity[1] + 1)

        def makeK(original: ComplexFunction, arity: Union[int, Tuple[int, int]]) -> ComplexFunction:
            def branchK(args: List[ComplexNumber], k: int) -> ComplexNumber:
                selector = args[-1]

                if(not _isIntegerValue(selector)):
                    raise ValueError(f"Branch index must be a real integer, got {selector}")

                n = int(selector.r)
                if(original.period is not None):
                    n %= original.period

                return original.fn(args[:-1], n)

            return ComplexFunction(original.name + "_k", arity, branchK)

        functions[name + "_k"] = makeK(function, arity)

    return functions


FUNCTIONS: Dict[str, ComplexFunction] = _buildFunctionRegistry()


def builtinContext() -> Dict[str, List[ComplexNumber]]:
    return {
        "i": [ComplexNumber([0.0, 1.0])],
        "pi": [ComplexNumber([math.pi, 0.0])],
        "e": [ComplexNumber([math.e, 0.0])]
    }


class Interpreter:
    def __init__(
        self,
        context: Dict[str, List[ComplexNumber]],
        maxValues: int = MAX_VALUES,
        functions: Optional[Dict[str, ComplexFunction]] = None
    ) -> None:
        self.context: Dict[str, List[ComplexNumber]] = context
        self.maxValues: int = max(1, maxValues)
        self.functions: Dict[str, ComplexFunction] = functions if(functions is not None) else FUNCTIONS

    def interpret(self, node: ASTNode) -> List[ComplexNumber]:
        values = self._eval(node)
        unique: List[ComplexNumber] = []

        for value in values:
            if(not any(_valuesClose(value, u) for u in unique)):
                unique.append(value)

        return unique

    def _safe(self, fn: Callable[[], ComplexNumber], node: ASTNode) -> ComplexNumber:
        try:
            return fn()
        except(InterpretError):
            raise
        except(ValueError, ZeroDivisionError, OverflowError) as err:
            message = str(err) or type(err).__name__
            raise InterpretError(message, node.position, node.token.source) from err

    def _eval(self, node: ASTNode) -> List[ComplexNumber]:
        if(isinstance(node, LiteralASTNode)):
            return [ComplexNumber(node.value)]

        if(isinstance(node, IdentifierASTNode)):
            if(node.name in self.context):
                return list(self.context[node.name])
            raise InterpretError(f"Unknown identifier '{node.name}'", node.position, node.token.source)

        if(isinstance(node, UnaryExpressionASTNode)):
            values = self._eval(node.operand)

            if(node.operator is ASTOperator.NEG):
                return [v.neg() for v in values]

            return values

        if(isinstance(node, BinaryExpressionASTNode)):
            left = self._eval(node.left)
            right = self._eval(node.right)

            if(node.operator is ASTOperator.POW):
                return self._applyPow(left, right, node)

            op = {
                ASTOperator.ADD: lambda a, b: a.add(b),
                ASTOperator.SUB: lambda a, b: a.sub(b),
                ASTOperator.MULT: lambda a, b: a.mult(b),
                ASTOperator.DIV: lambda a, b: a.div(b)
            }[node.operator]

            result: List[ComplexNumber] = []

            for a in left:
                for b in right:
                    result.append(self._safe(lambda a=a, b=b: op(a, b), node))

                    if(len(result) >= self.maxValues):
                        return result

            return result

        if(isinstance(node, CallExpressionASTNode)):
            return self._evalCall(node)

        raise InterpretError(f"Unsupported AST node '{type(node).__name__}'", node.position, node.token.source)

    def _applyPow(self, left: List[ComplexNumber], right: List[ComplexNumber], node: BinaryExpressionASTNode) -> List[ComplexNumber]:
        result: List[ComplexNumber] = []

        for a in left:
            for b in right:
                if(_isIntegerValue(b)):
                    result.append(self._safe(lambda a=a, b=b: a.powInt(int(b.r)), node))

                    if(len(result) >= self.maxValues):
                        return result
                else:
                    for k in _branchSequence():
                        value = self._safe(lambda a=a, b=b, k=k: _powBranch(a, b, k), node)

                        if(any(_valuesClose(value, u) for u in result)):
                            break

                        result.append(value)

                        if(len(result) >= self.maxValues):
                            return result

            if(len(result) >= self.maxValues):
                return result

        return result

    def _evalCall(self, node: CallExpressionASTNode) -> List[ComplexNumber]:
        argValues: List[List[ComplexNumber]] = [self._eval(arg) for arg in node.arguments]
        function = self.functions.get(node.name)

        if(function is not None):
            error = function.arityError(len(node.arguments))

            if(error):
                raise InterpretError(error, node.position, node.token.source)

            if(not function.multi):
                result = []

                for combo in itertools.product(*argValues):
                    result.append(self._safe(lambda c=list(combo): function.fn(c, 0), node))

                    if(len(result) >= self.maxValues):
                        return result

                return result

            result = []

            for combo in itertools.product(*argValues):
                for k in _branchSequence():
                    value = self._safe(lambda c=list(combo), k=k: function.fn(c, k), node)

                    if(any(_valuesClose(value, u) for u in result)):
                        break

                    result.append(value)

                    if(len(result) >= self.maxValues):
                        return result

            return result

        if(node.name in self.context):
            result = []
            base = self.context[node.name]

            for combo in itertools.product(base, *argValues):
                value = combo[0]

                for arg in combo[1:]:
                    value = self._safe(lambda v=value, arg=arg: v.mult(arg), node)

                result.append(value)

                if(len(result) >= self.maxValues):
                    return result

            return result

        raise InterpretError(f"Unknown function '{node.name}'", node.position, node.token.source)
