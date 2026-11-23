// Builds the class diagram (expression pipeline) and writes a Graphviz .dot file
// using the user's diagram_generator module.
const path = require("path");
const { generateDotFile } = require("/mnt/data0/win/desktop/Projekty/Projekty/Templates/FIT/AIS/projects/01/diagram_generator.js");

const P = "public", Pr = "private";
const f = (name, type, access = P) => ({ name, type, access });
const m = (name, type, access, parameters = []) => ({ name, type, access, parameters, genericParams: [] });

const enumVals = (vals) => vals.map((v) => ({ name: v, type: "", access: P }));

const classes = [
    // ---- Tokenization ----
    {
        name: "TokenType", isAbstract: false, isEnum: true, isInterface: false, genericParams: [],
        fields: enumVals(["NUMBER", "IDENT", "PLUS", "MINUS", "STAR", "DSTAR", "SLASH", "CARET", "LPAR", "RPAR", "COMMA", "PIPE", "END"]),
        methods: [], inheritance: [],
    },
    {
        name: "ASTOperator", isAbstract: false, isEnum: true, isInterface: false, genericParams: [],
        fields: enumVals(["ADD", "SUB", "MULT", "DIV", "POW", "POS", "NEG"]),
        methods: [], inheritance: [],
    },
    {
        name: "Token", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("type", "TokenType"), f("text", "str"), f("position", "int"), f("end", "int"), f("source", "str"), f("preview", "str")],
        methods: [m("describe", "str", P)],
        inheritance: [],
        refs: [{ target: "TokenType", label: "type" }],
    },
    {
        name: "Tokenizer", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("source", "str"), f("_tokens", "List[Token]", Pr), f("_index", "int", Pr), f("_cursor", "int", Pr), f("_exhausted", "bool", Pr)],
        methods: [
            m("peekToken", "Token", P, [{ name: "offset", type: "int" }]),
            m("nextToken", "Token", P),
            m("isAtEnd", "bool", P),
            m("save", "state", P),
            m("restore", "None", P, [{ name: "state", type: "state" }]),
            m("_tokenizeNext", "Token", Pr),
        ],
        inheritance: [],
        refs: [{ target: "Token", label: "tokens" }],
        uses: ["TokenizeError"],
    },

    // ---- AST (data structure) ----
    {
        name: "ASTNode", isAbstract: true, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("token", "Token"), f("position", "int")],
        methods: [], inheritance: [],
        refs: [{ target: "Token", label: "token" }],
    },
    {
        name: "ExpressionASTNode", isAbstract: true, isEnum: false, isInterface: false, genericParams: [],
        fields: [], methods: [],
        inheritance: [{ baseClass: "ASTNode", bindings: [] }],
    },
    {
        name: "LiteralASTNode", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("value", "float")], methods: [],
        inheritance: [{ baseClass: "ASTNode", bindings: [] }],
    },
    {
        name: "IdentifierASTNode", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("name", "str")], methods: [],
        inheritance: [{ baseClass: "ASTNode", bindings: [] }],
    },
    {
        name: "BinaryExpressionASTNode", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("operator", "ASTOperator"), f("left", "ASTNode"), f("right", "ASTNode")], methods: [],
        inheritance: [{ baseClass: "ExpressionASTNode", bindings: [] }],
        refs: [{ target: "ASTOperator", label: "operator" }],
    },
    {
        name: "UnaryExpressionASTNode", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("operator", "ASTOperator"), f("operand", "ASTNode")], methods: [],
        inheritance: [{ baseClass: "ExpressionASTNode", bindings: [] }],
        refs: [{ target: "ASTOperator", label: "operator" }],
    },
    {
        name: "CallExpressionASTNode", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("name", "str"), f("arguments", "List[ExpressionASTNode]")], methods: [],
        inheritance: [{ baseClass: "ExpressionASTNode", bindings: [] }],
    },

    // ---- Parsing (recursive descent) ----
    {
        name: "Parser", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("t", "Tokenizer")],
        methods: [
            m("parse", "ASTNode", P),
            m("parseExpression", "ExpressionASTNode", P),
            m("parseTerm", "ExpressionASTNode", P),
            m("parseUnary", "ExpressionASTNode", P),
            m("parsePower", "ExpressionASTNode", P),
            m("parsePrimary", "ExpressionASTNode", P),
            m("parseCall", "CallExpressionASTNode", P, [{ name: "ident", type: "Token" }]),
            m("parseAbs", "CallExpressionASTNode", P, [{ name: "lpipe", type: "Token" }]),
            m("parseParen", "ExpressionASTNode", P),
        ],
        inheritance: [],
        refs: [
            { target: "Tokenizer", label: "tokenizer" },
            { target: "ASTNode", label: "builds", style: "dashed" },
        ],
        uses: ["ParseError"],
    },

    // ---- Interpretation ----
    {
        name: "Interpreter", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("context", "Dict[str, List[ComplexNumber]]"), f("maxValues", "int"), f("functions", "Dict[str, ComplexFunction]")],
        methods: [
            m("interpret", "List[ComplexNumber]", P, [{ name: "node", type: "ASTNode" }]),
            m("_eval", "List[ComplexNumber]", Pr, [{ name: "node", type: "ASTNode" }]),
            m("_evalCall", "List[ComplexNumber]", Pr, [{ name: "node", type: "CallExpressionASTNode" }]),
            m("_safe", "ComplexNumber", Pr, [{ name: "fn", type: "Callable" }, { name: "node", type: "ASTNode" }]),
        ],
        inheritance: [],
        refs: [
            { target: "ASTNode", label: "evaluates", style: "dashed" },
            { target: "ComplexNumber", label: "values" },
            { target: "ComplexFunction", label: "functions" },
        ],
        uses: ["InterpretError"],
    },
    {
        name: "ComplexFunction", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("name", "str"), f("arity", "int | (int, int)"), f("fn", "Callable[[List[ComplexNumber], int], ComplexNumber]"), f("multi", "bool"), f("period", "int?")],
        methods: [m("arityError", "str?", P, [{ name: "count", type: "int" }])],
        inheritance: [],
        refs: [{ target: "ComplexNumber", label: "fn" }],
    },
    {
        name: "ComplexNumber", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("r", "float"), f("i", "float"), f("sign", "str"), f("distance", "float"), f("angle", "float")],
        methods: [
            m("add", "ComplexNumber", P, [{ name: "x", type: "ComplexNumber" }]),
            m("sub", "ComplexNumber", P, [{ name: "x", type: "ComplexNumber" }]),
            m("mult", "ComplexNumber", P, [{ name: "x", type: "ComplexNumber" }]),
            m("div", "ComplexNumber", P, [{ name: "x", type: "ComplexNumber" }]),
            m("neg", "ComplexNumber", P),
            m("conj", "ComplexNumber", P),
            m("sqrt", "ComplexNumber", P),
            m("abs", "ComplexNumber", P),
            m("arg", "ComplexNumber", P),
            m("real", "ComplexNumber", P),
            m("imag", "ComplexNumber", P),
        ],
        inheritance: [],
    },

    // ---- Errors ----
    {
        name: "ExpressionError", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [f("message", "str"), f("position", "int?"), f("source", "str?")],
        methods: [m("__str__", "str", P)],
        inheritance: [],
    },
    {
        name: "TokenizeError", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [], methods: [], inheritance: [{ baseClass: "ExpressionError", bindings: [] }],
    },
    {
        name: "ParseError", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [], methods: [], inheritance: [{ baseClass: "ExpressionError", bindings: [] }],
    },
    {
        name: "InterpretError", isAbstract: false, isEnum: false, isInterface: false, genericParams: [],
        fields: [], methods: [], inheritance: [{ baseClass: "ExpressionError", bindings: [] }],
    },
];

const out = path.join(__dirname, "..", "docs", "img", "class_diagram.dot");
generateDotFile(classes, out, { hideEmpty: true });
console.log("wrote", out);
