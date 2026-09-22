# Lossless Audit

Tells you whether a FLAC is actually lossless, or whether someone decoded an
MP3 and re-encoded it so the file extension would say otherwise.

Reads the file, measures its long-term spectrum, and scores it out of 100.
Runs from the terminal or as a small local web app. Works in English and
Persian.

## The problem

Buy or download a "lossless" album and a fair number of the files are not.
Somebody took a 128 kbps MP3, decoded it, encoded the result as FLAC, and
now it is a 30 MB file carrying 128 kbps of music. The container is honest;
the contents are not. Nothing about the file's metadata will tell you, and
by the time you notice you have already replaced the original.

The giveaway is in the spectrum. Every lossy encoder discards the top of the
band to save bits, and does it with a filter so steep that nothing in nature
produces the same shape:

| Source | Content stops at |
|---|---|
| MP3 128 kbps | ~16 kHz |
| MP3 192–256 kbps | ~18–19 kHz |
| MP3 320 kbps / AAC 256 | ~20 kHz |
| Real CD audio | 22.05 kHz, with no step |

Encode that to FLAC and the wall is preserved perfectly, because FLAC is
lossless — it faithfully stores the damage.

## The mistake most detectors make

"Is there anything above 20 kHz?" does not work. Every 16-bit file has
dither, and dither is broadband: its noise floor reaches Nyquist in a
transcode just as it does in a genuine rip. Ask that question and everything
passes.

What separates them is the *step*. A real recording's spectrum decays
smoothly. A transcode falls off a cliff — 40 dB inside 600 Hz — and then
runs flat along the noise floor. This tool looks for the cliff, not for the
presence of high frequencies.

The first version of this scorer got that wrong and passed every fake it was
given. The fixtures in `tests/` exist so that cannot happen again quietly.

## Install

Python 3.8 or newer and libsndfile. No pip packages.

```sh
# Debian / Ubuntu
sudo apt install libsndfile1

# macOS
brew install libsndfile
```

Then:

```sh
git clone https://github.com/sarabbafrani/lossless-audit
cd lossless-audit
python3 -m losslessaudit.cli path/to/album/
```

Or install it properly:

```sh
pip install .
lossless-audit path/to/album/
lossless-audit-gui
```

## Command line

```
$ lossless-audit --no-chart suspicious.flac
======================================================================
suspicious.flac
======================================================================
  FLAC / PCM 16 / 44100 Hz / 2 ch / 4:12 / 28.4 MB

  24 / 100   Poor — re-encoded from a lossy source
    Bandwidth               15.4 / 60   brick wall at 15.9 kHz
    Bit depth               15.0 / 15   16 real bits
    Sample rate             10.0 / 10   44100 Hz
    Headroom                15.0 / 15   no clipping
```

Without `--no-chart` it also draws the spectrum, which is usually enough to
see the wall with your own eyes.

Useful flags:

```
--lang en|fa       output language (defaults to your locale)
--json             machine-readable, for scripting
--fail-under N     exit 1 if anything scores below N
--no-chart         numbers only
```

`--fail-under` makes it usable as a gate:

```sh
lossless-audit --fail-under 80 --no-chart ~/Music/ || echo "something is fake"
```

## Web interface

```sh
lossless-audit-gui        # or: python3 -m losslessaudit.webapp
```

Opens a page on `127.0.0.1`. Drag files onto it, or point it at a folder.
Each file gets a score ring, its spectrum with the wall marked, and the
breakdown of where the points went. A button switches between English and
Persian without re-reading anything.

The server binds to localhost only and nothing is uploaded anywhere — the
files are read by the same process that draws the page.

## How the score works

100 points across four things a file can get wrong:

| Component | Points | What it catches |
|---|---:|---|
| Bandwidth | 60 | the lossy wall |
| Bit depth | 15 | 24-bit files padded up from 16 |
| Sample rate | 10 | 96 kHz files upsampled from CD |
| Headroom | 15 | clipping, loudness-war masters |

A confirmed wall caps the total rather than costing it 13 points, because a
fake FLAC is otherwise free to collect full marks on the other three — an
early version scored a known transcode 87/100 that way. With the cap, a wall
at 20 kHz lands around 51 and one at 16 kHz around 24.

`docs/scoring.md` has the exact curves.

## What it cannot tell you

Worth being clear about, because a number out of 100 invites more trust than
it deserves.

**It scores the file, not the music.** A genuinely lossless transfer of a
1955 mono recording has little above 15 kHz because the microphone did not
capture any. There is no wall, so it scores well — correctly, since the file
is intact — but the score says nothing about whether it sounds good.

**Noise above the wall defeats it.** Anyone who adds synthetic hiss to the
top of the spectrum after transcoding fills the cliff in and passes. This is
rare, and it is deliberate fraud rather than laziness, but it is possible.

**It does not judge naturalness.** A file whose spectrum is flat from 13 kHz
to 46 kHz is not music, but nothing here objects. Flagging that is an
obvious next feature and is not implemented yet.

**Below 20.7 kHz only.** A wall closer to Nyquist than that is reported but
not treated as proof, since resamplers leave similar marks.

Treat a low score as strong evidence and a high score as absence of the
specific evidence this tool looks for. When it shows you a 40 dB drop at
16 kHz, though, there is not much room for doubt.

## Tests

```sh
cd tests && python3 -m unittest test_engine -v
```

The fixtures are synthesised in the frequency domain with a cutoff chosen by
the test, so the correct answer is known in advance and no audio ships in
the repository. They include dither, specifically so the detector cannot
pass by taking the shortcut described above.

## Persian

[README.fa.md](README.fa.md) — همین مستندات به فارسی.

## License

MIT. See [LICENSE](LICENSE).
