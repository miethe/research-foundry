---
name: nano-banana-pro
description: Generate/edit images with Nano Banana Pro (Gemini 3 Pro Image). Use for image create/modify requests incl. edits. Supports text-to-image + image-to-image; 1K/2K/4K; use --input-image.
---

# Nano Banana Pro Image Generation & Editing

Generate new images or edit existing ones using Google's Nano Banana Pro API (Gemini 3 Pro Image).

## Usage

Run the script using absolute path (do NOT cd to skill directory first):

**Generate new image:**
```bash
uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "your image description" --filename "output-name.png" [--resolution 1K|2K|4K] [--api-key KEY]
```

**Edit existing image:**
```bash
uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "editing instructions" --filename "output-name.png" --input-image "path/to/input.png" [--resolution 1K|2K|4K] [--api-key KEY]
```

**Important:** Always run from the user's current working directory so images are saved where the user is working, not in the skill directory.

## Default Workflow (draft → iterate → final)

Goal: fast iteration without burning time on 4K until the prompt is correct.

- Draft (1K): quick feedback loop
  - `uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "<draft prompt>" --filename "yyyy-mm-dd-hh-mm-ss-draft.png" --resolution 1K`
- Iterate: adjust prompt in small diffs; keep filename new per run
  - If editing: keep the same `--input-image` for every iteration until you’re happy.
- Final (4K): only when prompt is locked
  - `uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "<final prompt>" --filename "yyyy-mm-dd-hh-mm-ss-final.png" --resolution 4K`

## Resolution Options

The Gemini 3 Pro Image API supports three resolutions (uppercase K required):

- **1K** (default) - ~1024px resolution
- **2K** - ~2048px resolution
- **4K** - ~4096px resolution

Map user requests to API parameters:
- No mention of resolution → `1K`
- "low resolution", "1080", "1080p", "1K" → `1K`
- "2K", "2048", "normal", "medium resolution" → `2K`
- "high resolution", "high-res", "hi-res", "4K", "ultra" → `4K`

## API Key

The script checks for API key in this order:
1. `--api-key` argument (use if user provided key in chat)
2. `GEMINI_API_KEY` environment variable

If neither is available, the script exits with an error message.

## Preflight + Common Failures (fast fixes)

- Preflight:
  - `command -v uv` (must exist)
  - `test -n \"$GEMINI_API_KEY\"` (or pass `--api-key`)
  - If editing: `test -f \"path/to/input.png\"`

- Common failures:
  - `Error: No API key provided.` → set `GEMINI_API_KEY` or pass `--api-key`
  - `Error loading input image:` → wrong path / unreadable file; verify `--input-image` points to a real image
  - “quota/permission/403” style API errors → wrong key, no access, or quota exceeded; try a different key/account

## Filename Generation

Generate filenames with the pattern: `yyyy-mm-dd-hh-mm-ss-name.png`

**Format:** `{timestamp}-{descriptive-name}.png`
- Timestamp: Current date/time in format `yyyy-mm-dd-hh-mm-ss` (24-hour format)
- Name: Descriptive lowercase text with hyphens
- Keep the descriptive part concise (1-5 words typically)
- Use context from user's prompt or conversation
- If unclear, use random identifier (e.g., `x9k2`, `a7b3`)

Examples:
- Prompt "A serene Japanese garden" → `2025-11-23-14-23-05-japanese-garden.png`
- Prompt "sunset over mountains" → `2025-11-23-15-30-12-sunset-mountains.png`
- Prompt "create an image of a robot" → `2025-11-23-16-45-33-robot.png`
- Unclear context → `2025-11-23-17-12-48-x9k2.png`

## Image Editing

When the user wants to modify an existing image:
1. Check if they provide an image path or reference an image in the current directory
2. Use `--input-image` parameter with the path to the image
3. The prompt should contain editing instructions (e.g., "make the sky more dramatic", "remove the person", "change to cartoon style")
4. Common editing tasks: add/remove elements, change style, adjust colors, blur background, etc.

## Prompt Handling

**For generation:** Pass user's image description as-is to `--prompt`. Only rework if clearly insufficient.

**For editing:** Pass editing instructions in `--prompt` (e.g., "add a rainbow in the sky", "make it look like a watercolor painting")

Preserve user's creative intent in both cases.

## Prompt Templates (high hit-rate)

Use templates when the user is vague or when edits must be precise.

- Generation template:
  - “Create an image of: <subject>. Style: <style>. Composition: <camera/shot>. Lighting: <lighting>. Background: <background>. Color palette: <palette>. Avoid: <list>.”

- Editing template (preserve everything else):
  - “Change ONLY: <single change>. Keep identical: subject, composition/crop, pose, lighting, color palette, background, text, and overall style. Do not add new objects. If text exists, keep it unchanged.”

## Output

- Saves PNG to current directory (or specified path if filename includes directory)
- Script outputs the full path to the generated image
- **Do not read the image back** - just inform the user of the saved path

## Examples

**Generate new image:**
```bash
uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "A serene Japanese garden with cherry blossoms" --filename "2025-11-23-14-23-05-japanese-garden.png" --resolution 4K
```

**Edit existing image:**
```bash
uv run ~/.codex/skills/nano-banana-pro/scripts/generate_image.py --prompt "make the sky more dramatic with storm clouds" --filename "2025-11-23-14-25-30-dramatic-sky.png" --input-image "original-photo.jpg" --resolution 2K
```

## Asset Pipeline Integration

When generating images for a project, follow the asset pipeline configuration from `.claude/config/multi-model.toml`.

**Output structure**:
```
assets/ai-gen/
  {date}/
    nbp/
      {filename}.png              # Generated image
      {filename}.prompt.txt       # Exact prompt used
      {filename}.meta.json        # Provenance metadata
```

**Provenance metadata format** (`meta.json`):
```json
{
  "model": "gemini-3-pro-image",
  "product_name": "Nano Banana Pro",
  "timestamp": "2026-02-25T14:30:00Z",
  "prompt": "full prompt text",
  "resolution": "2048x2048",
  "seed": null,
  "parameters": {},
  "watermark_preserved": true,
  "generation_attempt": 1
}
```

**Rules**:
- Always save prompt alongside output (`store_prompts = true` in config)
- Preserve Google's image generation metadata/watermarking
- Save seeds when available for reproducibility
- Use date-based directory structure for organization
- Create `assets/ai-gen/` directory if it doesn't exist

## Batch Generation

For generating multiple related images (icon sets, marketing variants):
1. Generate sequentially (not parallel) to maintain rate limit compliance
2. Use consistent prompt prefix for style coherence across batch
3. Name files descriptively: `hero-dark.png`, `hero-light.png`, `icon-search.png`
4. Generate at draft resolution (1K) first, iterate, then final resolution (2K or 4K)

## Model Routing Context

NBP is the default for `image_generation` in multi-model config. Routing:
- High-fidelity images (marketing, hero art) → NBP at 4K
- Contextual images (UI mockups with code understanding) → Gemini 3.1 Pro
- Icon sets / simple graphics → NBP at 1K (draft) → 2K (final)
- If NBP fails → fallback to Gemini 3.1 Pro inline generation

**Important**: Gemini 3.1 Pro Image Generation and NBP use the same underlying model (Gemini 3 Pro Image). NBP is the direct image generation interface; Gemini adds reasoning/multimodal context. Choose based on whether you need code-context-aware generation (Gemini) or pure image quality (NBP).

## Integration with Creative Workflows

- Referenced from `model-selection-guide.md` for image routing decisions
- Works alongside Gemini for UI mockup → implementation workflows
- Output directory managed per `[asset_pipeline]` config in `multi-model.toml`
