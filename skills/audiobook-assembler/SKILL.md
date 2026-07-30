---
name: audiobook-assembler
description: Assemble audiobooks from groups of audio files (per-chapter .m4a/.mp3 directories, standalone files) into one .m4b per book — AAC 128 kbps, chapter markers, title/author metadata, and "Series NN - Title" filenames. Use when the user asks to assemble, combine, or convert audiobook files into .m4b.
---

# Audiobook assembler

Turn a collection of audiobook audio files into one `.m4b` per book.
You supply the judgment (what is a book, which series it belongs to,
what it should be named); the bundled `assemble.py` supplies the
deterministic ffmpeg mechanics. All audio processing runs in the
`audiobook-assembler` container image — never rely on host ffmpeg.

## Setup (once per machine)

Build the image from this skill's directory if it does not exist yet:

```sh
container image list | grep -q audiobook-assembler \
  || container build -t audiobook-assembler <this skill's directory>
```

## Procedure

1. **Survey the input.** The layout of the input is not defined in
   advance: books may arrive as one directory of per-chapter files,
   several books' files mixed flat in one directory, a nested
   author/series tree, lone standalone files, or any combination.
   Do not assume directory == book. Use every clue available —
   directory structure, file names, embedded tags, and your own
   knowledge of the works (how many books an author or series
   contains, their titles and order, roughly how many chapters or
   parts each has) — to work out how many books the input contains
   and which files belong to each.
   Probe tags via the image:
   `container run --rm -v <dir>:/in:ro audiobook-assembler -c
   "import json,subprocess;print(subprocess.run(['ffprobe','-v','error','-show_entries','format_tags','-of','json','/in/<file>'],capture_output=True,text=True).stdout)"`.
   Ignore non-audio files. Group editions of the same title — the
   narrator usually appears in parentheses in the directory/file name
   or in the `comment` tag. The goal of this step is a partitioning:
   every audio file assigned to exactly one book, each book to become
   one `.m4b`.

2. **Identify each book.** Cross-check tags against names — prefer
   tags when present and consistent (`album` → title, `artist` →
   author, `date` → year), fall back to parsing names (a leading year,
   a parenthesized narrator, trailing bitrate/duration/size
   annotations like `64k 09.40.05 {275mb}`), and treat any
   disagreement between the two as a signal to look closer rather
   than silently picking one. Determine series membership and book
   number from your own knowledge of the author's bibliography plus
   context clues (titles, years, directory names). **Before running a
   batch, present the file→book partitioning and the planned
   `Series NN - Title` mapping to the user** — this is the step where
   mistakes are cheap.

3. **Assemble each book.** Create the destination directory
   (`mkdir -p` then `chmod 777` it — the container runs as uid 1000),
   mount the input root, and pass the book's files explicitly:

   ```sh
   container run --rm \
     -v <input root>:/in:ro -v <dest dir>:/out \
     audiobook-assembler /opt/asm/assemble.py \
       --title "<Title>" --author "<Author>" \
       [--narrator "<Narrator>"] [--date <year>] \
       -o "/out/<Filename>.m4b" /in/<file 1> /in/<file 2> ...
   ```

   Files are ordered by `track` tag, then natural filename sort, so
   the order you list them matters only as a tiebreak. The script
   writes chapters from the files' `title` tags, encodes AAC 128 kbps,
   self-checks the result with ffprobe (codec, duration, chapter
   count, tags), and exits nonzero on any mismatch — treat a failure
   as a stop-and-report, not a skip.

4. **Filenames.** Series books: `<Series> <NN> - <Title>.m4b`
   (two-digit number, e.g. `The Book of the New Sun 01 - The Shadow of
   the Torturer.m4b`). Standalones: `<Title>.m4b`. Replace any
   filesystem-hostile characters (`/`, leading/trailing dots).

5. **Layout.** `<dest>/<Author>/<Filename>.m4b`. When a title exists
   in multiple editions (different narrators), assemble **all** of
   them and disambiguate by directory:
   `<dest>/<Author>/<Title> (<Narrator>)/<Filename>.m4b` — the
   narrator directory is used only for multi-edition titles.

6. **Existing .m4b files are never re-encoded**, regardless of
   bitrate. Remux them instead (`--remux`, exactly one input): stream
   copy with the new name and metadata, chapters preserved.

7. **Report.** End with a summary table: book → output path, duration,
   chapters, size. Flag anything you were uncertain about (series
   guesses, tag oddities, skipped files).
