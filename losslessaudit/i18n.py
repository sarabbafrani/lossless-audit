"""Message catalogue.

The analysis code never builds a sentence. It returns a message code plus
whatever numbers belong in it, and the interface renders that in whichever
language the user picked. Adding a language means adding one dict below.
"""

import re

LANGUAGES = ("en", "fa")

MESSAGES = {
    "en": {
        # score components
        "part.bandwidth": "Bandwidth",
        "part.bits": "Bit depth",
        "part.rate": "Sample rate",
        "part.headroom": "Headroom",

        "bw.wall": "brick wall at {f} kHz",
        "bw.step": "suspicious step at {f} kHz",
        "bw.clean": "no wall; natural roll-off to {f} kHz",

        "bits.padded": "claims {declared}-bit, only {eff} bits carry data",
        "bits.ok": "{eff} real bits",
        "bits.low": "only {eff} bits used",
        "bits.verylow": "very low bit depth ({eff})",

        "rate.upsampled": "{sr} Hz but nothing above {f} kHz — upsampled",
        "rate.ok": "{sr} Hz",
        "rate.low": "{sr} Hz — below CD rate",
        "rate.verylow": "{sr} Hz — very low",

        "clip.none": "no clipping",
        "clip.few": "a handful of samples at full scale",
        "clip.tiny": "very slight clipping",
        "clip.some": "noticeable clipping",
        "clip.lots": "heavy clipping — loudness-war master",
        "clip.severe": "severe clipping",
        "clip.runs": " ({n} consecutive runs)",

        # verdicts
        "grade.excellent": "Excellent",
        "grade.good": "Good",
        "grade.suspect": "Suspect",
        "grade.poor": "Poor",

        "tag.from_lossy": "re-encoded from a lossy source",
        "tag.anomaly": "spectral anomaly worth a look",
        "tag.clean": "genuine lossless",
        "tag.minor": "sound, with a minor flaw",
        "tag.low": "low quality",

        # errors
        "err.short": "file is too short to analyse",
        "err.unread": "no audio could be read from this file",
        "err.notdir": "that path is not a folder",

        # web interface
        "ui.title": "Lossless Audit",
        "ui.sub": "Find out whether a FLAC is genuinely lossless or was made from an MP3.",
        "ui.drop": "Drop audio files here",
        "ui.drophint": "or click to choose — several at once is fine",
        "ui.folder": "or type the path to a folder",
        "ui.scan": "Scan folder",
        "ui.quit": "Quit",
        "ui.checking": "Checking {i} of {n}",
        "ui.done": "Checked {n} files.",
        "ui.searching": "Looking through the folder…",
        "ui.nofiles": "No audio files in that folder.",
        "ui.unreadable": "Could not read that folder.",
        "ui.failed": "Could not read: {msg}",
        "ui.of100": "of 100",
        "ui.closed": "Stopped. You can close this tab.",
        "ui.legend": ("Out of 100: bandwidth 60, bit depth 15, sample rate 10, "
                      "headroom 15. A confirmed lossy wall caps the total. "
                      "This is strong evidence, not proof — old recordings "
                      "genuinely lack high frequencies."),
        "ui.lang": "فارسی",
    },

    "fa": {
        "part.bandwidth": "پهنای باند",
        "part.bits": "عمق بیت",
        "part.rate": "نرخ نمونه‌برداری",
        "part.headroom": "سقف و بریدگی",

        "bw.wall": "دیوار تیز در {f} کیلوهرتز",
        "bw.step": "پله مشکوک در {f} کیلوهرتز",
        "bw.clean": "بدون دیوار، افت طبیعی تا {f} کیلوهرتز",

        "bits.padded": "ادعای {declared} بیت، ولی فقط {eff} بیت داده دارد",
        "bits.ok": "{eff} بیت واقعی",
        "bits.low": "فقط {eff} بیت استفاده شده",
        "bits.verylow": "عمق بیت خیلی کم ({eff})",

        "rate.upsampled": "{sr} هرتز ولی محتوا تا {f} کیلوهرتز — بالا برده شده",
        "rate.ok": "{sr} هرتز",
        "rate.low": "{sr} هرتز — پایین‌تر از استاندارد سی‌دی",
        "rate.verylow": "{sr} هرتز — خیلی پایین",

        "clip.none": "بدون بریدگی",
        "clip.few": "چند نمونه در سقف",
        "clip.tiny": "بریدگی خیلی جزئی",
        "clip.some": "بریدگی محسوس",
        "clip.lots": "بریدگی زیاد — مستر فشرده",
        "clip.severe": "بریدگی شدید",
        "clip.runs": " ({n} مورد پشت‌سرهم)",

        "grade.excellent": "عالی",
        "grade.good": "خوب",
        "grade.suspect": "مشکوک",
        "grade.poor": "ضعیف",

        "tag.from_lossy": "از یک فایل با اتلاف ساخته شده",
        "tag.anomaly": "نشانه مشکوک در طیف",
        "tag.clean": "بی‌اتلاف و سالم",
        "tag.minor": "سالم، با ایراد جزئی",
        "tag.low": "کیفیت پایین",

        "err.short": "فایل کوتاه‌تر از آن است که بشود تحلیل کرد",
        "err.unread": "صدایی از این فایل خوانده نشد",
        "err.notdir": "این مسیر پوشه نیست",

        "ui.title": "سنجش کیفیت صدا",
        "ui.sub": "بفهم فایل واقعاً بی‌اتلاف است یا از یک ام‌پی‌تری ساخته شده.",
        "ui.drop": "فایل‌ها را اینجا بینداز",
        "ui.drophint": "یا کلیک کن و انتخاب کن — چند تا با هم هم می‌شود",
        "ui.folder": "یا مسیر یک پوشه را اینجا بنویس",
        "ui.scan": "بررسی پوشه",
        "ui.quit": "بستن برنامه",
        "ui.checking": "در حال بررسی {i} از {n}",
        "ui.done": "{n} فایل بررسی شد.",
        "ui.searching": "در حال گشتن در پوشه…",
        "ui.nofiles": "فایل صوتی در این پوشه پیدا نشد.",
        "ui.unreadable": "پوشه خوانده نشد.",
        "ui.failed": "خوانده نشد: {msg}",
        "ui.of100": "از ۱۰۰",
        "ui.closed": "برنامه بسته شد. می‌توانی این صفحه را ببندی.",
        "ui.legend": ("نمره از صد: پهنای باند شصت، عمق بیت پانزده، "
                      "نرخ نمونه‌برداری ده، سقف و بریدگی پانزده. "
                      "اگر دیوار قطعی پیدا شود سقف نمره می‌آید پایین. "
                      "این شاهد قوی است نه اثبات قطعی — ضبط‌های قدیمی "
                      "طبیعتاً فرکانس بالا ندارند."),
        "ui.lang": "English",
    },
}


_SLOT = re.compile(r"\{(\w+)\}")


def fill(template, args):
    """Substitute {name} slots. Deliberately simpler than str.format so the
    browser can run the identical logic on the identical catalogue."""
    if not args:
        return template
    return _SLOT.sub(lambda m: str(args.get(m.group(1), m.group(0))), template)


def t(lang, code, **kw):
    """Render one message. An unknown language falls back to English."""
    table = MESSAGES.get(lang) or MESSAGES["en"]
    return fill(table.get(code) or MESSAGES["en"].get(code, code), kw)


def catalogue(lang):
    """The whole table for one language, for handing to the web interface."""
    base = dict(MESSAGES["en"])
    base.update(MESSAGES.get(lang, {}))
    return base
