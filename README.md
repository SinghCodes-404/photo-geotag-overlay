# Photo Location Stamp

Two small Python scripts that add a **"GPS Map Camera"–style banner** to the
bottom of your photos — the kind that shows a little map, the place name, the
full address, the coordinates, and the day/date/time:

```
┌───────┐  Nanowal Khurd, Punjab, India                     ← place name
│  map  │  Nanowal-Lakhanpur Road, Nanowal Khurd, Khamanon
│  pin  │  Tahsil, Fatehgarh Sahib, Punjab, 141801, India   ← full address
└───────┘  Lat: 30.839203°  Long: 76.313354°                ← coordinates
           Wednesday, 24/06/2026 09:04 AM GMT +05:30         ← day / date / time
```

The **location** is read from the GPS that your phone camera saved inside each
photo. The **date and time** are set by you, from the way you name your folders
(explained below) — this exists because a phone clock can be wrong, and for
something like a college internship the timestamps need to actually make sense.

There are two scripts and you run them in order:

1. **`set_datetime.py`** — sets the correct date/time on each photo.
2. **`geotag.py`** — draws the banner onto each photo.

> **Heads up:** these are Python scripts, so far tested on Linux. They also work
> on Windows and macOS — you just install Python first. Steps for all three are
> below. You do **not** need to be a programmer to use this; copy the commands
> as written.

---

## What you need first

- **Python 3** (version 3.8 or newer).
- Two Python packages: **Pillow** and **piexif**.
- **An internet connection** while running `geotag.py` — it fetches the map and
  looks up the address online.
- Each photo must actually **contain GPS location** (most phone cameras save this
  automatically if Location was on). Photos without GPS are simply skipped with a
  message; they won't crash the run.

---

## Installation

Pick the section for your operating system. You only do this once.

### Arch Linux (or Manjaro, EndeavourOS)

```bash
sudo pacman -S python python-pillow ttf-liberation
pip install piexif
```

If `pip install piexif` complains about a "externally managed environment", use:

```bash
pip install --user piexif
```

### Ubuntu / Debian / Linux Mint / Pop!_OS

```bash
sudo apt update
sudo apt install python3 python3-pip fonts-liberation
pip3 install pillow piexif
```

### Windows

1. Install Python from <https://www.python.org/downloads/>. **On the first
   screen of the installer, tick the box that says "Add Python to PATH"** before
   clicking Install — this matters.
2. Open **Command Prompt** (press Start, type `cmd`, hit Enter) and run:
   ```
   pip install pillow piexif
   ```
3. Windows already has the Arial font, but the scripts point at a Linux font by
   default. Open `geotag.py` in Notepad and change these two lines near the top:
   ```python
   FONT_BOLD = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"
   FONT_REG  = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"
   ```
   to:
   ```python
   FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
   FONT_REG  = "C:/Windows/Fonts/arial.ttf"
   ```

### macOS

1. Install Python from <https://www.python.org/downloads/> (or with Homebrew:
   `brew install python`).
2. In the **Terminal** app, run:
   ```bash
   pip3 install pillow piexif
   ```
3. Point the fonts at a macOS font. Open `geotag.py` and change the two font
   lines near the top to:
   ```python
   FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
   FONT_REG  = "/System/Library/Fonts/Supplemental/Arial.ttf"
   ```

> On Windows/macOS, if you ever type `python3` and it isn't found, try just
> `python` (and `pip` instead of `pip3`). They mean the same thing on those
> systems.

---

## Step 1 — Organize your photos into folders

This is the most important part, so read it slowly. The scripts decide each
photo's date and time **entirely from the folder it sits in**. Lay your photos
out like this:

```
Social_Internship/
├── 2026-06-24/                  ← a DATE folder
│   ├── Morning_0900/            ← an ACTIVITY folder (starts at 09:00)
│   │   ├── IMG_001.jpg
│   │   └── IMG_002.jpg
│   └── Evening_1630/            ← another activity (starts at 16:30)
│       └── IMG_010.jpg
├── 2026-06-25/
│   ├── Morning_1000/
│   └── Evening_1700/
└── ...
```

The two naming rules:

- **Date folder** must be written as **`YYYY-MM-DD`** — four-digit year, month,
  day, joined by dashes. Example: `2026-06-24`. The weekday ("Wednesday") is
  worked out from this automatically, so you never type it yourself.

- **Activity folder** can be named anything you like, as long as it **ends with an
  underscore and the start time in 24-hour `HHMM` form**. Only those last four
  digits matter. All of these are valid and start the activity at 9:00 AM:
  `Morning_0900`, `A03_LivestockFarmVisit_0900`, `TreePlanting_0900`.
  Something like `1630` means 4:30 PM.

Then drop that activity's photos inside the folder. Within one folder, photos are
ordered by their **file name**, so the natural `IMG_001, IMG_002…` order is the
order they'll be timestamped in.

You choose how many days and how many activities per day exist — the scripts just
process whatever folders they find. One day can have two activities, three, or
one; it doesn't matter.

---

## Step 2 — Set the date and time

First do a **dry run**. This only *prints* what it would do and changes nothing,
so you can check it looks right:

```bash
python3 set_datetime.py --dry-run Social_Internship
```

You'll see something like:

```
[2026-06-24/Morning_0900]  base Wed 24/06/2026 09:00 AM  (3 photos)
    IMG_001.jpg  ->  Wed 24/06/2026 09:00 AM
    IMG_002.jpg  ->  Wed 24/06/2026 09:04 AM
    IMG_003.jpg  ->  Wed 24/06/2026 09:10 AM
```

The first photo in a folder gets the folder's start time, and each photo after it
is placed **about 5 minutes later** (randomly 3–7 minutes, so the times look
natural instead of perfectly spaced). If the schedule looks right, run it for
real by removing `--dry-run`:

```bash
python3 set_datetime.py Social_Internship
```

Good to know:

- This writes the time **into the photo's metadata without re-saving the image**,
  so there is **no quality loss**.
- It edits the files **inside `Social_Internship/` in place**. Keep your untouched
  original photos somewhere else — treat the `Social_Internship/` copies as the
  working set.
- Running it again gives the **exact same times** (the randomness is fixed per
  folder), so it's safe to re-run.

---

## Step 3 — Draw the location banner

```bash
python3 geotag.py Social_Internship
```

The stamped photos are written to a new **`geotagged/`** folder that mirrors your
layout, so nothing you have is overwritten:

```
geotagged/Social_Internship/2026-06-24/Morning_0900/IMG_001.jpg
geotagged/Social_Internship/2026-06-24/Evening_1630/IMG_010.jpg
...
```

### The three ways to run geotag.py

**1. On a whole folder tree** (the normal case, shown above) — give it the
folder name and it walks everything inside:

```bash
python3 geotag.py Social_Internship
```

**2. On one or a few specific photos** — just name the files:

```bash
python3 geotag.py IMG_001.jpg
python3 geotag.py IMG_001.jpg IMG_002.jpg
```

**3. On every photo in the current folder — the `.` (dot) shortcut.** If you've
put `geotag.py` right next to a bunch of loose `.jpg` files and just want to
stamp all of them, run:

```bash
python3 geotag.py .
```

The `.` simply means **"this folder I'm currently in"**. It's handy when your
photos aren't organized into the date/activity structure and you only want to
geotag whatever is sitting here. (Running `python3 geotag.py` with nothing after
it does the same thing for the loose files in the current folder.)

> `geotag.py` never changes your originals — it always writes fresh copies into
> `geotagged/`.

---

## The usual workflow, start to finish

```bash
# 1. Arrange photos:  Social_Internship/YYYY-MM-DD/Label_HHMM/your.jpg
# 2. Preview the times
python3 set_datetime.py --dry-run Social_Internship
# 3. Apply the times
python3 set_datetime.py Social_Internship
# 4. Stamp the banners
python3 geotag.py Social_Internship
# 5. Your finished photos are in  geotagged/Social_Internship/...
```

---

## If something goes wrong

- **`error: folder not found: Social_Internship`** — you're not in the folder
  that *contains* `Social_Internship`, or you spelled it differently. Either
  `cd` into the right place, or pass the correct name/path. Folder names are
  case-sensitive on Linux/Mac (`Social internship` ≠ `Social_Internship`).

- **`command not found: python3`** (Windows/macOS) — use `python` and `pip`
  instead of `python3` and `pip3`.

- **A photo is skipped / "no GPS"** — that photo doesn't have location saved in
  it. This is common for photos sent over WhatsApp or Instagram, which strip out
  the GPS. Use the original file (transfer it by Google Drive as a file, email
  attachment, or USB cable) rather than a messaging-app copy.

- **The map looks empty in a rural area** — that's just how much OpenStreetMap
  knows about that spot. It's not a bug, and zooming in further shows *less*, not
  more.

- **Font error like "cannot open resource"** — the font path at the top of
  `geotag.py` doesn't match your system. Fix the `FONT_BOLD` / `FONT_REG` lines
  as shown in the install section for your OS.

---

## Settings you can change

Both scripts have a short list of settings at the very top of the file that you
can edit in any text editor.

**`geotag.py`:**

| Setting | What it does |
|---------|--------------|
| `SHOW_DATETIME` | Set to `False` to leave off the day/date/time line |
| `TZ_LABEL` | The timezone text after the time (default `GMT +05:30`) |
| `ZOOM` | Map zoom level (default `17`; lower shows more area) |
| `FONT_BOLD`, `FONT_REG` | Paths to the fonts (change these per OS) |
| `CONTACT` | Your email — required by OpenStreetMap's usage rules; put your own |

**`set_datetime.py`:**

| Setting | What it does |
|---------|--------------|
| `TZ` | The timezone your folder times are in (default IST, +05:30) |
| `JITTER_MIN_S`, `JITTER_MAX_S` | The min/max gap between photos, in seconds |

---

## Notes

- If an activity folder has a lot of photos, the ~5-minute gaps add up
  (12 photos ≈ 55 minutes), so leave enough room between your activity start
  times.
- Reverse-geocoding results are cached in a hidden `.geocode_cache.json` file, so
  repeated locations aren't looked up twice. Delete that file to force fresh
  lookups.
- These scripts use free OpenStreetMap services. Keep your volumes reasonable and
  put your real email in `CONTACT` if you reuse this heavily.

---

## License

Free to use and modify. If you share it, please keep a real contact email in the
`CONTACT` setting so OpenStreetMap can reach whoever is making the requests.
