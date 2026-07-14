---
name: explain-diff
description: Use when the user asks for a rich explanation of a code change, diff, branch, or PR. Produces a self-contained interactive HTML file (in Chinese) with Background, Intuition, Code walkthrough, and a multiple-choice Quiz. Use this skill whenever the user wants to understand a commit, diff, branch, PR, or merge — even if they just say "explain this change" or paste a diff — rather than only when they explicitly ask for "an HTML explanation".
---

# Explain Diff

Produce a rich, interactive explanation of the specified code change as a single self-contained HTML file.

## Required sections

- **Background**: Explain the existing system relevant to this change. Broadly explore the surrounding code for this (read callers, callees, tests, config, and docs). We don't know how much the reader already knows, so include a deep background for beginners (mark it as skippable for those already familiar), and then a narrower background directly relevant to the change.
- **Intuition**: Explain the core intuition for the code change. Focus on the essence, not the full details. Use concrete examples with toy data. Use figures and diagrams liberally.
- **Code**: High-level walkthrough of the changes. Group and order the changes in an understandable way (by subsystem, by commit, by concern — whatever reads best).
- **Quiz**: Five multiple-choice questions that test the reader's understanding of the change. Medium difficulty: hard enough that you need to actually understand the substance to answer, but not gotchas. The goal is to confirm real understanding. Each question is interactive — when the reader clicks an option, the page tells them whether they were right and gives feedback.

## Output format

- A single self-contained HTML file: CSS and JavaScript inlined, no external dependencies.
- One long scrolling page with section headers and a table of contents. Don't use tabs for the top-level structure.
- Basic responsive styling so it's readable on a phone.
- Save it to a global location outside the current repo (e.g. `/tmp/`), with the filename always prefixed by today's date as `YYYY-MM-DD-`, so files stay time-sorted and out of version control. Example: `/tmp/2026-01-12-explanation-<slug>.html`
- 输出内容一律使用中文（包括正文、标题、图表标注、代码注释说明、Quiz 题目与选项）。代码本身和标识符保持原样，不要翻译。
- Write with the clarity and flow of Martin Kleppmann: engaging, in classic style, with smooth transitions between sections.

## Diagrams

Pick a small number of diagram families and reuse them throughout:

- A simplified version of the UI the user sees, to explain UI changes.
- A system diagram showing data flow or communication between components — include example data in it.

Rules:

- Don't use ASCII diagrams. Always use simple HTML/CSS for diagrams, HTML lists for lists of things, etc.
- For code blocks, always use `<pre>` tags. If you use a custom styled div instead, it **must** have `white-space: pre-wrap` in its CSS, or the browser will collapse all newlines into a single line.
- Before saving, scan each code block in the HTML source and confirm its CSS includes `white-space: pre` or `pre-wrap`.
- Use callouts for key concepts, definitions, and important edge cases.
