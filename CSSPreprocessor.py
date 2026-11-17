# function processCSS(css) {
#     const variables = {};
#     return css
#         .replace(/\/\*[\S\s]*?\*\//g, "")
#         .replace(/(?:@(\w*)\s?=\s?(.*);|@(\w*))/g, (match, varDef, value, varRef) => varDef ? ((variables[varDef] = value), "") : variables[varRef]);
# }

import re
from typing import Any, Dict, Optional, Tuple, Type


class CSS():
    def __init__(self, file: str, content: str, variables: Dict[str, str]) -> None:
        self.file: str = file
        self.content: str = content
        self.variables: Dict[str, str] = variables

    def var(self, name: str, type: Optional[Type[Any]] = None) -> Any:
        if(not name in self.variables):
            raise ReferenceError(f"Variable '{name}' cannot be found in {CSS._getFilename(self.file)}")

        value = self.variables[name]

        return type(value) if type else value

    @staticmethod
    def process(file: str) -> "CSS":
        css = open(file, "r").read()
        variables: Dict[str, str] = {}

        def variableProcessor(m: re.Match) -> str:
            match: str = m[0]
            varDef: Optional[str] = m[1]
            value: Optional[str] = m[2]
            varRef: Optional[str] = m[3]

            if(varDef):
                variables[varDef] = value
            elif(not varRef in variables):
                line = CSS._getLine(css, m.start(0))
                filename = CSS._getFilename(file)
                err = f"Undeclared variable '{match}' at {filename}:{line[0]}:{line[1]}:\n{line[2]}\n{' ' * line[1]}^{'~' * (m.end(0) - m.start(0) - 1)}"

                raise ReferenceError(err)

            return "" if varDef else variables[varRef]

        css = re.sub(r"\/\*[\S\s]*?\*\/", "", css)
        css = re.sub(r"\t", ' ' * 4, css)
        css = re.sub(r'(?:@(\w*)\s*=\s*(.*);|@(\w*))', variableProcessor, css)

        return CSS(file, css, variables)

    @staticmethod
    def _getFilename(path: str) -> str:
        return re.search(r"[^\/\\]+$", path)[0]

    @staticmethod
    def _getLine(text: str, index: int) -> Tuple[int, int, str]:
        ch = ""
        i = 0

        lineBuffer = ""
        lineNumber = 1
        indexPos = 0

        while len(text):
            ch = text[i]

            if(i == index):
                indexPos = len(lineBuffer) - 1

            if(ch == '\n' or ch == '\r'):
                if(i >= index):
                    return (lineNumber, indexPos, lineBuffer)
                lineBuffer = ""
                lineNumber += 1
            else:
                lineBuffer += ch

            i += 1
