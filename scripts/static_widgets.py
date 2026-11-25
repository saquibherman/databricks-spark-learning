"""Replace JavaScript widgets in Databricks %md-sandbox cells with static HTML.

The Academy lectures build their knowledge checks, flip cards and tab panels with inline <script>s.
VS Code's notebook renderer doesn't run scripts, so those cells render empty or half-hidden. This
rewrites them as plain HTML (with <details> for anything you reveal by clicking), which renders the
same in VS Code and Databricks:

- multiple-choice quiz (mcqRoot)   -> every question with options A-D and a "Show answer" fold
- true/false quiz (trueFalseRoot)  -> every statement with a "Show answer" fold
- flip cards (flip-*)              -> cards whose "back" opens in a fold
- Spark UI tabs (sparkui-*)        -> all panels shown one after another

Output has no blank lines or indentation, so Markdown keeps it as a single HTML block.

Usage: python static_widgets.py <notebook.ipynb> ...
"""
import json
import re
import sys

FONT = "font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif"
BOX = f"{FONT};width:100%;margin:10px 0;padding:24px;background:#f5f7fa;border-radius:12px;border:1px solid #e0e0e0;box-sizing:border-box"
CARD = "background:#fff;border-radius:12px;border:2px solid #e0e0e0;padding:18px 24px;margin:20px 0 12px 0"
OPTION = "display:flex;align-items:center;gap:16px;padding:12px 20px;background:#fff;border:2px solid #e0e0e0;border-radius:8px;margin:0 0 8px 0"
LETTER = "width:32px;height:32px;min-width:32px;border:2px solid #e0e0e0;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;color:#333"
SUMMARY = "cursor:pointer;color:#1976d2;font-weight:600;margin:4px 0"
BADGE = "padding:8px 16px;border-radius:20px;font-weight:600;font-size:0.9em;background:#e3f2fd;color:#1976d2"


def header(title: str, subtitle: str, count: int) -> str:
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
            f'<div><div style="font-size:1.4em;font-weight:600;color:#333">{title}</div>'
            f'<div style="font-size:0.95em;color:#666;margin-top:4px">{subtitle}</div></div>'
            f'<span style="{BADGE}">{count} questions</span></div>')


def answer_box(ok: bool, head: str, body: str) -> str:
    bg, border, fg = ("#e8f5e9", "#4caf50", "#2e7d32") if ok else ("#ffebee", "#f44336", "#c62828")
    return (f'<details style="margin:4px 0 8px 0"><summary style="{SUMMARY}">Show answer</summary>'
            f'<div style="margin-top:8px;padding:12px 16px;background:{bg};border:2px solid {border};border-radius:8px">'
            f'<div style="font-weight:700;color:{fg}">{head}</div>'
            f'<div style="color:#333;margin-top:6px;line-height:1.5">{body}</div></div></details>')


def mcq(questions: list) -> str:
    out = [f'<div style="{BOX}">', header("📝 Multiple Choice Quiz", "Knowledge Check", len(questions))]
    for n, q in enumerate(questions, 1):
        out.append(f'<div style="{CARD}"><div style="font-size:0.85em;font-weight:600;color:#1976d2;margin-bottom:6px">'
                   f'Question {n} of {len(questions)}</div><div style="font-size:1.15em;color:#333;line-height:1.6">{q["question"]}</div></div>')
        for o in q["options"]:
            out.append(f'<div style="{OPTION}"><div style="{LETTER}">{o["id"].upper()}</div>'
                       f'<div style="flex:1;color:#333">{o["text"]}</div></div>')
        right = next(o for o in q["options"] if o["id"] == q["correct"])
        out.append(answer_box(True, f'✓ {right["id"].upper()}. {right["text"]}', q["explanation"]))
    out.append("</div>")
    return "\n".join(out)


def true_false(questions: list) -> str:
    out = [f'<div style="{BOX}">', header("⚡ True or False: Rapid Fire", "Test your knowledge!", len(questions))]
    for n, q in enumerate(questions, 1):
        out.append(f'<div style="{CARD}"><div style="font-size:0.85em;font-weight:600;color:#1976d2;margin-bottom:6px">'
                   f'Statement {n} of {len(questions)}</div><div style="font-size:1.15em;color:#333;line-height:1.6">{q["statement"]}</div></div>')
        explanation = re.sub(r"^(Correct|False|True|Incorrect)!\s*", "", q["explanation"])
        out.append(answer_box(q["answer"], "True" if q["answer"] else "False", explanation))
    out.append("</div>")
    return "\n".join(out)


QUIZ = re.compile(r'<div id="(mcqRoot|trueFalseRoot)"></div>\s*<script>.*?</script>', re.S)


def convert_quiz(m: re.Match) -> str:
    s = m.group(0)
    i = s.index("var questions = ") + len("var questions = ")
    questions, _ = json.JSONDecoder().raw_decode(s[i:])
    return mcq(questions) if m.group(1) == "mcqRoot" else true_false(questions)


FLIP_CARD = re.compile(
    r'<div id="flip-[\w-]+"[^>]*>\n<div[^>]*preserve-3d[^>]*>\n'
    r'<div[^>]*backface-visibility: hidden;[^>]*display: flex; flex-direction: column[^>]*>\n(?P<front>.*?)'
    r'<div style="margin-top: auto; color: #9AA6AB[^>]*>Click to flip</div>\n</div>\n'
    r'<div[^>]*rotateY\(180deg\)[^>]*>\n(?P<back>.*?)</div>\n</div>\n</div>', re.S)
FLIP_SCRIPT = re.compile(r'<script>\s*\(function\(\) \{\s*var ids = \["flip-.*?</script>\n?', re.S)


def convert_flip(m: re.Match) -> str:
    return ('<details style="background:#F9F7F4;border:1px solid #DCE0E2;border-radius:10px;padding:18px">\n'
            f'<summary style="cursor:pointer;list-style:none">\n{m.group("front")}'
            '<div style="color:#9AA6AB;font-size:0.8em;padding-top:10px">&#x25B6; Click for more</div>\n</summary>\n'
            '<div style="margin-top:12px;background:#EEF3F5;border:1px solid #618794;border-radius:8px;padding:14px 16px">\n'
            f'{m.group("back")}</div>\n</details>')


TAB_BUTTONS = re.compile(r'<div[^>]*>\n?(?:<button id="sparkui-btn-[^>]*>.*?</button>\n?)+</div>\n?', re.S)
TAB_SCRIPT = re.compile(r"<script>\s*\(function\(\) \{\s*var tabs = \['jobs'.*?</script>\n?", re.S)


def convert_tabs(text: str) -> str:
    text = TAB_BUTTONS.sub("", text)
    text = TAB_SCRIPT.sub("", text)
    return re.sub(r'(<div id="sparkui-panel-\w+" style=")display: (?:none|block);(.*?)border-top: none; border-radius: 0 0 8px 8px',
                  r'\1display: block;\2border-radius: 8px; margin-bottom: 12px', text)


def convert(text: str) -> tuple[str, int]:
    text, n = QUIZ.subn(convert_quiz, text)
    text, f = FLIP_CARD.subn(convert_flip, text)
    if f:
        text = FLIP_SCRIPT.sub("", text)
        text = text.replace("Click any card to flip it and reveal more detail.", "Click any card to reveal more detail.")
    t = 0
    if "sparkui-btn-" in text:
        text, t = convert_tabs(text), 1
    return text, n + f + t


def main() -> None:
    for path in sys.argv[1:]:
        nb = json.load(open(path, encoding="utf-8"))
        total = 0
        for cell in nb["cells"]:
            new, n = convert("".join(cell["source"]))
            if n:
                total += n
                cell["source"] = new.splitlines(keepends=True)
        if total:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
            print(f"{total:3} widgets  {path}")


if __name__ == "__main__":
    main()
