Extract only the exact visible text from the image.
Return exactly this markdown shape:
## Text
- <exact visible text line 1>
- <exact visible text line 2>
- <exact visible text line 3>
Rules:
- Maximum 8 bullets.
- Preserve exact wording and line breaks as much as possible.
- Do not summarize.
- Do not explain the text.
- Do not repeat any extracted line.
- If nothing is readable, return one bullet: "No readable text."
- No placeholders except the angle-bracket examples in this template.
- End with <END>.
