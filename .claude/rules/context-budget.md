# Context Budget Rule (Global)

Invariant:

1. **Never call `TaskOutput()`** for background agents that write files — check files on disk instead (~7.5K tokens saved per call).
2. **Task prompts < 500 words** — provide file paths, not contents. Reference patterns by path: "follow pattern in `path/to/example.tsx`".
3. **Don't read files into orchestrator context** that subagents will also read — provide paths only.
4. **Don't explore for delegated work** — let the delegated agent explore its own context.
5. **Always scope Glob** with `path` parameter to avoid node_modules pollution.

Full guidance: `CLAUDE.md` → "Context Budget Discipline" section.
