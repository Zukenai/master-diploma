# Iteration 01 Notes

The current baseline uses a lightweight TF-IDF-style sparse retrieval implementation rather than an external search engine. This keeps the stack minimal and fully local.

Reranking is represented as an interface plus no-op implementation so later iterations can extend the architecture without forcing a rewrite of the pipeline entrypoint.
