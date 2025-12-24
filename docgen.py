#!/usr/bin/env python
# Generates documentation from a Markdown file

from argparse import ArgumentParser, Namespace
from enum import Enum


class DocGenState(Enum):
    NONE = 0
    INSIDE_UNORDERED_LIST = 1
    INSIDE_ORDERED_LIST = 2
    INSIDE_CODE_BLOCK = 3
    INSIDE_PARAGRAPH = 4


class DocGen:
    TEMPLATE_START = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GameLISP Docs</title>
  <link href="css/style.css" rel="stylesheet" />
</head>
<body>
"""

    TEMPLATE_END: str = """\
</body>
</html>
"""

    def __init__(self, infile: str, outfile: str, verbose: bool) -> None:
        self.infile: str = infile
        self.outfile: str = outfile
        self.verbose: bool = verbose

        self.toc: list[str] = []
        self.heading_levels: list[int] = [0, 0, 0, 0, 0, 0]

        self.state: DocGenState = DocGenState.NONE

    def generate(self) -> None:
        """Generates the documentation"""
        print("Starting generation...")

        self.content: str = ""
        self.lines: list[str] = self.read_lines()
        for line in self.lines:
            if not line:
                self.change_state(DocGenState.NONE)
                continue

            char: str = line[0]
            if char == "#":
                self.parse_header(line)
                continue

            if char == "-" or char == "+":
                self.parse_unordered_list(line)
                continue

            if line.startswith("1."):
                self.parse_ordered_list(line)

            if line.startswith("```"):
                self.parse_code_block(line)
                continue

            self.parse_paragraph(line)

        print("Saving...")
        self.save_to_outfile()

        print("Done!")

    def read_lines(self) -> list[str]:
        """Reads the file into lines"""
        with open(self.infile) as f:
            return [line.strip() for line in f.readlines()]

    def parse_header(self, line: str) -> None:
        """Parses a Markdown header"""
        heading_level: int = 0
        while line[heading_level] == "#":
            heading_level += 1

        if heading_level > 6:
            raise Exception("heading level exceeded 6")

        heading_content: str = line[heading_level:].strip()
        numbering: str = self.get_heading_numbering(heading_level)
        self.add_to_toc(numbering)

        heading: str = f"{numbering} {heading_content}"

        html: str = f"<h{heading_level}>{heading}</h{heading_level}>"
        self.emit(html)

        self.print_status(f"H{heading_level}: {heading_content}")

    def get_heading_numbering(self, heading_level: int) -> str:
        """Returns the heading"""
        if heading_level < 6:
            self.heading_levels[heading_level] = 0

        self.heading_levels[heading_level - 1] += 1

        numbering: str = ""
        for i in range(heading_level):
            numbering += f"{self.heading_levels[i]}."

        return numbering

    def parse_unordered_list(self, line: str) -> None:
        self.change_state(DocGenState.INSIDE_UNORDERED_LIST)

    def parse_ordered_list(self, line: str) -> None:
        self.change_state(DocGenState.INSIDE_ORDERED_LIST)

    def parse_code_block(self, line: str) -> None:
        self.change_state(DocGenState.INSIDE_CODE_BLOCK)

    def parse_paragraph(self, line: str) -> None:
        if self.state == DocGenState.NONE:
            self.change_state(DocGenState.INSIDE_PARAGRAPH)

    def add_to_toc(self, numbering: str) -> None:
        numbering = "h" + numbering.replace(".", "-")
        self.toc.append(numbering)

    def emit(self, html: str) -> None:
        """Emits HTML to content buffer"""
        self.content += f"  {html}\n"

    def save_to_outfile(self) -> None:
        """Saves the converted HTML to the output file"""
        with open(self.outfile, "w") as f:
            f.write(self.TEMPLATE_START)
            f.write(self.content)
            f.write(self.TEMPLATE_END)

    def print_status(self, msg: str) -> None:
        """Prints a status message, if verbose output is on"""
        if self.verbose:
            print(msg)

    def change_state(self, to: DocGenState) -> None:
        if self.state == to:
            return

        match self.state:
            case DocGenState.INSIDE_UNORDERED_LIST:
                self.emit("</ul>")
            case DocGenState.INSIDE_ORDERED_LIST:
                self.emit("</ol>")
            case DocGenState.INSIDE_CODE_BLOCK:
                self.emit("</code></pre>")
            case DocGenState.INSIDE_PARAGRAPH:
                self.emit("</p>")

        self.state = to
        match self.state:
            case DocGenState.INSIDE_UNORDERED_LIST:
                self.emit("<ul>")
            case DocGenState.INSIDE_ORDERED_LIST:
                self.emit("<ol>")
            case DocGenState.INSIDE_CODE_BLOCK:
                self.emit("<pre>")
            case DocGenState.INSIDE_PARAGRAPH:
                self.emit("<p>")


def main() -> None:
    """Entry-point of the program"""
    args: Namespace = parse_arguments()
    docgen: DocGen = DocGen(args.filename, args.output, args.verbose)
    docgen.generate()


def parse_arguments() -> Namespace:
    """Parses the arguments from the command line"""
    parser: ArgumentParser = ArgumentParser(
        prog="docgen",
        description="generates the documentation for GameLISP from a Markdown file",
        epilog="pedrob",
    )

    parser.add_argument("filename", help="path to a Markdown file")
    parser.add_argument(
        "-o",
        "--output",
        help="path to the output HTML file",
        default="docs.html",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="prints extra information",
        action="store_true",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
