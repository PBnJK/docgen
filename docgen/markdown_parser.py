#!/usr/bin/env python
# Parses DocGen Markdown

from enum import Enum
import re


class TokenType(Enum):
    TEXT = 0
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6
    ERROR = 255


class Token:
    def __init__(self, tktype: TokenType, value: str) -> None:
        self.type = tktype
        self.value = value


class MarkdownParserState(Enum):
    NONE = 0
    INSIDE_UNORDERED_LIST = 1
    INSIDE_ORDERED_LIST = 2
    INSIDE_FENCED_CODE_BLOCK = 3
    INSIDE_INDENTED_CODE_BLOCK = 4
    INSIDE_BLOCKQUOTE = 5
    INSIDE_PARAGRAPH = 6


class MarkdownParser:
    def __init__(self, source: str, verbose: bool) -> None:
        self.source: str = source
        self.verbose: bool = verbose

        self.toc: list[str] = []
        self.heading_levels: list[int] = [0, 0, 0, 0, 0, 0]
        self.depth: int = 0

        self.footnotes: dict[str, tuple[int, str]] = {}
        self.footnote_num: int = 1

        self.state: MarkdownParserState = MarkdownParserState.NONE

    def generate(self) -> None:
        """Generates the documentation"""
        print("Starting generation...")

        self.content: str = ""
        self.tokens: list[Token] = []

        self.lines: list[str] = self.read_lines()
        self.ids: dict[str, str] = self.load_ids()

        for line in self.lines:
            if self.state == MarkdownParserState.INSIDE_FENCED_CODE_BLOCK:
                if line.startswith("```"):
                    self.parse_fenced_code_block(line)
                else:
                    self.emit_html(line)
                continue

            if not line or re.match(r"^\[(.*)\]: (.*)$", line):
                self.change_state(MarkdownParserState.NONE)
                continue

            if line == "---" or line == "___" or line == "***":
                self.parse_horizontal_rule()
                continue

            if line.startswith("# ") or line.startswith("##"):
                self.parse_heading(line)
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
        lines: list[str] = []
        for line in self.source.split():
            lines.append(line.rstrip().replace("\t", "  "))

        return lines

    def parse_horizontal_rule(self) -> None:
        """Parses a horizontal rule (<hr />)"""
        self.emit_html("<hr />")

    def parse_heading(self, line: str) -> None:
        """Parses a heading (<hx></hx>)"""
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

        html: str = (
            f"<h{heading_level}>{numbering} {heading_content}</h{heading_level}>"
        )
        self.emit_html(html)

        self.print_status(f"H{heading_level}: {heading_content}")

    def parse_blockquote(self, line: str) -> None:
        """Parses a block quote (<blockquote></blockquote>)"""
        self.change_state(MarkdownParserState.INSIDE_BLOCKQUOTE)

        html: str = self.parse_inline_text(line[1:].strip())
        self.emit_html(html)

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
        self.change_state(MarkdownParserState.INSIDE_UNORDERED_LIST)

        # depth: int = len(m.group(1))
        item: str = self.parse_inline_text(m.group(2))
        self.emit_html(f"<li>{item}</li>")

    def parse_ordered_list(self, m: re.Match) -> None:
        """Parses an ordered list (<ol></ol>)"""
        self.ol_offset = int(m.group(1))
        self.change_state(MarkdownParserState.INSIDE_ORDERED_LIST)

        item: str = self.parse_inline_text(m.group(2))
        self.emit_html(f"<li>{item}</li>")

    def parse_fenced_code_block(self, line: str) -> None:
        """Parses a fenced code block (<pre><code></code></pre>)"""
        if self.state == MarkdownParserState.INSIDE_FENCED_CODE_BLOCK:
            self.change_state(MarkdownParserState.NONE)
            return

        self.change_state(MarkdownParserState.INSIDE_FENCED_CODE_BLOCK)
        if line == "```":
            self.emit_html("<code>")
        else:
            extension: str = line[3:]
            self.emit_html(f'<code class="language-{extension}">')

    def parse_indented_code_block(self, line: str) -> None:
        """Parses an indented code block (<pre><code></code></pre>)"""
        self.change_state(MarkdownParserState.INSIDE_INDENTED_CODE_BLOCK)
        self.emit_html(line.strip())

    def parse_paragraph(self, line: str) -> None:
        """Parses a paragraph (<p></p>)"""
        if self.state == MarkdownParserState.NONE:
            self.change_state(MarkdownParserState.INSIDE_PARAGRAPH)

        html: str = self.parse_inline_text(line)
        self.emit_html(html)

    def parse_inline_text(self, text: str) -> str:
        """Parses inline text (<b></b>, <i></i>, etc.)"""
        if self.state == MarkdownParserState.INSIDE_FENCED_CODE_BLOCK:
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
        """ "Parses project code references ([@function] or [@file])"""
        id: str = m.group(1)
        return f"{id}"

    def replace_footnotes(self, m: re.Match) -> str:
        """ "Parses footnotes ([^footnote])"""
        id: str = m.group(1)
        num, definition = self.footnotes[id]
        if num == -1:
            num = self.footnote_num
            self.footnote_num += 1
            self.footnotes[id] = (num, definition)

        return f'<sup><a href="#fn{num}">[{num}]</a></sup>'

    def replace_images(self, m: re.Match) -> str:
        """ "Parses images ([!alt](link))"""
        alt: str = m.group(1)
        link: str = m.group(2)
        return f'<img src="{link}" alt="{alt}" />'

    def replace_images_with_id(self, m: re.Match) -> str:
        """ "Parses images ([!alt][id])"""
        alt: str = m.group(1)

        id: str = m.group(2)
        link: str = self.ids[id]

        return f'<img src="{link}" alt="{alt}" />'

    def replace_links(self, m: re.Match) -> str:
        """ "Parses links ([name](link))"""
        name: str = m.group(1)

        link: str = m.group(2)
        if link in self.ids:
            link = self.ids[link]

        return f'<a href="{link}">{name}</a>'

    def get_bold_tag(self, tag: str) -> str:
        """Starts or stops bold text"""
        return self.get_emphasis_tag(tag, "<b>", "</b>")

    def get_italics_tag(self, tag: str) -> str:
        """Starts or stops italics text"""
        return self.get_emphasis_tag(tag, "<i>", "</i>")

    def get_strikethrough_tag(self, tag: str) -> str:
        """Starts or stops strikethrough text"""
        return self.get_emphasis_tag(tag, "<s>", "</s>")

    def get_subscript_tag(self, tag: str) -> str:
        """Starts or stops subscript text"""
        return self.get_emphasis_tag(tag, "<sub>", "</sub>")

    def get_superscript_tag(self, tag: str) -> str:
        """Starts or stops superscript text"""
        return self.get_emphasis_tag(tag, "<sup>", "</sup>")

    def get_inserted_tag(self, tag: str) -> str:
        """Starts or stops inserted text"""
        return self.get_emphasis_tag(tag, "<ins>", "</ins>")

    def get_marked_tag(self, tag: str) -> str:
        """Starts or stops marked text"""
        return self.get_emphasis_tag(tag, "<mark>", "</mark>")

    def get_code_tag(self, tag: str) -> str:
        """Starts or stops code text"""
        if self.stack[len(self.stack) - 1] == tag:
            self.inside_code = False
            self.stack.pop()
            return "</code>"

        self.inside_code = True
        self.stack.append(tag)
        return "<code>"

    def get_emphasis_tag(self, tag: str, open_element: str, close_element: str) -> str:
        """Returns the appropriate element for starting or stopping text emphasis"""
        if self.stack[len(self.stack) - 1] == tag:
            self.stack.pop()
            return close_element

        self.stack.append(tag)
        return open_element

    def add_to_toc(self, numbering: str) -> None:
        """Adds to the table of contents"""
        numbering = "h" + numbering.replace(".", "-")
        self.toc.append(numbering)

    def emit(self, token: Token) -> None:
        """Emits a token to content buffer"""
        self.tokens.append(token)

    def emit_html(self, html: str) -> None:
        """Emits HTML to content buffer"""
        self.content += f"  {html}\n"

    def print_status(self, msg: str) -> None:
        """Prints a status message, if verbose output is on"""
        if self.verbose:
            print(msg)

    def change_state(self, to: MarkdownParserState) -> None:
        """Changes the state of the parser if needed, opening and closing tags as appropriate"""
        if self.state == to:
            return

        match self.state:
            case MarkdownParserState.INSIDE_UNORDERED_LIST:
                self.emit_html("</ul>")
            case MarkdownParserState.INSIDE_ORDERED_LIST:
                self.emit_html("</ol>")
            case (
                MarkdownParserState.INSIDE_FENCED_CODE_BLOCK
                | MarkdownParserState.INSIDE_INDENTED_CODE_BLOCK
            ):
                self.emit_html("</code></pre>")
            case MarkdownParserState.INSIDE_BLOCKQUOTE:
                self.emit_html("</p></blockquote>")
            case MarkdownParserState.INSIDE_PARAGRAPH:
                self.emit_html("</p>")

        self.state = to
        match self.state:
            case MarkdownParserState.INSIDE_UNORDERED_LIST:
                self.emit_html("<ul>")
            case MarkdownParserState.INSIDE_ORDERED_LIST:
                self.emit_html(f'<ol start="{self.ol_offset}">')
            case (
                MarkdownParserState.INSIDE_FENCED_CODE_BLOCK
                | MarkdownParserState.INSIDE_INDENTED_CODE_BLOCK
            ):
                self.emit_html("<pre>")
            case MarkdownParserState.INSIDE_BLOCKQUOTE:
                self.emit_html("<blockquote><p>")
            case MarkdownParserState.INSIDE_PARAGRAPH:
                self.emit_html("<p>")
