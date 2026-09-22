# How the score is built

100 points, four components. The weights are not arbitrary: only one of the
four can detect a lossy source, so it carries most of the total, and a
confirmed detection overrides the rest.

## Bandwidth — 60 points

First the tool decides where the music actually stops.

It takes up to 90 Hann-windowed 4096-point FFTs spread across the file
(skipping the first and last 5% so fades do not skew the average), averages
their power spectra, converts to dB relative to the loudest bin, and smooths
across 9 bins.

Then it scans from 8 kHz upward for the steepest drop across any 600 Hz
span. That drop is the wall.

- **Wall** — a drop of 18 dB or more, located at least 800 Hz below Nyquist.
- **Step** — 12 to 18 dB. Suspicious, not conclusive; costs 6 points and
  caps the total at 78.
- Anything closer than 800 Hz to Nyquist is ignored: resamplers leave a
  similar mark and it proves nothing about the source.

If a wall exists, the effective bandwidth is the wall frequency. Otherwise
it is where the smoothed spectrum finally drops below −90 dB, which on a
real file is essentially Nyquist.

Points are interpolated along:

| Bandwidth | Points |
|---:|---:|
| 13.0 kHz | 4 |
| 15.0 kHz | 10 |
| 16.0 kHz | 16 |
| 17.0 kHz | 24 |
| 18.0 kHz | 30 |
| 19.0 kHz | 38 |
| 20.0 kHz | 48 |
| 20.8 kHz and up | 60 |

## Bit depth — 15 points

Every sample read is OR-ed together. The number of trailing zero bits in the
result gives the number of bits that ever actually change.

- 16 or more real bits — 15
- declared 24-bit but 16 or fewer real bits — 8 (padded, not genuine)
- 14 to 15 real bits — 10
- fewer — 5

There is no bonus above 16. A correct 16-bit file is transparent; the
penalty is for claiming depth the file does not carry.

## Sample rate — 10 points

- 44.1 kHz or higher — 10
- above 50 kHz but walled below 22.5 kHz — 6 (upsampled from CD)
- 32 to 44.1 kHz — 6
- below 32 kHz — 3

## Headroom — 15 points

A sample counts as clipped when its magnitude is within one LSB of full
scale, using the file's declared bit depth to size that LSB.

| Clipped fraction | Points |
|---:|---:|
| 0 | 15 |
| < 10⁻⁵ | 14 |
| < 10⁻⁴ | 12 |
| < 10⁻³ | 9 |
| < 10⁻² | 6 |
| more | 3 |

Three or more clipped samples in a row is a run — real clipping rather than
an isolated peak touching the ceiling. Any run costs a further 2 points.

## The cap

Summing the four components is not enough on its own. A transcode with an
honest bit depth, a standard sample rate and no clipping collects 40 points
before the bandwidth component has any say, so an early version of this
scorer gave a known 320 kbps fake 87 out of 100 while simultaneously
labelling it "poor". The number and the verdict disagreed, which makes both
useless.

So when a wall is found below 20.7 kHz, the total is capped:

| Wall at | Cap |
|---:|---:|
| 13.0 kHz | 8 |
| 15.0 kHz | 18 |
| 16.0 kHz | 25 |
| 17.5 kHz | 34 |
| 19.0 kHz | 45 |
| 20.0 kHz | 52 |
| 20.7 kHz | 58 |

A 16 kHz wall now lands at 24 and a 20 kHz wall at 51, which puts both in
the same band as the verdict.

## Grades

| Score | Grade |
|---:|---|
| 90–100 | Excellent |
| 75–89 | Good |
| 55–74 | Suspect |
| 0–54 | Poor |
