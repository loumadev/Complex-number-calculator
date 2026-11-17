import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ComplexNumber import ComplexNumber
from ExpressionParser import (
    ASTOperator, BinaryExpressionASTNode, CallExpressionASTNode, IdentifierASTNode,
    InterpretError, Interpreter, LiteralASTNode, ParseError, Parser, TokenizeError,
    Tokenizer, TokenType, UnaryExpressionASTNode, builtinContext, referencesOf
)

PASSED = 0
FAILED = []

def check(name, cond):
    global PASSED
    if(cond):
        PASSED += 1
    else:
        FAILED.append(name)
        print(f"FAIL: {name}")

def tokenize(src):
    t = Tokenizer(src)
    out = []
    while(not t.isAtEnd()):
        out.append(t.nextToken())
    out.append(t.peekToken(0))
    return out

def parse(src):
    return Parser(Tokenizer(src)).parse()

def ev(src, ctx=None, maxv=8):
    context = builtinContext()
    if(ctx):
        context.update(ctx)
    return Interpreter(context, maxv).interpret(parse(src))

def evstr(src, ctx=None, maxv=8):
    return [str(v) for v in ev(src, ctx, maxv)]

def parseErr(src):
    try:
        parse(src)
        return None
    except ParseError as e:
        return e

# ---------------- Tokenizer ----------------
toks = tokenize("3 + 4.5 * x - 2**3 / (1, .5e2) ^ i")
check("tok types", [t.type for t in toks] == [
    TokenType.NUMBER, TokenType.PLUS, TokenType.NUMBER, TokenType.STAR, TokenType.IDENT,
    TokenType.MINUS, TokenType.NUMBER, TokenType.DSTAR, TokenType.NUMBER, TokenType.SLASH,
    TokenType.LPAR, TokenType.NUMBER, TokenType.COMMA, TokenType.NUMBER, TokenType.RPAR,
    TokenType.CARET, TokenType.IDENT, TokenType.END
])
check("tok text", [t.text for t in toks[:3]] == ["3", "+", "4.5"])
check("tok exponent", toks[13].text == ".5e2")
check("tok positions", toks[2].position == 4 and toks[1].position == 2)
check("tok preview slice", "4.5" in toks[2].preview)

try:
    Tokenizer("3 + ! 2").peekToken(2)
    check("tok error raised", False)
except TokenizeError as e:
    check("tok error raised", True)
    check("tok error pos", e.position == 4)
    check("tok error msg", "!" in e.message)

try:
    Tokenizer("1e400").peekToken(0)
    check("tok overflow raised", False)
except TokenizeError:
    check("tok overflow raised", True)

check("tok unicode minus", tokenize("3−4")[1].type == TokenType.MINUS)

# peekToken offsets
t = Tokenizer("1 2 3")
check("peek 0", t.peekToken(0).text == "1")
check("peek 1", t.peekToken(1).text == "2")
check("peek 2", t.peekToken(2).text == "3")
check("next advances", t.nextToken().text == "1" and t.peekToken(0).text == "2")
check("peek at end", t.peekToken(99).type == TokenType.END)

# save/restore
t = Tokenizer("a b c")
s = t.save()
t.nextToken()
t.nextToken()
t.restore(s)
check("restore", t.peekToken(0).text == "a")

# ---------------- Parser structure ----------------
ast = parse("3i")
check("3i is binary mult", isinstance(ast, BinaryExpressionASTNode) and ast.operator == ASTOperator.MULT)
check("3i left literal", isinstance(ast.left, LiteralASTNode) and ast.left.value == 3)
check("3i right ident", isinstance(ast.right, IdentifierASTNode) and ast.right.name == "i")

for src in ["3i", "3*i", "3(i)", "3*(i)", "(3)*(i)"]:
    a = parse(src)
    ok = (
        isinstance(a, BinaryExpressionASTNode) and a.operator == ASTOperator.MULT
        and isinstance(a.left, LiteralASTNode) and a.left.value == 3
        and isinstance(a.right, IdentifierASTNode) and a.right.name == "i"
    )
    check(f"{src} structure", ok)

# JS precedence
a = parse("2+3*4")
check("prec 1", a.operator == ASTOperator.ADD and isinstance(a.right, BinaryExpressionASTNode) and a.right.operator == ASTOperator.MULT)

a = parse("2*3+4*5")
check("prec 2", a.operator == ASTOperator.ADD and a.left.operator == ASTOperator.MULT and a.right.operator == ASTOperator.MULT)

a = parse("10-3-2")
check("left assoc sub", a.operator == ASTOperator.SUB and isinstance(a.left, BinaryExpressionASTNode) and a.left.operator == ASTOperator.SUB)

a = parse("100/10/2")
check("left assoc div", a.operator == ASTOperator.DIV and a.left.operator == ASTOperator.DIV)

a = parse("2**3**2")
check("right assoc pow", a.operator == ASTOperator.POW and isinstance(a.right, BinaryExpressionASTNode) and a.right.operator == ASTOperator.POW)

a = parse("2^3^2")
check("caret right assoc", a.operator == ASTOperator.POW and a.right.operator == ASTOperator.POW)

a = parse("-2**2")
check("unary looser than pow", isinstance(a, UnaryExpressionASTNode) and a.operator == ASTOperator.NEG and isinstance(a.operand, BinaryExpressionASTNode) and a.operand.operator == ASTOperator.POW)

a = parse("2** -3")
check("pow right unary", isinstance(a, BinaryExpressionASTNode) and a.operator == ASTOperator.POW and isinstance(a.right, UnaryExpressionASTNode))

a = parse("2*-3")
check("mult unary right", a.operator == ASTOperator.MULT and isinstance(a.right, UnaryExpressionASTNode))

a = parse("2**3*2")
check("pow tighter than mult", a.operator == ASTOperator.MULT and a.left.operator == ASTOperator.POW)

a = parse("sqrt(4, 5)")
check("call args", isinstance(a, CallExpressionASTNode) and a.name == "sqrt" and len(a.arguments) == 2)

a = parse("(1+2)*(3)")
check("paren transparent", isinstance(a, BinaryExpressionASTNode) and a.operator == ASTOperator.MULT and isinstance(a.left, BinaryExpressionASTNode) and a.left.operator == ASTOperator.ADD)

a = parse("i(3)")
check("ident call", isinstance(a, CallExpressionASTNode) and a.name == "i")

# parser errors
e = parseErr("1+")
check("err 1+", e is not None and e.position == 2)
e = parseErr("(1")
check("err (1", e is not None and ")" in e.message)
e = parseErr("1 2 3 4 5 6 7 8 9 10")
check("err trailing not raised for implicit mult", e is None)
e = parseErr(")1")
check("err )1", e is not None)
e = parseErr("2**")
check("err 2**", e is not None)
e = parseErr("^3")
check("err ^3", e is not None)
e = parseErr("1,2")
check("err 1,2", e is not None)
e = parseErr("f(1,")
check("err f(1,", e is not None)
check("f(1 2) is valid (implicit mult)", isinstance(parse("f(1 2)"), CallExpressionASTNode))
e = parseErr("("*20 + "1" + ")"*19)
check("unbalanced parens error", e is not None)
check("nesting ok", parse("("*100 + "1" + ")"*100) is not None)
e = parseErr("("*500 + "1" + ")"*500)
check("nesting too deep error", e is not None and "deeply nested" in e.message)

# backtracking: i(1+ -> identifier + implicit mult, error at missing operand/paren
e = parseErr("i(1+")
check("backtrack call", e is not None and e.position == 4)

# ---------------- Interpreter ----------------
check("ev 3+4i", evstr("3+4i") == ["3 + 4i"])
check("ev 3i", evstr("3i") == ["3i"])
check("ev 2*3+4", evstr("2*3+4") == ["10"])
check("ev 2**3**2", evstr("2**3**2") == ["512"])
check("ev -2**2", evstr("-2**2") == ["-4"])
check("ev 2**-3", evstr("2**-3") == ["0.125"])
check("ev 2^-1", evstr("2^-1") == ["0.5"])
check("ev 1/4", evstr("1/4") == ["0.25"])
check("ev i*i", evstr("i*i") == ["-1"])
check("ev 1/i", evstr("1/i") == ["-1i"])
check("ev 1.5e3", evstr("1.5e3") == ["1500"])
check("ev .5", evstr(".5") == ["0.5"])
check("ev 1e-2", evstr("1e-2") == ["0.01"])
check("ev exp(i*pi)", evstr("exp(i*pi)")[0].startswith("-1"))
check("ev sin(0)", evstr("sin(0)") == ["0"])
check("ev sqrt(4)", evstr("sqrt(4)") == ["2", "-2"])
check("ev 2^0.5 count", len(evstr("2^0.5")) == 2)
check("ev 4^0.5", evstr("4^0.5")[0] == "2")
check("ev 8^(1/3) count", len(evstr("8^(1/3)")) == 3)
check("ev log(i) count 8", len(evstr("log(i)")) == 8)
check("ev log(i) principal", evstr("log(i)")[0] == "1.5707963267948966i")
check("ev log(8,2) principal", evstr("log(8, 2)")[0] == "3")
check("ev log10(100) principal", evstr("log10(100)")[0] == "2")
check("ev sqrt_k(4,1)", evstr("sqrt_k(4, 1)") == ["-2"])
check("ev sqrt_k(4,2) wraps", evstr("sqrt_k(4, 2)") == ["2"])
check("ev sqrt_k(4,-1) wraps", evstr("sqrt_k(4, -1)") == ["-2"])
check("ev log_k(i,0)", evstr("log_k(i, 0)")[0] == "1.5707963267948966i")
check("ev log_k(i,1)", evstr("log_k(i, 1)")[0] == "7.853981633974483i")
check("ev log_k(i,-1)", evstr("log_k(i, -1)")[0] == "-4.71238898038469i")

# _k computes k-th directly without generating earlier ones
t0 = time.time()
v = ev("log_k(i, 1000000)")[0]
t1 = time.time()
check("log_k large k fast", t1 - t0 < 0.5)
check("log_k large k value", abs(v.i - (math.pi / 2 + 1000000 * 2 * math.pi)) < 1e-6 and abs(v.r) < 1e-6)

check("ev i(3) implicit", evstr("i(3)") == ["3i"])
check("ev 2i**2", evstr("2i**2") == ["-2"])
check("ev (2)(3)", evstr("(2)(3)") == ["6"])
check("ev (2)i", evstr("(2)i") == ["2i"])
check("ev abs(3+4i)", evstr("abs(3+4i)") == ["5"])
check("ev arg(i)", evstr("arg(i)")[0] == "1.5707963267948966")
check("ev conj", evstr("conj(3+4i)") == ["3 - 4i"])
check("ev re", evstr("re(3+4i)") == ["3"])
check("ev im", evstr("im(3+4i)") == ["4"])
check("ev asin(1) count", len(evstr("asin(1)")) == 8)
check("ev asin(1) principal", evstr("asin(1)")[0] == "1.5707963267948966")
check("ev acos(0) principal", evstr("acos(0)")[0] == "1.5707963267948966")
check("ev atan(1) principal", abs(ev("atan(1)")[0].r - 0.7853981633974483) < 1e-9)
check("ev atan(1) second", abs(ev("atan(1)")[1].r - 3.9269908169872414) < 1e-9)
check("ev 0^2", evstr("0^2") == ["0"])
check("ev 0^0", evstr("0^0") == ["1"])
check("ev -3", evstr("-3") == ["-3"])
check("ev ++3", evstr("++3") == ["3"])
check("ev 2 * -3", evstr("2 * -3") == ["-6"])
check("ev 10-2-3", evstr("10-2-3") == ["5"])
check("ev 100/10/2", evstr("100/10/2") == ["5"])
check("ev pi", evstr("pi")[0] == "3.141592653589793")
check("ev e", evstr("e")[0] == "2.718281828459045")
check("ev sqrt(9)+1 cartesian", sorted(evstr("sqrt(9)+1")) == ["-2", "4"])
check("ev sqrt(9)*i cartesian", sorted(evstr("sqrt(9)*i")) == ["-3i", "3i"])

# maxValues cap
check("maxValues cap", len(evstr("log(i)", maxv=3)) == 3)

# interpreter errors
def interpErr(src, ctx=None):
    try:
        ev(src, ctx)
        return None
    except InterpretError as e:
        return e

e = interpErr("1/0")
check("err div0", e is not None and "Division by zero" in e.message)
e = interpErr("foo(1)")
check("err unknown fn", e is not None and "foo" in e.message)
e = interpErr("A+1")
check("err unknown ident", e is not None and "A" in e.message)
e = interpErr("A+1", {"A": [ComplexNumber([1, 0])]})
check("ok known ident", e is None)
e = interpErr("exp(1, 2)")
check("err arity", e is not None and "expects 1 argument" in e.message)
e = interpErr("log(0)")
check("err log0", e is not None and "log(0)" in e.message)
e = interpErr("arg(0)")
check("err arg0", e is not None)
e = interpErr("0^-1")
check("err 0^-1", e is not None)
e = interpErr("sqrt_k(4, 1.5)")
check("err k not int", e is not None and "integer" in e.message)
e = interpErr("log(1, 1)")
check("err log base 1", e is not None)

# context multi-valued propagation
vals = ev("B+1", {"B": ev("sqrt(4)")})
check("context multi-valued", sorted(str(v) for v in vals) == ["-1", "3"])

# references
check("references", sorted(set(referencesOf(parse("exp(A*B)+i(C)")))) == ["A", "B", "C", "exp", "i"])

# ---------------- Pipe |x| ----------------
check("pipe basic", evstr("|3+4i|") == ["5"])
check("pipe ident", evstr("|x|", {"x": [ComplexNumber([3, 4])]}) == ["5"])
check("pipe implicit left", evstr("2|3|") == ["6"])
check("pipe implicit right", evstr("|2|3") == ["6"])
check("pipe nested", evstr("||2||") == ["2"])
check("pipe nested left", evstr("2||3||") == ["6"])
check("pipe add", evstr("|2|+3") == ["5"])
check("pipe sub", evstr("|2|-3") == ["-1"])
check("pipe star", evstr("|2|*3") == ["6"])
check("pipe slash", evstr("|2|/4") == ["0.5"])
check("pipe pow right", evstr("|2|^3") == ["8"])
check("pipe pow left", evstr("2^|3|") == ["8"])
check("pipe neg", evstr("-|2|") == ["-2"])
check("pipe pow neg", evstr("|2|^-1") == ["0.5"])
check("pipe pair mult", evstr("|x||y|", {"x": [ComplexNumber([3, 4])], "y": [ComplexNumber([0, 7])]}) == ["35"])
check("pipe pair sub", evstr("|x|-|y|", {"x": [ComplexNumber([3, 4])], "y": [ComplexNumber([0, 7])]}) == ["-2"])
check("pipe dedup", evstr("|sqrt(4)|") == ["2"])
check("pipe of i", evstr("|i|") == ["1"])

e = parseErr("|2")
check("err pipe unclosed", e is not None and "Expected '|'" in e.message)
e = parseErr("|")
check("err pipe empty", e is not None)
e = parseErr("2|")
check("err pipe dangling", e is not None and "Unexpected" in e.message)
e = parseErr("|2|3|")
check("err pipe unbalanced", e is not None)

# ---------------- Function aliases ----------------
for alias in ["abs", "mag", "mod", "norm", "len", "size"]:
    check(f"alias {alias}", evstr(f"{alias}(3+4i)") == ["5"])
check("alias phase", evstr("phase(i)") == [str(ComplexNumber([math.pi / 2, 0.0]))])

print(f"\n{PASSED} passed, {len(FAILED)} failed")
if(FAILED):
    sys.exit(1)

print("ALL TESTS PASSED")
