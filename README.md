# Reality Check

A desktop pattern-interrupt for doomscrolling. When you open Instagram, YouTube, TikTok, X, Reddit, or Facebook in Chrome, a short video clip slides into a corner, plays once with sound, and slides away. It can also fire on a timer. A menu-bar dashboard controls everything: pause, the timer (on or off, and how often), where it appears, whether it shows when you open socials, whether it stays quiet while you are on a call, and a counter of how many times you have opened a social site. macOS only.

The clip plays with a transparent background (a cut-out, not a box) in a click-through, always-on-top overlay, so it never steals focus or blocks your clicks. It picks at random and will not replay a clip it has shown in the last 20 fires, so you do not get the same one twice in a row.

## Requirements

- macOS
- Node.js (for the overlay app)
- Google Chrome (the watched browser)
- Optional, for the "pause during camera or mic use" feature: Xcode Command Line Tools (the installer uses `swiftc` to build a tiny detector). Without it, that one feature stays off and everything else works.
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
3. The repo includes a set of ready-to-use clips in `clips/`. You can add your own too (see "Add clips").
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

Note on CapCut: CapCut cannot export a truly transparent video. Its MP4/MOV export bakes the removed area to solid black. Put your subject on a solid green (or magenta) background and export normally, then use `--green` or the batch script. The keyer removes only that one solid color and leaves the subject untouched. Clips come out at 360p, 24fps, which keeps them small.

## Dashboard

Click the eye icon in the menu bar to open the dashboard (or pick Settings from its menu). The big round button is play/pause: pausing stops a clip that is on screen right away. From the dashboard you can also:
- See how many times you have opened a social site, with a reset.
- Play a clip now.
- Toggle whether it shows when you open a social site.
- Toggle "pause during camera or mic use" so it stays quiet on calls (on by default).
- Turn the timer on or off, and set how often it fires (minutes). Turning it off keeps your interval for next time.
- Pick the position: any corner, bottom-center, center, or random corners. Top corners slide in from the top.

Settings are saved automatically and survive restarts.

## How it works

- A watcher inside the Electron process asks Chrome for its active tab URL once a second.
- When you arrive on a watched site it fires, with a 60-second cooldown so it nudges rather than spams. The timer fires it too when turned on.
- Each fire picks a random clip (skipping the last 20 played), moves the overlay to the display your cursor is on, and plays it at your chosen position. The window is frameless, transparent, always-on-top, and click-through.
- A small Swift helper reads the system camera and mic "in use" state. While either is active (any app: Zoom, Meet, FaceTime, and so on), nothing fires and a clip already on screen stops at once. It reads the in-use flag only, so it needs no camera or mic permission.
- A launchd LaunchAgent keeps it alive and starts it at login.

## Configure

Most settings live in the dashboard (pause, timer on/off and interval, position, socials toggle, camera/mic pause, visit count) and persist across restarts. Advanced bits stay in the source:
- `app/main.js` `SITES`: the trigger domains. `COOLDOWN_MS`: minimum gap between site triggers. `NO_REPEAT`: how many recent clips to skip.
- `app/overlay.html`: clip display `width`, slide `transition` duration, `FADE` and `FLOOR` (the audio fades in from `FLOOR`, not from silence).
- `prep/make_lean.py`: clip output size and rate (`MAX_W` 360, `FPS` 24) and the key tightness.

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
- Clips in `clips/` are included with the project. You can add or replace them with your own at any time.

## License

MIT. See [LICENSE](LICENSE).
