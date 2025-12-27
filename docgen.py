#!/usr/bin/env python
# Generates documentation from a Markdown file

from argparse import ArgumentParser, Namespace
from enum import Enum
import re


class DocGenState(Enum):
    NONE = 0
    INSIDE_UNORDERED_LIST = 1
    INSIDE_ORDERED_LIST = 2
    INSIDE_FENCED_CODE_BLOCK = 3
    INSIDE_INDENTED_CODE_BLOCK = 4
    INSIDE_BLOCKQUOTE = 5
    INSIDE_PARAGRAPH = 6


class DocGen:
    TEMPLATE_START = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Docs</title>

  <link href="css/docs.css" rel="stylesheet>
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
        self.depth: int = 0

        self.footnotes: dict[str, tuple[int, str]] = {}
        self.footnote_num: int = 1

        self.state: DocGenState = DocGenState.NONE

    def generate(self) -> None:
        """Generates the documentation"""
        print("Starting generation...")

        self.content: str = ""
        self.lines: list[str] = self.read_lines()
        self.ids: dict[str, str] = self.load_ids()
        print(self.ids)
        for line in self.lines:
            if self.state == DocGenState.INSIDE_FENCED_CODE_BLOCK:
                if line.startswith("```"):
                    self.parse_fenced_code_block(line)
                else:
                    self.emit(line)
                continue

            if not line or re.match(r"^\[(.*)\]: (.*)$", line):
                self.change_state(DocGenState.NONE)
                continue

            if line == "---" or line == "___" or line == "***":
                self.parse_horizontal_rule()
                continue

            if line.startswith("# ") or line.startswith("##"):
                self.parse_header(line)
                continue

            if line.startswith("> "):
                self.parse_blockquote(line)
                continue

            if m := re.match(r"^(\s*)[-+*] (.*)$", line):
                self.parse_unordered_list(m)
                continue

            if m := re.match(r"^(\d+)\. (.*)$", line):
                self.parse_ordered_list(m)
                continue

            if line.startswith("```"):
                self.parse_fenced_code_block(line)
                continue

            if line.startswith("    "):
                self.parse_indented_code_block(line)
                continue

            self.parse_paragraph(line)

        print("Saving...")
        self.save_to_outfile()

        print("Done!")

    def load_ids(self) -> dict[str, str]:
        ids: dict[str, str] = {}
        for i in range(len(self.lines)):
            line: str = self.lines[i]

            self.lines[i] = re.sub(r"\\<", "&lt;", self.lines[i])
            self.lines[i] = re.sub(r"\\>", "&gt;", self.lines[i])
            if m := re.match(r"^\[(.*)\]: (.*)$", line):
                id: str = m.group(1).strip()
                link: str = m.group(2).strip()

                if id[0] == "^":
                    self.footnotes[id] = (-1, link)
                else:
                    ids[id] = link

        return ids

    def read_lines(self) -> list[str]:
        """Reads the file into lines"""
        with open(self.infile) as f:
            lines: list[str] = []
            for line in f.readlines():
                lines.append(line.rstrip().replace("\t", "  "))

            return lines

    def parse_horizontal_rule(self) -> None:
        self.emit("<hr/>")

    def parse_header(self, line: str) -> None:
        """Parses a header (<hx></hx>)"""
        heading_level: int = 0
        while line[heading_level] == "#":
            heading_level += 1

        if heading_level > 6:
            self.parse_paragraph(line)
            return

        heading_content: str = line[heading_level:].strip()
        heading_content = self.parse_inline_text(heading_content)

        numbering: str = self.get_heading_numbering(heading_level)
        self.add_to_toc(numbering)

        heading: str = f"{numbering} {heading_content}"

        html: str = f"<h{heading_level}>{heading}</h{heading_level}>"
        self.emit(html)

        self.print_status(f"H{heading_level}: {heading_content}")

    def parse_blockquote(self, line: str) -> None:
        """Parses a block quote (<blockquote></blockquote>)"""
        self.change_state(DocGenState.INSIDE_BLOCKQUOTE)

        html: str = self.parse_inline_text(line[1:].strip())
        self.emit(html)

    def get_heading_numbering(self, heading_level: int) -> str:
        """Returns the heading numbers"""
        if heading_level < 6:
            self.heading_levels[heading_level] = 0

        self.heading_levels[heading_level - 1] += 1

        numbering: str = ""
        for i in range(heading_level):
            numbering += f"{self.heading_levels[i]}."

        return numbering

    def parse_unordered_list(self, m: re.Match) -> None:
        """Parses an unordered list (<ul></ul>)"""
        self.change_state(DocGenState.INSIDE_UNORDERED_LIST)

        # depth: int = len(m.group(1))
        item: str = self.parse_inline_text(m.group(2))
        self.emit(f"<li>{item}</li>")

    def parse_ordered_list(self, m: re.Match) -> None:
        """Parses an ordered list (<ol></ol>)"""
        self.ol_offset = int(m.group(1))
        self.change_state(DocGenState.INSIDE_ORDERED_LIST)

        item: str = self.parse_inline_text(m.group(2))
        self.emit(f"<li>{item}</li>")

    def parse_fenced_code_block(self, line: str) -> None:
        """Parses a fenced code block (<pre><code></code></pre>)"""
        if self.state == DocGenState.INSIDE_FENCED_CODE_BLOCK:
            self.change_state(DocGenState.NONE)
            return

        self.change_state(DocGenState.INSIDE_FENCED_CODE_BLOCK)
        if line == "```":
            self.emit("<code>")
        else:
            extension: str = line[3:]
            self.emit(f'<code class="language-{extension}">')

    def parse_indented_code_block(self, line: str) -> None:
        """Parses an indented code block (<pre><code></code></pre>)"""
        self.change_state(DocGenState.INSIDE_INDENTED_CODE_BLOCK)
        self.emit(line.strip())

    def parse_paragraph(self, line: str) -> None:
        """Parses a paragraph (<p></p>)"""
        if self.state == DocGenState.NONE:
            self.change_state(DocGenState.INSIDE_PARAGRAPH)

        html: str = self.parse_inline_text(line)
        self.emit(html)

    def parse_inline_text(self, text: str) -> str:
        """Parses inline text (<b></b>, <i></i>, etc.)"""
        if self.state == DocGenState.INSIDE_FENCED_CODE_BLOCK:
            return text

        self.stack: list[str] = [""]
        self.inside_code: bool = False

        text += " "
        html: str = ""

        text = re.sub(r"\[(@.*?)\]", self.replace_code_inlining, text)
        text = re.sub(r"\[(\^.+?)\]", self.replace_footnotes, text)
        text = re.sub(r"!\[(.*?)\]\((.*?)\)", self.replace_images, text)
        text = re.sub(r"!\[(.*?)\]\[(.*?)\]", self.replace_images_with_id, text)
        text = re.sub(r"\[(.*?)\]\((.*?)\)", self.replace_links, text)

        i: int = 0
        while i < len(text) - 1:
            char: str = text[i]
            if char == "`":
                html += self.get_code_tag("`")
            elif not self.inside_code:
                if char == "*":
                    if text[i + 1] == "*":
                        i += 1
                        html += self.get_bold_tag("**")
                    else:
                        html += self.get_italics_tag("*")
                elif char == "_":
                    if text[i + 1] == "_":
                        i += 1
                        html += self.get_bold_tag("__")
                    else:
                        html += self.get_italics_tag("_")
                elif char == "~":
                    if text[i + 1] == "~":
                        i += 1
                        html += self.get_strikethrough_tag("~~")
                    else:
                        html += self.get_subscript_tag("~")
                elif char == "^":
                    html += self.get_superscript_tag("^")
                elif char == "`":
                    html += self.get_code_tag("`")
                elif char == "+" and text[i + 1] == "+":
                    html += self.get_inserted_tag("++")
                elif char == "=" and text[i + 1] == "=":
                    html += self.get_marked_tag("==")
                else:
                    html += char
            else:
                html += char

            i += 1

        return html

    def replace_code_inlining(self, m: re.Match) -> str:
        id: str = m.group(1)
        return f"{id}"

    def replace_footnotes(self, m: re.Match) -> str:
        id: str = m.group(1)
        num, definition = self.footnotes[id]
        if num == -1:
            num = self.footnote_num
            self.footnote_num += 1
            self.footnotes[id] = (num, definition)

        return f'<sup><a href="#fn{num}">[{num}]</a></sup>'

    def replace_images(self, m: re.Match) -> str:
        alt: str = m.group(1)
        link: str = m.group(2)
        return f'<img src="{link}" alt="{alt}" />'

    def replace_images_with_id(self, m: re.Match) -> str:
        alt: str = m.group(1)

        id: str = m.group(2)
        link: str = self.ids[id]

        return f'<img src="{link}" alt="{alt}" />'

    def replace_links(self, m: re.Match) -> str:
        name: str = m.group(1)

        link: str = m.group(2)
        if link in self.ids:
            link = self.ids[link]

        return f'<a href="{link}">{name}</a>'

    def get_bold_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</b>"

        self.stack.append(tag)
        return "<b>"

    def get_italics_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</i>"

        self.stack.append(tag)
        return "<i>"

    def get_strikethrough_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</s>"

        self.stack.append(tag)
        return "<s>"

    def get_subscript_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</sub>"

        self.stack.append(tag)
        return "<sub>"

    def get_superscript_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</sup>"

        self.stack.append(tag)
        return "<sup>"

    def get_code_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.inside_code = False
            self.stack.pop()
            return "</code>"

        self.inside_code = True
        self.stack.append(tag)
        return "<code>"

    def get_inserted_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</ins>"

        self.stack.append(tag)
        return "<ins>"

    def get_marked_tag(self, tag: str) -> str:
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return "</mark>"

        self.stack.append(tag)
        return "<mark>"

    def add_to_toc(self, numbering: str) -> None:
        numbering = "h" + numbering.replace(".", "-")
        self.toc.append(numbering)

    def emit(self, html: str) -> None:
        """Emits HTML to content buffer"""
        self.content += f"  {html}\n"

    def save_to_outfile(self) -> None:
        """Saves the converted HTML to the output file"""
        with open(self.outfile, "w") as f:
            self.write_template_start(f)
            f.write(self.content)
            f.write(self.TEMPLATE_END)

    def write_template_start(self, f) -> None:
        f.write(self.TEMPLATE_START)
        with open("lib/highlight.min.js") as js:
            f.write("<script>\n")
            f.write(js.read())
            f.write("hljs.highlightAll();\n")
            f.write("</script>\n")

        with open("lib/highlight.min.css") as css:
            f.write("<style>\n")
            f.write(css.read())
            f.write("</style>\n")

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
            case (
                DocGenState.INSIDE_FENCED_CODE_BLOCK
                | DocGenState.INSIDE_INDENTED_CODE_BLOCK
            ):
                self.emit("</code></pre>")
            case DocGenState.INSIDE_BLOCKQUOTE:
                self.emit("</p></blockquote>")
            case DocGenState.INSIDE_PARAGRAPH:
                self.emit("</p>")

        self.state = to
        match self.state:
            case DocGenState.INSIDE_UNORDERED_LIST:
                self.emit("<ul>")
            case DocGenState.INSIDE_ORDERED_LIST:
                self.emit(f'<ol start="{self.ol_offset}">')
            case (
                DocGenState.INSIDE_FENCED_CODE_BLOCK
                | DocGenState.INSIDE_INDENTED_CODE_BLOCK
            ):
                self.emit("<pre>")
            case DocGenState.INSIDE_BLOCKQUOTE:
                self.emit("<blockquote><p>")
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
