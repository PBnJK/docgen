#!/usr/bin/env python
# Generates documentation for a project

from argparse import ArgumentParser, Namespace
from contextlib import chdir
from pathlib import Path


import tomllib


class DocGen:
    TEMPLATE_START = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Docs</title>
</head>
<body>
"""

    TEMPLATE_END: str = """\
</body>
</html>
"""

    def __init__(self, basedir: Path, outdir: Path, verbose: bool) -> None:
        self.base_directory: Path = basedir
        self.output_directory: Path = outdir
        self.verbose: bool = verbose

        self.load_config()

    def load_config(self) -> None:
        """Loads configuration options from the .toml file, if present"""
        with chdir(self.base_directory):
            try:
                with open("docgen.toml", "rb") as f:
                    configs: dict = tomllib.load(f)
                    self.load_config_from_dict(configs)
            except FileNotFoundError:
                self.load_config_from_dict({})

    def load_config_from_dict(self, config: dict) -> None:
        """Loads configuration options from a dictionary"""
        self.project_name: str = config.get("name", "Unnamed Project")

        # Both *author* and *authors* are valid keys for author names
        project_authors = config.get("author")
        if not project_authors:
            project_authors = config.get("authors", ["Unknown Author"])

        # Author names can either be a string or a list of strings
        if isinstance(project_authors, list):
            self.project_authors: list[str] = [
                str(author) for author in project_authors
            ]
        else:
            self.project_authors: list[str] = [str(project_authors)]

        self.project_version: str = config.get("version", "Unknown Version")

    def generate(self) -> None:
        """Generates the project documentation"""
        pass

    def print_status(self, msg: str) -> None:
        """Wrapper to print status messages"""
        if self.verbose:
            print(msg)


def main() -> None:
    """Entry-point of the program"""
    args: Namespace = parse_arguments()

    docgen: DocGen = DocGen(args.directory, args.output, args.verbose)
    docgen.generate()


def parse_arguments() -> Namespace:
    """Parses the arguments from the command line"""
    parser: ArgumentParser = ArgumentParser(
        prog="docgen",
        description="generates documentation from a Markdown file",
        epilog="pedrob",
    )

    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=".",
        help="path to the directory containing your project",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=".",
        help="path to which files will be outputted",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="prints extra information",
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
