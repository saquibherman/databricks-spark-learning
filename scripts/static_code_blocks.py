"""Replace JS-rendered (Prism) code blocks in Databricks %md-sandbox cells with static HTML.

The Academy lectures write code as <div class="code-block" data-language="python">...</div> and
highlight it with Prism at render time. VS Code's notebook renderer doesn't run scripts, so the code
collapses into one line. This pre-renders it with Pygments (inline styles, Prism "tomorrow" colors)
so it looks the same in VS Code and in Databricks, and drops the now-unused Prism loader scripts.

Usage: python static_code_blocks.py <notebook.ipynb> ...
"""
import html
import json
import re
import sys

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.style import Style
from pygments.token import (Comment, Keyword, Name, Number, Operator, Punctuation, String, Text,
                            Token)


class PrismTomorrow(Style):
    background_color = "#1e1e1e"
    styles = {
        Token: "#cccccc", Text: "#cccccc",
        Comment: "#999999",
        Keyword: "#cc99cd", Keyword.Constant: "#f08d49", Operator.Word: "#cc99cd",
        Name.Builtin: "#e2777a", Name.Function: "#f08d49", Name.Class: "#f8c555",
        Name.Decorator: "#e2777a", Name.Namespace: "#cccccc",
        String: "#7ec699", Number: "#f08d49",
        Operator: "#67cdcc", Punctuation: "#cccccc",
    }


PRE_BASE = ("color:#cccccc;border-radius:8px;padding:16px;margin:16px 0;overflow-x:auto;"
            "font-family:Consolas,Monaco,monospace;font-size:14px;line-height:1.5")
# code-block: lecture snippets; code-block-dark: lab solutions (Copy button dropped, it needs JS)
BACKGROUND = {"code-block": "background:#1e1e1e;", "code-block-dark": "background:#2d2d2d;border:1px solid #444;"}

CODE_BLOCK = re.compile(r'<div class="(code-block(?:-dark)?)" data-language="(\w+)">\n?(.*?)\n?</div>', re.S)
PRISM_ASSETS = re.compile(r'[ \t]*<(?:link|script)[^>]*cdnjs\.cloudflare\.com/ajax/libs/prism/[^>]*>(?:</script>)?[ \t]*\n?')
PRISM_RUNNER = re.compile(r"<script>\s*\(function\(\) \{\s*document\.querySelectorAll\('\.code-block(?:-dark)?'\).*?</script>\n?", re.S)


def render(match: re.Match) -> str:
    kind, lang, raw = match.group(1), match.group(2), match.group(3)
    # Prism used the block's textContent: tags dropped (the course writes empty lines as <br/>), entities decoded
    code = html.unescape(re.sub(r"</?[a-zA-Z][^>]*>", "", raw)).strip("\n")
    fmt = HtmlFormatter(nowrap=True, noclasses=True, style=PrismTomorrow)
    body = highlight(code, get_lexer_by_name(lang), fmt).rstrip("\n")
    # A blank line would end the surrounding Markdown HTML block, so keep empty lines non-blank
    body = "\n".join(line if line.strip() else "<span></span>" for line in body.split("\n"))
    return f'<pre style="{BACKGROUND[kind]}{PRE_BASE}"><code>{body}</code></pre>'


def convert(text: str) -> tuple[str, int]:
    text, n = CODE_BLOCK.subn(render, text)
    if n:
        text = PRISM_ASSETS.sub("", text)
        text = PRISM_RUNNER.sub("", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
    return text, n


def main() -> None:
    for path in sys.argv[1:]:
        nb = json.load(open(path, encoding="utf-8"))
        total = 0
        for cell in nb["cells"]:
            src = "".join(cell["source"])
            new, n = convert(src)
            if n:
                total += n
                cell["source"] = new.splitlines(keepends=True)
        if total:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
            print(f"{total:3} blocks  {path}")


if __name__ == "__main__":
    main()
