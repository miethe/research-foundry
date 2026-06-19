# Research Foundry Docs Site

Built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Build locally

```bash
pip install -e ".[docs]"
mkdocs serve -f website/mkdocs.yml
```

The dev server runs at <http://localhost:8000> with live reload.

## Production deploy

Docs are deployed automatically via `.github/workflows/docs.yml` on every push to `main` that
touches `website/**`.

**One-time repo setup**: go to GitHub → Settings → Pages → Source and select **GitHub Actions**.
