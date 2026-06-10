# Reality Check

A desktop pattern-interrupt for doomscrolling. When you open Instagram, YouTube, TikTok, X, Reddit, or Facebook in Chrome, a short video clip slides up in the bottom-right corner, plays once with sound, and slides away. It also fires once every few minutes on its own. A menu-bar dashboard controls everything: pause, frequency, position, the socials toggle, and a counter of how many times you have opened a social site. macOS only.

The clip plays with a transparent background (a cut-out, not a box) in a click-through, always-on-top overlay, so it never steals focus or blocks your clicks.

## Requirements

- macOS
- Node.js (for the overlay app)
- Google Chrome (the watched browser)
- Optional, only for the clip-prep scripts: ffmpeg, yt-dlp, Python 3

## Install

1. Clone and enter:
   ```
   git clone https://github.com/riendeauan-byte/reality-check.git
   cd reality-check
   ```
2. Install the app:
   ```
   cd app && npm install && cd ..
   ```
3. Add at least one clip (see "Add clips"). The repo ships with none on purpose.
4. Start it, and have it launch at login:
   ```
   ./install-autostart.sh
   ```
5. The first time you open a watched site, macOS asks to let it control Chrome. Click Allow. That is how it reads the active tab. Until you allow it, nothing fires.

To run once in the foreground for testing instead of installing: `./start.sh`

## Add clips

Clips live in `clips/` as transparent WebM (VP9 with alpha). Drop in any number. One is picked at random each time it fires. Three ways to make them, all local and free:

1. You already have a clip with a transparent or green background:
   ```
   ./import_clip.sh /path/to/clip.mov            # already transparent (alpha)
   ./import_clip.sh /path/to/clip.mp4 --green    # subject on a green screen
   ```
   Converts it to the WebM the overlay needs and drops it in `clips/`.

2. A batch of green-screen renders in a `manual renders/` folder:
   ```
   ./prep/make_lean.sh
   ```
   Keys out the green, auto-crops to the subject, scales down, and writes one
   compact clip per file. It samples a few frames per clip instead of dumping
   full frame sequences, so it stays light on disk even for a large batch.

3. Auto-remove the background straight from YouTube clips:
   ```
   ./prep/make_clips.sh "<youtube-url>" "<youtube-url>"
   ```
   Downloads, segments the person, writes transparent clips.

Options 2 and 3 need a small Python environment:
```
python3 -m venv prep/venv
prep/venv/bin/pip install rembg pillow onnxruntime scipy
```

Note on CapCut: CapCut cannot export a truly transparent video. Its MP4/MOV export bakes the removed area to solid black. Put your subject on a solid green background and export normally, then use `--green`.

## Dashboard

Click the eye icon in the menu bar to open the dashboard (or pick Settings from its menu). From there you can:
- Pause or resume.
- See how many times you have opened a social site, with a reset.
- Play a clip now.
- Set how often it also fires on a timer (minutes, 0 turns the timer off).
- Pick the position: any corner, bottom-center, center, or random corners.
- Toggle whether it shows when you open a social site.

Settings are saved automatically and survive restarts.

## How it works

- A watcher inside the Electron process asks Chrome for its active tab URL once a second.
- When you arrive on a watched site it fires, with a 60-second cooldown so it nudges rather than spams. A timer fires it too.
- Each fire picks a random clip, moves the overlay to the display your cursor is on, and plays it. The window is frameless, transparent, always-on-top, and click-through, pinned to the bottom-right.
- A launchd LaunchAgent keeps it alive and starts it at login.

## Configure

Most settings live in the dashboard (pause, frequency, position, socials toggle, visit count) and persist across restarts. Advanced bits stay in the source:
- `app/main.js` `SITES`: the trigger domains. `COOLDOWN_MS`: minimum gap between site triggers.
- `app/overlay.html`: clip `width`, slide `transition` duration, `FADE` (audio fade-in).

After editing source, reload:
```
launchctl kickstart -k "gui/$(id -u)/com.realitycheck.agent"
```

## Uninstall

```
./uninstall.sh
```
Stops it, removes the login agent, leaves your clips in place.

## Notes and limits

- Watches Chrome only by default. To watch another browser, edit `chromeURL` in `app/main.js` (swap the AppleScript app name).
- It cannot draw over another app's native macOS fullscreen (its own Space). That is an OS limitation. Normal windows and browsing are always covered.
- Bring your own clips. None are shipped, to avoid redistributing copyrighted video.

## License

MIT. See [LICENSE](LICENSE).
