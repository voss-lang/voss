# Voss ADE — platform packaging metadata

Packaging notes for manual verification of UXP-28..30 platform-native metadata. This directory is not user-facing application documentation.

## Icon bundle (`../icons/`)

Required paths referenced by `tauri.conf.json`:

| File | Status |
|------|--------|
| `icons/32x32.png` | Required for Linux/Windows tray and launcher sizes |
| `icons/128x128.png` | Required for Linux hi-DPI launcher |
| `icons/128x128@2x.png` | Required for macOS Retina |
| `icons/icon.icns` | Required for macOS `.app` / DMG |
| `icons/icon.ico` | Required for Windows taskbar and installer |

Regenerate with `pnpm tauri icon <source-png>` from `apps/voss-app` when branding changes.

## Linux (UXP-30)

- **Desktop entry:** `voss-ade.desktop` is a Handlebars template used by `bundle.linux.deb.desktopTemplate` and `bundle.linux.rpm.desktopTemplate`. Tauri substitutes `{{name}}`, `{{exec}}`, and `{{icon}}` at bundle time.
- **Categories:** `Development;TerminalEmulator` (hardcoded in template).
- **WM_CLASS / GTK app ID:** `app.enableGTKAppId` is `true`, so the GTK application ID matches `identifier` (`app.voss-ade`). The desktop entry sets `StartupWMClass=app.voss-ade` for window-manager grouping.

### Manual verification (Linux)

1. Build a `.deb` or run from a Linux host: `pnpm tauri build` in `apps/voss-app`.
2. Install the package or inspect `target/release/bundle/deb/*/data/usr/share/applications/*.desktop`.
3. Confirm `Name=Voss ADE`, `Categories=Development;TerminalEmulator`, and `StartupWMClass=app.voss-ade`.
4. Launch from the app menu; run `xprop WM_CLASS` on the window — class should align with `app.voss-ade`.
5. Confirm no system tray icon appears (tray UI is intentionally not enabled).

## Windows (UXP-29)

- **Taskbar identity:** `productName` (`Voss ADE`), `identifier` (`app.voss-ade`), and `icons/icon.ico` drive installer and taskbar labeling.
- **Window title:** `app.windows[].title` is `Voss ADE`.

### Manual verification (Windows)

1. Build NSIS/MSI bundle on Windows or inspect CI artifacts.
2. Pin the app to the taskbar; tooltip and icon should read **Voss ADE**.
3. Confirm no notification-area tray icon is shown.

## macOS (UXP-28)

- **Bundle name:** `productName` (`Voss ADE`) and `icons/icon.icns` feed the `.app` bundle.
- **Window title:** `app.windows[].title` is `Voss ADE`.
- **Signing:** `bundle.macOS.signingIdentity` is unset for local/dev builds.

### Manual verification (macOS)

1. Build `.app` / DMG: `pnpm tauri build` in `apps/voss-app`.
2. Inspect `Voss ADE.app/Contents/Info.plist` — `CFBundleName` / display name should be **Voss ADE**.
3. Dock and menu bar should show **Voss ADE**; no menu-bar status-item tray UI.

## Constraints

- Packaging metadata only — no in-app tray or status-bar UI.
- Product name must remain **Voss ADE** across all platforms.
