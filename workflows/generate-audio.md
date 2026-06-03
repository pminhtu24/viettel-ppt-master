---
description: Generate per-slide narration audio with AI-recommended voice selection, then optionally re-export PPTX with embedded audio
---

# Generate Audio Workflow

> Standalone post-export step. Run when the user asks for "generate audio", "record narration", "narrated PPT", or "video export with voice", or proactively offer it after a deck is exported. Produces one audio file per slide via `edge-tts` by default, or a cloud TTS provider (`elevenlabs` / `minimax` / `qwen` / `cosyvoice`) when the user chooses high-quality narration or a cloned voice, then optionally re-exports a video-ready PPTX with audio embedded and per-slide auto-advance timings.

This workflow is **independent**: it reads `notes/*.md` and queries the selected TTS voice catalog — no upstream conversation context required. Safe to invoke in a fresh session.

## When to Run

- `notes/total.md` exists and has been split into per-page files at `notes/*.md` (post-processing Step 7.1 done).
- Default mode: `edge-tts` is installed (`python3 -m pip install edge-tts`).
- The workflow is page-level only: one notes file becomes one audio file. Do not use a single long audio track or attempt automatic long-audio splitting.
- PPT narration assets must be PowerPoint-reliable audio: `m4a` (AAC), `mp3`, or `wav`. The built-in TTS path defaults to `mp3`; provider formats such as `pcm`, `opus`, or `flac` must be transcoded before embedding.
- PowerPoint recorded narration export requires `ffprobe` so slide timings can be written from actual audio duration.
- High-quality cloud mode: provider API key is set before use:
  - ElevenLabs: `ELEVENLABS_API_KEY`
  - MiniMax: `MINIMAX_API_KEY`
  - Qwen: `QWEN_API_KEY` or `DASHSCOPE_API_KEY`
  - CosyVoice: `COSYVOICE_API_KEY` or `DASHSCOPE_API_KEY`
  - Keys may live in the current process environment or the first `.env` found in this order: current working directory, clone repo root, `~/.ppt-master/.env`
- The deck is in a single dominant language (mixed-language decks: pick the dominant one — the AI uses judgment, not a heuristic).

If `notes/*.md` are missing, run `total_md_split.py <project_path>` first.

---

## Step 1: Determine the deck's language

The AI already knows the deck's language from writing the notes. No detection script needed.

- Identify the primary language from the notes content: `en` / `ja` / `ko` / `vi` / `fr` / `de` / etc.
- For mixed-language decks, pick the language the audience will hear most of.
- Do not add language-specific trigger phrases or examples here; keep the workflow instructions in English.

---

## Step 2: Choose audio backend and pull the voice catalog

Default to **edge** unless the user explicitly asks for a cloud provider / higher-quality cloud narration / a cloned voice.

**edge backend**:

```bash
python3 skills/ppt-master/scripts/notes_to_audio.py --list-voices --locale <locale>
```

**ElevenLabs backend**:

```bash
python3 skills/ppt-master/scripts/notes_to_audio.py --provider elevenlabs --list-voices
```

**Cloud providers using explicit voice IDs/names**:

```bash
python3 skills/ppt-master/scripts/notes_to_audio.py --provider minimax --list-voices
python3 skills/ppt-master/scripts/notes_to_audio.py --provider qwen --list-voices
python3 skills/ppt-master/scripts/notes_to_audio.py --provider cosyvoice --list-voices
```

The output is a flat list of all available voices for the selected provider. From this list, the AI picks **3–6 candidates** to recommend, applying these rules:

- **Cover both genders** when both exist for the locale.
- **For edge**: prefer `COMMON_VOICES`-listed voices (curated set inside `notes_to_audio.py`) when the locale has them — they are battle-tested.
- **For ElevenLabs**: prefer voices already present in the user's account; if the user provides a specific `voice_id`, do not override it.
- **For MiniMax / Qwen / CosyVoice**: if the user provides a cloned `voice_id`, use it directly. Do not attempt voice cloning inside the narration workflow.
- **Match the deck's tone** — pick the strongest recommendation based on style:
  - English consultant deck → `en-US-GuyNeural` (steady) or `en-US-JennyNeural` (clear)
  - General product or training deck → clear, friendly voices with moderate pacing
  - Launch or broadcast-style deck → confident presenter voices with strong articulation
  - Japanese / Korean / other supported languages → pick locale-matched neural voices and mark gender + tone

For each candidate, write a **one-line English description** covering: gender, tone, and best-fit use case. For cloud providers, include the voice name/ID exactly as it must be passed to `--voice-id`.

---

## Step 3: One-shot user interaction (mandatory)

Send a single message to the user that asks all three questions at once and provides a recommended value for each. Do NOT split into multiple rounds.

**Cloned-voice fast path**: if the user mentioned a cloned voice, voice clone, "my own voice", or similar phrasing along with a `voice_id`, skip the voice-recommendation list — set the provider to whichever the user named (`elevenlabs` / `minimax` / `qwen` / `cosyvoice`), pin the `voice_id` they gave you, and only confirm rate + embed-or-not.

**Message template**:

> I detected the notes language as **<language>** (locale: `<locale>`). Based on the deck tone (`<style>`), I recommend this setup:
>
> **Generation mode**: recommended `<edge|elevenlabs|minimax|qwen|cosyvoice>` because <one-sentence reason, such as "it requires no API setup and is stable" or "the user asked for high-quality cloud narration">.
>
> **Voice**:
> - **[1] <ShortName>** — <gender, tone, best-fit use case> recommended
> - [2] <ShortName> — <gender, tone, best-fit use case>
> - [3] <ShortName> — <gender, tone, best-fit use case>
> - [4] <ShortName> — <gender, tone, best-fit use case>
> - [5] <ShortName> — <gender, tone, best-fit use case>
> - You can also provide another ShortName from the voice list.
>
> **Rate / style settings**: recommended `<rate or provider defaults>` because <one-sentence reason, such as "each slide has 2-3 sentences, so normal speed is the most reliable" or "provider defaults preserve the original voice quality best">.
>
> **Re-export PPTX with embedded audio after generation**: recommended **yes** because it produces a video-ready deck with slide timings based on actual audio duration.
>
> Reply "yes" to use all recommended values, or tell me what to change, such as "voice 2, rate -5%" or "use MiniMax voice_id xxx".

**Recommended-value rules**:
- Generation mode: default to `edge`; when the user explicitly wants high-quality cloud narration or provides a cloud voice ID, use the requested provider (`elevenlabs` / `minimax` / `qwen` / `cosyvoice`).
- Voice: choose the candidate from Step 2 that best matches the deck tone.
- Rate: edge defaults to `+0%`; dense notes (average >4 long sentences per slide) usually work better at `-5%`; short notes can use `+5%`; justify anything outside that range. Cloud providers use provider defaults unless the user explicitly asks for rate or style changes.
- Embed: recommend "yes" by default unless the user already has a customized PPTX they do not want overwritten.

---

## Step 4: Execute (no further interaction)

Run sequentially — do NOT bundle:

```bash
# 1A. Generate audio with edge (default)
python3 skills/ppt-master/scripts/notes_to_audio.py <project_path> \
  --voice <chosen-ShortName> --rate <chosen-rate>

# 1B. Or generate audio with ElevenLabs
python3 skills/ppt-master/scripts/notes_to_audio.py <project_path> \
  --provider elevenlabs --voice-id <chosen-voice-id> \
  --elevenlabs-model eleven_multilingual_v2

# 1C. Or generate audio with MiniMax
# Defaults to the China endpoint; set MINIMAX_TTS_BASE_URL=https://api.minimax.io/v1/t2a_v2 for overseas access.
python3 skills/ppt-master/scripts/notes_to_audio.py <project_path> \
  --provider minimax --voice-id <chosen-voice-id> \
  --minimax-model speech-2.8-hd

# 1D. Or generate audio with Qwen TTS
python3 skills/ppt-master/scripts/notes_to_audio.py <project_path> \
  --provider qwen --voice-id <chosen-voice> \
  --qwen-model qwen3-tts-flash --qwen-language-type <language-type>

# 1E. Or generate audio with CosyVoice
python3 skills/ppt-master/scripts/notes_to_audio.py <project_path> \
  --provider cosyvoice --voice-id <chosen-voice> \
  --cosyvoice-model cosyvoice-v3-flash

# 2. (If user kept embedding) Re-export PPTX with audio embedded
python3 skills/ppt-master/scripts/svg_to_pptx.py <project_path> \
  --recorded-narration audio
```

If `notes_to_audio.py` errors with a missing dependency or missing provider API key, fix the prerequisite and re-run — do NOT swallow the error.

`--recorded-narration audio` prepares PowerPoint's recorded timings and narrations: every slide must have a matching supported audio file, every duration must be readable by `ffprobe`, and object animations must not use `--animation-trigger on-click`. Use `after-previous` or `with-previous` for narrated/video export.

---

## Step 5: Completion report

Output one summary block listing:

- Number of audio files generated and their location (`<project_path>/audio/*`).
- The provider, voice, and rate/settings actually used.
- (If embedded) the new narrated PPTX path under `<project_path>/exports/`.
- (If skipped embedding) one-line hint on how to embed later: `python3 skills/ppt-master/scripts/svg_to_pptx.py <project_path> --recorded-narration audio`.
