"""Per-album settings. Copy to the album folder as album_config.py and fill in as the work goes on.

Photo numbers (#) are the numbers fetch_album.py gives (camera-time order). Plan page "no" = the editor's page
number - 1 (Lupa counts its opening-words page as page 1). Every value below is an example: replace or empty it.
"""

# ---- language and company -------------------------------------------------------------------------------
LANG = "he"  # page titles, map labels, facts: "he" (Hebrew) or "en" (English). The book reads right to left.
COMPANY = "Lupa"  # the album maker; Lupa gets the automated editor route, others get print files + guided upload
BOOK_PAGES = None  # fixed page count; None = the natural length rounded up to BOOK_PAGE_STEP
BOOK_MIN_PAGES = 24  # product minimum
BOOK_MAX_PAGES = 100  # product maximum (Lupa Dutch book: 100)
BOOK_PAGE_STEP = 4  # pages are added in steps of this

# ---- sections = places, in trip order -----------------------------------------------------------------------
# (id, page title in LANG, English name, keywords matched in the reviewers' "place" text; the longest match wins)
SECTIONS: list[tuple[str, str, str, list[str]]] = [
    ("S01", "יוצאים לדרך", "Departure", ["home", "airport", "flight"]),
    ("S02", "רומא", "Rome", ["rome", "colosseum"]),
    ("S03", "Amalfi Coast", "Amalfi Coast", ["amalfi", "positano"]),
    ("S04", "חוזרים הביתה", "Home", []),
]
FORCE_SECTION: dict[int, str] = {}  # photo # -> section id, when the keywords put a photo in the wrong place

# ---- opening pages ---------------------------------------------------------------------------------------
COVER = 0  # photo # for the cover (one family photo in big scenery)
COVER_ONLY = True  # the cover photo is on the cover only; inside: opening words, map, departure
DEPARTURE: list[int] = []  # leaving-home photos (dog goodbye, airport, plane)
OPENING_AFTER_DEPARTURE = True
INTRO_PHOTOS: list[int] = []  # "home on wheels" / trip-base intro spread (the one planned exception to time order)
INTRO_BRING_BACK: dict[int, str] = {}
INTRO_AFTER = "S02"  # the intro spread comes right after this section
INTRO_TITLE_HE = ""  # its page title (LANG)
INTRO_TEXT_HE = ""
INTRO_TEXT_BOX = False
OPENING_PHOTO = None  # photo # (or a dict with n/x/y/w/h cm) on the opening-words page
OPENING_PHOTOS: list[dict] = []
OPENING_TITLE_HE = ""
OPENING_TEXT_HE = ""
OPENING_SIGN_HE = ""
OPENING_TEXT_SHOW = True
OPENING_BG = None  # faded photo behind the opening-words page (file in ready/upload)
OPENING_BLANK = False
CLOSING_TITLE_HE = ""  # last page header (e.g. "מילות סיום..." / "Closing words")

# ---- cover (make_cover_photo.py + make_cover_title.py) ------------------------------------------------------
COVER_TITLE_HE = "Our trip"  # first line of the cover title (any language)
COVER_SUB_HE = "2026"  # second line, half size
COVER_SRC = ""  # full-size cover photo (or the user's RAW export)
COVER_RATIO = 3900 / 2860  # the editor's cover photo shape (Lupa Panoramic Large)
COVER_LEFT = None  # px cut on the left (None = evenly from both sides); move so the sky lands under the title
COVER_PEOPLE = (0.30, 0.52, 0.80, 1.02)  # where the people are (fractions): their shadows get lifted
COVER_SKY = (1.55, 0.86, 1.25)  # sky saturation, deepen, cloud contrast (1, 1, 1 = untouched)
COVER_TITLE_CX = 1450  # title centre on the cover sheet (px): on the sky, off faces and peaks
COVER_TITLE_FONT = 207
COVER_IMAGE = "ready/upload/000_cover_title.jpg"  # shown on the plan
BACK_COVER_IMAGE = None
COVER_NOTE = "The cover photo fills the front cover; the title is drawn into the photo, on the sky."

# ---- photo choices (review rounds) -------------------------------------------------------------------------
REPLACE: dict[int, int] = {}  # photo in the book -> replacement photo
FORCE_OUT: dict[int, str] = {}  # photo -> reason shown in the plan
FORCE_KEEP: set[int] = set()
FORCE_HERO: set[int] = set()  # full page
NO_HERO: set[int] = set()
SPREAD_FORCE: set[int] = set()  # double-page spread (drone shots, panoramas)
NOTES: dict[int, str] = {}  # notes shown on a photo in the plan
SWAPS: list[tuple[int, int]] = []  # applied in order, after layout
FILL_PICKS: list[int] = []
BIGGER: list[tuple[int, int]] = []  # (a, b): a gets the bigger frame
SAME_SIZE: list[tuple[int, int]] = []
PAGE_MAX: dict[str, int] = {}  # section -> max photos per page
ORDER_BEFORE: dict[int, int] = {}  # photo a goes right before photo b (story exceptions; never fake times)
CLOCK_FIXES: list[dict] = []  # [{"mp": 17.9, "tz_hours": 8, "shift_hours": 5}] wrong camera clocks
ORDER_NOTE = ", with wrong camera clocks fixed"
LOCK_FILE = ""  # "plan_locked.json" once the user approved the book: no automatic reshuffles after that
TEXT_HALF: dict = {}  # section -> {"photos": [...], "title": "", "text": ""}: half a spread of text
SPREAD_3_PLACES = True
STORE_KEY = "album-marks-r1"  # change every review round, so old marks don't come back

# ---- print tuning (prepare_originals.py) -------------------------------------------------------------------
# photo -> extra fixes: "shadows" 0-160 (+ "region" x0,y0,x1,y1), "bright"/"contrast"/"sat" %, "rotate" degrees
EXTRA_TUNE: dict[int, dict] = {}

# ---- page headers ------------------------------------------------------------------------------------------
HIDDEN_TITLES: dict[int, list[str]] = {}  # plan page no -> sections whose header is removed
EXTRA_TITLES: dict[int, str] = {}  # plan page no -> extra header text
TITLE_BOTTOM: set[int] = set()  # headers at the page bottom
TITLE_SCALE: dict[int, float] = {}  # smaller header (e.g. to fit beside a QR)
HERO_TITLE_PAGES: set[int] = set()  # full-page photos that keep their section header

# ---- backgrounds -------------------------------------------------------------------------------------------
BG_TEXTURES: dict[int, int] = {}  # editor spread index -> photo used as a full-spread background
BG_TEXTURE_FADE: dict[int, float] = {}  # spread -> 0.2 = 20% lighter
BG_TEXTURE_SOFTEN = 0.0

# ---- route map (make_map.py) -------------------------------------------------------------------------------
# (number, label in LANG, dates, lat, lng, label side l/r/t/b/n) — coordinates from the photos' own locations
STOPS: list[tuple] = []
ROUTE: list[tuple[float, float]] = []  # driving waypoints in trip order
NUDGE: dict[int, tuple[int, int]] = {}
SIDE_TRIP: list[tuple[float, float]] = []  # dashed line (flight, boat)
SIDE_TRIP_LABEL = ""
MAP_TITLE = ""  # default "המסלול שלנו" / "Our route"
MAP_SUBTITLE = ""
MAP_NOTE = ""
ROUTE_MILES_ACTUAL = None  # odometer / rental bill, when known
STATE_LABEL_AT: dict[str, tuple[float, float]] = {}  # US trips: move a state's name

# ---- QR codes (make_qr.py; rules in references/qr-rules.md) -------------------------------------------------
# page = plan page no; x/y = top-left and s = size, in cm on that 30x22 page; bg = page colour under the code;
# t = a unique EXIF second. Never straddle a photo's edge: fully on background, or fully inside one photo.
QR_CODES: list[dict] = [
    # {"file": "ready/upload/qr_2026-05-02_rome.jpg", "src": "qr-codes/2026-05-02_rome.jpg", "bg": (246, 243, 236),
    #  "t": 41, "page": 12, "x": 0.6, "y": 18.9, "s": 2.34, "note": "Rome videos - bottom-left margin"},
]
QR_DEFAULT_BG = (246, 243, 236)

# ---- plan page -----------------------------------------------------------------------------------------------
ALBUM_TAB_TITLE = "Album plan"
ALBUM_TITLE = "Our trip · album plan"
ALBUM_LINE = "Shared Google album · dates"
OUTPUT_HTML = "album-plan.html"
PRODUCT_HTML = ""  # recommended book + price table (HTML card); "__ROOM__" = number of photos that fit
THEMES: list[tuple] = []  # (key, name, English name, tag, why, [sample images in themes/])
THEME_NOTE = "Check in the album editor that the theme works with your chosen book and size before you start."
EMO: dict[str, str] = {}  # optional: one cartoon symbol per section (Noto emoji code point); off by default
TRIP_FACTS: list[tuple[str, str]] = []  # (fact in LANG, source) from the family's trip documents
