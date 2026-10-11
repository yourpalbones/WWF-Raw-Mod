# WrestleEdit desktop packaging

The desktop wrapper uses Electron with renderer Node integration disabled, context isolation and sandboxing enabled. ROMs are opened locally through the existing editor. Downloads use a native Save As dialog. No ROM is bundled.

The portable Windows package requires extracting the entire folder and opening `WrestleEdit.exe`. Keep the supporting files beside it. There is no installer.

To reproduce version 0.1.0, download `electron-v44.7.0-win32-x64.zip` and `SHASUMS256.txt` from the official Electron v44.7.0 release into `outputs/desktop-runtime/`, then run `python3 tools/package_desktop.py`. The script checks the runtime checksum and packages the existing standalone editor. Release binaries stay in ignored `outputs/`.

Validation: wrapper JavaScript syntax, official runtime checksums and archive contents verified; the unchanged editor passed browser workflow checks. A Linux headless Electron launch failed in this cloud environment, and the Windows executable has not been launched here. Native Windows Save As dialogs remain to be verified on Windows.

Public release upload was attempted but rejected with HTTP 401 by the GitHub upload endpoint. Git pushes continue to work; no release download is advertised until assets can be published.
