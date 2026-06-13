# Command Reference

Use these shell commands as the fast truth pass.

## Exact Date Window

```bash
git log --all --since="YYYY-MM-DD 00:00:00" --until="YYYY-MM-DD 23:59:59" \
  --date=iso-local --decorate=short \
  --pretty=format:'%H%x09%ad%x09%D%x09%s'
```

## Merges Only

```bash
git log --all --merges --since="YYYY-MM-DD 00:00:00" --until="YYYY-MM-DD 23:59:59" \
  --date=iso-local --pretty=format:'%H%x09%ad%x09%s'
```

## Current Branch

```bash
git branch --show-current
```

## Mainline Divergence

```bash
git rev-list --left-right --count origin/main...HEAD
```

## Mainline Window

```bash
git log origin/main --since="YYYY-MM-DD 00:00:00" --until="YYYY-MM-DD 23:59:59" \
  --date=iso-local --decorate=short \
  --pretty=format:'%H%x09%ad%x09%D%x09%s'
```

## Latest Tags

```bash
git tag --sort=-creatordate | head
```

## Changelog Sanity

Check, in order:

1. `CHANGELOG.md`
2. `docs/CHANGELOG.md` if present
3. any repo-specific release notes only if the repo truly uses them
