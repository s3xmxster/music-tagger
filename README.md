# Music Tagger

**Music Tagger** is a Windows desktop application written in **Python** for automatically or manually editing audio file metadata.

The program is designed for convenient music library cleanup: it can parse track information from filenames, search for metadata online, download cover art, and write tags back to audio files.

---

## Features

- Open a **folder with audio files** or a **single audio file**
- Automatically search for:
  - **artist**
  - **track title**
  - **album**
  - **release year**
- Automatically load **cover artwork**
- Create a **backup** before applying changes
- Manually edit metadata for a **single track**
- View **detailed file properties**
- Built-in track information panel with cover preview
- Supports the following audio formats:
  - **MP3**
  - **FLAC**
  - **M4A**
  - **AAC**
  - **OGG**
  - **WAV**
- Supported languages: ru/en

---

## How metadata detection works

Music Tagger performs metadata search based on the **filename** of the audio file.

For best results, the file should have a name similar to this format:

```text
Artist_-_Title
