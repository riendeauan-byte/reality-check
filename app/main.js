const { app, BrowserWindow, screen, ipcMain } = require("electron");
const { execFile } = require("child_process");
const path = require("path");
const fs = require("fs");
const os = require("os");

const CLIPS_DIR = path.join(__dirname, "..", "clips"); // <repo>/clips

// Domains that trigger the nudge.
const SITES = [
  /instagram\.com/i,
  /youtube\.com/i,
  /tiktok\.com/i,
  /\bx\.com/i,
  /twitter\.com/i,
  /reddit\.com/i,
  /facebook\.com/i,
];

const POLL_MS = 1000;
const COOLDOWN_MS = 60000; // don't re-fire within 60s of arriving
const PERIODIC_MS = 7 * 60 * 1000; // also show one every 7 minutes

const WIN_W = 380;
const WIN_H = 640;

let win = null;
let prevMatch = false;
let lastFire = 0;
let isPlaying = false;
let safetyT = null;

function createWindow() {
  const { bounds } = screen.getPrimaryDisplay(); // full screen incl. under the Dock
  win = new BrowserWindow({
    width: WIN_W,
    height: WIN_H,
    x: bounds.x + bounds.width - WIN_W,
    y: bounds.y + bounds.height - WIN_H,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    movable: false,
    focusable: false,
    hasShadow: false,
    fullscreenable: false,
    enableLargerThanScreen: true, // allow the window into the Dock's region
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      autoplayPolicy: "no-user-gesture-required",
    },
  });

  win.setAlwaysOnTop(true, "floating"); // above content, BELOW the Dock
  win.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true,
    skipTransformProcessType: true,
  });
  win.setIgnoreMouseEvents(true); // click-through: never steals clicks
  win.loadFile(path.join(__dirname, "overlay.html"));
}

// Ask Chrome for the active tab URL. `is running` does NOT launch Chrome.
function chromeURL(cb) {
  execFile(
    "osascript",
    [
      "-e", 'if application "Google Chrome" is not running then return ""',
      "-e", 'tell application "Google Chrome"',
      "-e", "if (count of windows) = 0 then return \"\"",
      "-e", "return URL of active tab of front window",
      "-e", "end tell",
    ],
    { timeout: 2500 },
    (err, stdout) => cb(err ? "" : (stdout || "").trim())
  );
}

function fire() {
  if (isPlaying || !win) return; // don't interrupt a clip already playing
  let clips = [];
  try {
    clips = fs.readdirSync(CLIPS_DIR).filter((f) => f.endsWith(".webm"));
  } catch (_) {}
  if (!clips.length) return;
  isPlaying = true;
  lastFire = Date.now();
  const pick = clips[Math.floor(Math.random() * clips.length)];
  const src = "file://" + path.join(CLIPS_DIR, pick);
  // show on whichever display is active (cursor's screen), flush bottom-right
  try {
    const b = screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).bounds;
    win.setBounds({
      x: b.x + b.width - WIN_W,
      y: b.y + b.height - WIN_H,
      width: WIN_W,
      height: WIN_H,
    });
  } catch (_) {}
  win.setAlwaysOnTop(true, "floating"); // above content, BELOW the Dock
  win.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true,
    skipTransformProcessType: true,
  });
  win.showInactive();
  win.webContents.send("play", src);
  // safety: release the lock if 'done' never arrives (renderer hiccup)
  clearTimeout(safetyT);
  safetyT = setTimeout(() => {
    isPlaying = false;
    if (win) win.hide();
  }, 75000);
}

function startWatcher() {
  setInterval(() => {
    chromeURL((url) => {
      const match = !!url && SITES.some((r) => r.test(url));
      const now = Date.now();
      if (match && !prevMatch && now - lastFire > COOLDOWN_MS) {
        lastFire = now;
        fire();
      }
      prevMatch = match;
    });
  }, POLL_MS);
}

ipcMain.on("done", () => {
  clearTimeout(safetyT);
  isPlaying = false;
  if (win) win.hide();
});

app.whenReady().then(() => {
  if (app.dock) app.dock.hide();
  createWindow();
  startWatcher();
  setInterval(fire, PERIODIC_MS); // show one every 5 minutes regardless
  if (process.env.RC_TEST) setTimeout(fire, 1500); // RC_TEST=1 -> play once immediately
});

app.on("window-all-closed", (e) => e.preventDefault()); // stay resident
