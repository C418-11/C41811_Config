"""转换 ``ruff`` 日志为 HTML"""

from subprocess import PIPE
from subprocess import STDOUT
from subprocess import run

from ansi2html import Ansi2HTMLConverter

ENCODING = "utf-8"
OUTPUT_FILE = "./docs/_static/_ruff.html"


def run_commands(commands: list[list[str]]) -> str:
    # noinspection PyArgumentEqualDefault
    return "\n".join(run(cmd, check=False, stdout=PIPE, stderr=STDOUT, encoding=ENCODING).stdout for cmd in commands)  # noqa: S603


def write_ansi2html(text: str, out: str) -> None:
    conv = Ansi2HTMLConverter()
    with open(out, "w", encoding=ENCODING) as f:
        f.write(conv.convert(text))


def main():
    write_ansi2html(
        run_commands([["ruff", "check", "--exit-zero", "--no-fix"], ["ruff", "format", "--check"]]), OUTPUT_FILE
    )


if __name__ == "__main__":
    main()
