---
name: extract_keywords
track: core
kind: local_formatter
requires_env: []
inputs: [text, max_keywords, min_length]
outputs: [keywords, keyword_count, token_count]
side_effect: false
---
# extract_keywords

Extracts simple keyword frequencies from text already provided by the user or already collected by another tool.

Use this tool when the user asks to identify keywords, themes, repeated terms, or tags from known text. It does not search the web, read URLs, or fetch new information.
