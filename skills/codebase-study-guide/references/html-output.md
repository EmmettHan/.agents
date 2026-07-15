# HTML Output Contract

The default artifact for `codebase-study-guide` is a single self-contained HTML file.

## Location

- Default: `.claude/docs/study-guide.html`
- If the user specifies a directory or filename, follow it. Do not hardcode user-specific directories or filenames into the skill.
- Do not create a Markdown file as the primary deliverable unless the user explicitly asks for Markdown.

## Language

Use Simplified Chinese by default unless the user explicitly requests another language.

## Required structure

Use a normal HTML document with:

1. `<!doctype html>` and `<meta charset="utf-8">`.
2. A descriptive `<title>` and one visible `<h1>`.
3. A table of contents linking to the main sections.
4. Semantic `<main>`, `<section>`, `<article>`, `<table>`, `<pre><code>`, and `<footer>` elements where appropriate.
5. The content progression from purpose → threshold concepts → system map → worked request → deep dives → boundaries/tests → next steps.

## Presentation rules

- Keep prose readable on a light page background.
- Give `<pre>` blocks an explicit dark background and light text; do not rely on browser defaults.
- Give evidence/source blocks a separate visible background and show absolute paths plus line anchors.
- Use responsive CSS for tables, diagrams, and narrow screens.
- Use callouts for threshold concepts, design tradeoffs, self-tests, and exploration tasks.
- Use inline HTML/CSS/SVG for diagrams. Avoid external Mermaid, CSS, JavaScript, font, image, or CDN dependencies unless the user explicitly requests them.

## Evidence rules

- Verify source paths before including them.
- Separate confirmed facts from inference. Mark inference explicitly.
- For each important call-chain edge, include the function name and an absolute source path; add a line anchor when available.
- Distinguish compile-time dependencies, runtime library loading, IPC, in-process calls, and kernel/system-call boundaries.

## Learning rules

- Keep the 2–3 threshold concepts near the beginning.
- Pair each major textual model with a visual map, flow, timeline, or table.
- Include worked code examples with annotations explaining why the code exists.
- Include retrieval prompts and PRIMM-style tasks: Predict → Run → Investigate → Modify → Make.
- End with a staged learning route that removes guidance over time.

## Validation checklist

- Open the HTML directly if possible and confirm the layout is readable.
- Check that code text contrasts with its background.
- Check that every major section has a visible heading and that the table of contents anchors work.
- Check balanced structural tags and valid escaping of code examples.
- Re-check every absolute source path and line anchor used as evidence.
- Confirm the output does not silently depend on network access.
