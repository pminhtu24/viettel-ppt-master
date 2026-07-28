> See [`image-searcher.md`](./image-searcher.md) for provider behavior. Technical SVG/PPT constraints are in [`shared-standards.md`](./shared-standards.md).

# Web Image Acquisition Reference

## 1. Trigger

Run only when at least one resource-list row has `Acquire Via: web` and `Status: Pending`. Skip `user` and `placeholder` rows.

Allowed values are `web`, `user`, and `placeholder`. AI image generation is not supported.

For a legacy row whose `Acquire Via` value is `ai`:

- If its file exists, change it to `Acquire Via: user`, `Status: Existing`.
- If its file is absent, stop before Executor and ask the user to choose web sourcing, provide a file, or use a placeholder. Do not silently search the web.

## 2. Resource-list contract

| Filename | Dimensions | Purpose | Type | Acquire Via | Status | Reference |
|---|---|---|---|---|---|---|
| team.jpg | 800x600 | Team photo | Photography | `web` | Pending | Diverse engineering team in a modern office |

Every row requires `Acquire Via`, `Status`, and `Reference`.

| Acquire Via | Action | Terminal status |
|---|---|---|
| `web` | Run `image_search.py` | `Sourced` or `Needs-Manual` |
| `user` | Confirm the file exists | `Existing` |
| `placeholder` | No acquisition | `Placeholder` |

## 3. Workflow

1. Read `design_spec.md` and collect pending web rows.
2. Confirm `project/images/` exists.
3. Run the provider flow in [`image-searcher.md`](./image-searcher.md).
4. Retry a recoverable failure once with broader search parameters.
5. After a second failure, set `Status: Needs-Manual`, report the filename and reason, then continue.
6. Confirm no web row remains `Pending`.

`project/images/image_sources.json` is the single source of truth for license and attribution data. Do not place credits in speaker notes, SVG metadata, or a separate appendix.

## 4. Executor handoff

| Artifact | Path | Purpose |
|---|---|---|
| Image files | `project/images/*.{jpg,png,webp}` | SVG `<image>` references |
| Source manifest | `project/images/image_sources.json` | License tier and inline attribution |

Executor does not invoke `image_search.py`. It embeds `Existing` and `Sourced` files, adds inline attribution when required, and renders a dashed placeholder for `Placeholder` or unresolved `Needs-Manual` rows.

```markdown
## ✅ Image Acquisition Phase Complete
- [x] {N} web rows processed
- [x] Each row is `Sourced` or `Needs-Manual`
- [x] image_sources.json written
- [ ] **Next**: Auto-proceed to Executor phase
```
