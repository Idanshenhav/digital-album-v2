# First run: setup checks (Cowork, Claude Code, any computer)

Run once per computer, in the album folder, before stage 4. Fix what fails, using the fallback.

1. **Python packages** (Pillow, numpy, OpenCV, qrcode):
   """
   python3 -m pip install -r <skill>/requirements.txt
   """
   If pip is blocked, try `pip install --user …`. OpenCV is only needed for the QR scan check.
2. **A headless browser** draws titles, the map labels, full pages and the cover title (Hebrew and bold fonts
   need a real browser):
   """
   python3 -c "import sys; sys.path.insert(0, '<skill>/scripts'); import chrome; print(chrome.CHROME)"
   """
   If it prints "chrome-not-found": `python3 -m pip install playwright && python3 -m playwright install chromium`,
   then check again. If downloads are blocked, set `CHROME=/path/to/chrome`, or run the drawing steps on a computer
   with Chrome and copy the `ready/` folder back.
3. **Network**: the scripts download from Google Photos (lh3.googleusercontent.com), map tiles
   (server.arcgisonline.com), routes (router.project-osrm.org), US state borders (cdn.jsdelivr.net) and Lupa theme
   pictures (assets.lupa.co.il). Test with `curl -sI https://router.project-osrm.org`. If one is blocked, ask the
   user to allow it in the app's network settings.
4. **Browser control**: the Claude in Chrome extension must be connected (it drives the album editor, reads photo
   locations and uploads files). Uploading needs the files in a folder Claude can read: keep the album folder
   inside the folder the user shared with Claude.
5. **Fonts**: Hebrew titles need a Hebrew font in the headless browser. Draw a test title
   (`lupa_titles.render_text("בדיקה", 61, "dark", False)`) and look at it.

Work folder: one folder per album (the user picks it). Copy `scripts/*` and `assets/plan.*` into it and run the
scripts from there; they read `album_config.py` from the current folder.
