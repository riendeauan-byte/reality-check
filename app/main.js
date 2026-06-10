const { app, BrowserWindow, screen, ipcMain, Tray, Menu, nativeImage } = require("electron");
const { execFile } = require("child_process");
const path = require("path");
const fs = require("fs");

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

// ---------- settings (persisted) ----------
const SETTINGS_PATH = path.join(app.getPath("userData"), "settings.json");
const DEFAULTS = {
  paused: false,
  onSocials: true, // fire when you open a social site
  periodicMinutes: 7, // also fire every N minutes (0 = off)
  position: "bottom-right", // bottom-right|bottom-left|top-right|top-left|bottom-center|center
  visitCount: 0,
};
let settings = { ...DEFAULTS };

function loadSettings() {
  try {
    settings = { ...DEFAULTS, ...JSON.parse(fs.readFileSync(SETTINGS_PATH, "utf8")) };
  } catch (_) {}
}
let saveT = null;
function saveSettings() {
  clearTimeout(saveT);
  saveT = setTimeout(() => {
    try {
      fs.mkdirSync(path.dirname(SETTINGS_PATH), { recursive: true });
      fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2));
    } catch (_) {}
  }, 150);
}

let overlay = null;
let dash = null;
let tray = null;
let prevMatch = false;
let lastFire = 0;
let isPlaying = false;
let safetyT = null;
let periodicT = null;

function activeDisplay() {
  try {
    return screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  } catch (_) {
    return screen.getPrimaryDisplay();
  }
}

// ---------- overlay (full-screen transparent layer; clip placed via CSS) ----------
function createOverlay() {
  const b = activeDisplay().bounds;
  overlay = new BrowserWindow({
    x: b.x,
    y: b.y,
    width: b.width,
    height: b.height,
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
  overlay.setAlwaysOnTop(true, "floating"); // above content, BELOW the Dock
  overlay.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true,
    skipTransformProcessType: true,
  });
  overlay.setIgnoreMouseEvents(true); // click-through
  overlay.loadFile(path.join(__dirname, "overlay.html"));
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
  if (isPlaying || !overlay || settings.paused) return;
  let clips = [];
  try {
    clips = fs.readdirSync(CLIPS_DIR).filter((f) => f.endsWith(".webm"));
  } catch (_) {}
  if (!clips.length) return;
  isPlaying = true;
  lastFire = Date.now();
  const pick = clips[Math.floor(Math.random() * clips.length)];
  const src = "file://" + path.join(CLIPS_DIR, pick);
  const b = activeDisplay().bounds;
  overlay.setBounds({ x: b.x, y: b.y, width: b.width, height: b.height });
  overlay.setAlwaysOnTop(true, "floating");
  overlay.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true,
    skipTransformProcessType: true,
  });
  let pos = settings.position;
  if (pos === "random-corners") {
    const corners = ["bottom-right", "bottom-left", "top-right", "top-left"];
    pos = corners[Math.floor(Math.random() * corners.length)];
  }
  overlay.showInactive();
  overlay.webContents.send("play", { src, position: pos });
  clearTimeout(safetyT);
  safetyT = setTimeout(() => {
    isPlaying = false;
    if (overlay) overlay.hide();
  }, 75000);
}

ipcMain.on("done", () => {
  clearTimeout(safetyT);
  isPlaying = false;
  if (overlay) overlay.hide();
});

function bumpVisit() {
  settings.visitCount++;
  saveSettings();
  pushToDash();
  updateTray();
}

function startWatcher() {
  setInterval(() => {
    chromeURL((url) => {
      const match = !!url && SITES.some((r) => r.test(url));
      const now = Date.now();
      if (match && !prevMatch) {
        bumpVisit(); // count every arrival on a social site
        if (!settings.paused && settings.onSocials && now - lastFire > COOLDOWN_MS) {
          lastFire = now;
          fire();
        }
      }
      prevMatch = match;
    });
  }, POLL_MS);
}

function restartPeriodic() {
  clearInterval(periodicT);
  periodicT = null;
  const m = Number(settings.periodicMinutes) || 0;
  if (m > 0) {
    periodicT = setInterval(() => {
      if (!settings.paused) fire();
    }, m * 60000);
  }
}

// ---------- dashboard window ----------
function openDashboard() {
  if (dash) {
    dash.show();
    dash.focus();
    return;
  }
  dash = new BrowserWindow({
    width: 340,
    height: 470,
    resizable: false,
    fullscreenable: false,
    title: "Reality Check",
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  });
  dash.loadFile(path.join(__dirname, "dashboard.html"));
  dash.on("closed", () => {
    dash = null;
  });
}
function pushToDash() {
  if (dash) dash.webContents.send("settings", settings);
}

ipcMain.on("get-settings", (e) => e.reply("settings", settings));
ipcMain.on("set-settings", (e, patch) => {
  settings = { ...settings, ...patch };
  saveSettings();
  restartPeriodic();
  updateTray();
  pushToDash();
});
ipcMain.on("reset-count", () => {
  settings.visitCount = 0;
  saveSettings();
  pushToDash();
  updateTray();
});
ipcMain.on("preview", () => fire());

// ---------- tray (menu bar) ----------
function trayImage() {
  const img = nativeImage.createFromPath(path.join(__dirname, "trayTemplate.png"));
  img.setTemplateImage(true);
  return img;
}
function updateTray() {
  if (!tray) return;
  const menu = Menu.buildFromTemplate([
    { label: "Settings…", click: openDashboard },
    { label: "Play a clip now", click: () => fire() },
    { type: "separator" },
    {
      label: settings.paused ? "Resume" : "Pause",
      click: () => {
        settings.paused = !settings.paused;
        saveSettings();
        updateTray();
        pushToDash();
      },
    },
    { type: "separator" },
    { label: `Social visits: ${settings.visitCount}`, enabled: false },
    { type: "separator" },
    { label: "Quit", click: () => app.exit(0) },
  ]);
  tray.setContextMenu(menu);
  tray.setToolTip(settings.paused ? "Reality Check (paused)" : "Reality Check");
}
function createTray() {
  tray = new Tray(trayImage());
  tray.on("click", openDashboard);
  updateTray();
}

app.whenReady().then(() => {
  if (app.dock) app.dock.hide();
  loadSettings();
  createOverlay();
  createTray();
  startWatcher();
  restartPeriodic();
  if (process.env.RC_DASH) openDashboard(); // RC_DASH=1 -> open dashboard (testing)
  if (process.env.RC_TEST) setTimeout(fire, 1500); // RC_TEST=1 -> play once
});

app.on("window-all-closed", (e) => e.preventDefault()); // stay resident
