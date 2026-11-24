# CLAUDE.md

Before writing or changing any code in this repository, read and follow [doc/code_standard.md](doc/code_standard.md).

## Show every step with a worked example

Every notebook, in every layer, shows what each step does to the data, not only what the code does:

- Pick one small, real example of the notebook's input, a few rows, and follow those rows through every step to the end.
- In each step's markdown cell, add a table for each sub-step that changes the data. Label it with the step number, a letter and the operation that does it, such as **2a. After `groupBy`** or **2b. After `join`**. Show the columns as they are right after that operation.
- Shorten long values with `…`, write line breaks as `⏎`, and put HTML, JSON or binary values in backticks so they are not rendered.
- If a sub-step changes nothing in the example, say so in one line and say what it would change on other data.
- End with the rows exactly as they are written to the output table.
- When the code changes, update the example so it still matches the code.
