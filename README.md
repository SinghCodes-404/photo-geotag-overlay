<img width="3072" height="4096" alt="IMG20260625174728" src="https://github.com/user-attachments/assets/10ad8546-d7fb-4717-bb0d-af21388e5682" /># Geotag Photos — Location Banner Overlay

`geotag.py` burns a **GPS Map Camera–style location banner** onto the bottom of
geotagged photos. For each image it reads the GPS coordinates from EXIF,
reverse-geocodes them to a place name and address, fetches an OpenStreetMap
thumbnail, and composites a banner:

Compare the given two images in the repository. 

IMG20260625174728.jpg Vs 
IMG20260625174728-geotagged.jpg

**Location only** — no time or date is written to the banner.

---

## Requirements

- **Python 3** with **Pillow** (`PIL`) — everything else uses the standard library.
  ```bash
  pip install pillow
  ```
- **Fonts**: Liberation Sans (Bold + Regular). Pre-installed on most Linux
  distros. If missing:
  ```bash
  # Debian/Ubuntu
  sudo apt install fonts-liberation
  # Arch
  sudo pacman -S ttf-liberation
  ```
  On a different OS, edit `FONT_BOLD` / `FONT_REG` near the top of `geotag.py`
  to point at any bold/regular TTF (e.g. DejaVu Sans, Arial).
- **Internet access** — needed to reach OpenStreetMap for reverse geocoding
  and map tiles.

The photos must contain **GPS EXIF data**. Images without it are skipped with a
warning (the script never fails the whole run over one bad file).

---

## Usage

Run from the folder that contains the photos.

```bash
# Process every *.jpg in the current folder
python3 geotag.py

# Process one or more specific files
python3 geotag.py IMG20260625174721.jpg IMG20260625180726.jpg
```

Output is written to **`./geotagged/`** using the original filenames. Your
original photos are never modified.

Example run:

```
[IMG20260625174721.jpg]
  ✓ IMG20260625174721.jpg  ->  Nanowal Khurd, Punjab, India
...
Done: 45/45 images written to geotagged/
```

---

## How it works

| Step | Source / tool |
|------|---------------|
| Read GPS from EXIF | Pillow (`_getexif` → GPS tags → decimal degrees) |
| Place name + address | **Nominatim / OpenStreetMap** reverse geocoding |
| Map thumbnail | **OpenStreetMap tiles**, stitched and cropped around the point, with a pin |
| Banner compositing | Pillow (gradient shade + Liberation Sans text) |

- **Title** = locality (village/town/city) + state + country.
- **Address** = Nominatim's full `display_name`, wrapped to the banner width.
- **Coordinates** come straight from each photo's EXIF.

### Caching & rate limits
- Reverse-geocode results are cached in **`.geocode_cache.json`** (keyed by
  rounded coordinates), so photos from the same spot only hit the network once.
- Nominatim is polled at **1 request/second** to respect its
  [usage policy](https://operations.osmfoundation.org/policies/nominatim/).
  Expect roughly 1–2 minutes for a few dozen new locations; cached repeats are
  instant.
- Delete `.geocode_cache.json` to force fresh lookups.

---

## Configuration

Tunable constants are at the top of `geotag.py`:

| Constant | Meaning |
|----------|---------|
| `OUT_DIR` | Output folder (default `geotagged`) |
| `ZOOM` | Map zoom level (default `17`; higher = tighter, lower = more area/context) |
| `CONTACT` / `UA` | Contact email + User-Agent sent to OSM (required by policy) |
| `MARGIN_F` | Banner / map margin, as a fraction of image width |
| `MAP_F` | Map square size, as a fraction of image height |
| `TITLE_F`, `BODY_F` | Title / body font size, as a fraction of image height |
| `GAP_F` | Line spacing, as a fraction of image height |
| `FONT_BOLD`, `FONT_REG` | Paths to the TTF fonts used |

All layout values are fractions of the image dimensions, so the banner scales
consistently across different photo sizes.

---

## Notes & limitations

- **Rural areas look sparse** on the map — OpenStreetMap simply has little data
  there. Zooming in further shows *less* context, not more.
- Displayed coordinates are read directly from EXIF, so they may differ by a few
  metres from other apps that rewrite the GPS values.
- Uses free, no-API-key OpenStreetMap services. Please keep volumes reasonable
  and set a real `CONTACT` email in the script if you fork it for heavy use.
