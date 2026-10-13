# WrestleEdit desktop packaging

The desktop wrapper uses Electron with renderer Node integration disabled, context isolation and sandboxing enabled. ROMs are opened locally through the existing editor. Downloads use a native Save As dialog. No ROM is bundled.

The portable Windows package requires extracting the entire folder and opening `WrestleEdit.exe`. Keep the supporting files beside it. There is no installer.

To reproduce version 0.16.0, download `electron-v44.7.0-win32-x64.zip` and `SHASUMS256.txt` from the official Electron v44.7.0 release into `outputs/desktop-runtime/`, then run `python3 tools/package_desktop.py`. The script checks the runtime checksum and packages the existing standalone editor. Release binaries stay in ignored `outputs/`.

Validation: wrapper JavaScript syntax, official runtime checksums and archive contents verified; the unchanged editor passed browser workflow checks. A Linux headless Electron launch failed in this cloud environment, and the Windows executable has not been launched here. Native Windows Save As dialogs remain to be verified on Windows.

[Download the published v0.16 Windows preview](https://github.com/yourpalbones/WWF-Raw-Mod/releases/download/wrestleedit-v0.16.1/WrestleEdit-Windows-x64.zip).
GitHub Actions built and published this archive successfully. Its official
Electron runtime checksum, archive integrity and embedded editor contents
were verified. Direct release uploads from the cloud integration had previously
failed; the release workflow now handles publication.

A tag named `wrestleedit-v*` now builds the verified portable Windows package
and publishes it through GitHub Actions. The workflow uses GitHub’s supplied
release credentials. See [release notes](release-notes.md).
