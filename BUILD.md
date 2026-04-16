# Building MPC RandoKitter

This document explains how to build standalone executables of MPC RandoKitter for distribution.

## Overview

MPC RandoKitter can be built as a standalone application that doesn't require Python or any dependencies to be installed. This is achieved using PyInstaller.

## Quick Start

### macOS or Linux

```bash
# Install build dependencies
pip install -r requirements-build.txt

# Build
./build.sh

# Output will be in dist/
# macOS: dist/MPC_RandoKitter.app
# Linux: dist/MPC_RandoKitter
```

## Prerequisites

### All Platforms

- Python 3.7 or later
- pip (Python package installer)

### Optional

- Git (for cloning the repository)
- `create-dmg` (macOS only, for creating DMG installers)

## Installation of Build Tools

### 1. Install Python Dependencies

```bash
# Install runtime requirements
pip install -r requirements.txt

# Install build requirements
pip install -r requirements-build.txt
```

This will install:
- `customtkinter` - Modern UI
- `pyinstaller` - Application bundler

### 2. Verify Installation

```bash
python3 --version     # Should be 3.7+
pyinstaller --version # Should be 5.0+
```

## Building

### Automated Build (Recommended)

Use the provided build script:

```bash
# Build for current platform
./build.sh

# Clean build artifacts
./build.sh clean

# Clean and rebuild
./build.sh rebuild
```

### Manual Build

```bash
# Clean previous builds
rm -rf build dist

# Run PyInstaller
pyinstaller MPC_RandoKitter.spec

# Executable will be in dist/
```

## Build Output

### macOS

```
dist/
└── MPC_RandoKitter.app/          # macOS application bundle
    ├── Contents/
    │   ├── MacOS/
    │   │   └── MPC_RandoKitter    # Executable
    │   ├── Resources/
    │   └── Info.plist
```

**Size:** ~15-30 MB (smaller than M8_KitCreator because RandoKitter has no audio-processing dependencies)

**To run:**
```bash
open dist/MPC_RandoKitter.app
```

**To create DMG:**
```bash
# Install create-dmg (if not installed)
brew install create-dmg

# Create DMG
create-dmg \
  --volname "MPC RandoKitter" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  dist/MPC_RandoKitter.dmg \
  dist/MPC_RandoKitter.app
```

### Linux

```
dist/
└── MPC_RandoKitter              # Single executable file
```

**Size:** ~15-30 MB (smaller than M8_KitCreator because RandoKitter has no audio-processing dependencies)

**To run:**
```bash
chmod +x dist/MPC_RandoKitter
./dist/MPC_RandoKitter
```

**To create portable archive:**
```bash
cd dist
tar -czf MPC_RandoKitter-linux-$(uname -m).tar.gz MPC_RandoKitter
```

## What Gets Bundled

The standalone executable includes:

- Python runtime
- All Python packages (customtkinter, etc.)
- Application code
- CustomTkinter themes and assets

**Users don't need to install:**
- Python
- pip
- customtkinter

## Troubleshooting

### "ModuleNotFoundError: No module named 'X'"

**Solution:** Add missing module to `hiddenimports` in `MPC_RandoKitter.spec`:

```python
hiddenimports = [
    # ... existing imports ...
    'missing_module_name',
]
```

### Application too large

The bundled app is relatively small (~15-30MB) because it only bundles Python and the CustomTkinter UI library. If your build is larger than expected, consider:

1. **Enable UPX compression**:
   ```python
   # In MPC_RandoKitter.spec
   upx=True,
   ```
   Note: May cause issues on some systems

2. **Directory mode instead of one-file**:
   - Faster startup
   - Easier debugging
   - Slightly smaller total size

### macOS "App is damaged" error

**Cause:** macOS Gatekeeper blocking unsigned apps

**Solution:** Sign the application (requires Apple Developer account):

```bash
# Sign the app
codesign --deep --force --sign "Developer ID Application: Your Name" \
  dist/MPC_RandoKitter.app

# Notarize with Apple
xcrun notarytool submit dist/MPC_RandoKitter.dmg \
  --apple-id "your@email.com" \
  --team-id "TEAM_ID" \
  --password "app-specific-password" \
  --wait
```

**Temporary workaround** (for testing):
```bash
# Remove quarantine flag
xattr -cr dist/MPC_RandoKitter.app
```

### Linux dependencies missing

Some Linux distributions may need additional packages:

```bash
# Debian/Ubuntu
sudo apt-get install libxcb-xinerama0 libxkbcommon-x11-0

# Fedora/RHEL
sudo dnf install xcb-util-wm xcb-util-renderutil
```

### PyInstaller onefile+.app deprecation

PyInstaller 6.16+ warns that onefile mode combined with macOS `.app` bundles will become an error in v7.0. The current spec works on 6.x; future versions of MPC_RandoKitter should migrate to onedir mode (set `onefile=False` in the spec).

## Testing the Build

### macOS

```bash
# Run the app
open dist/MPC_RandoKitter.app

# Check for errors in Console.app
# Filter by process: MPC_RandoKitter

# Test with sample directories
open dist/MPC_RandoKitter.app
# Use GUI to select a source folder of samples
# Verify the generated kit structure is correct
```

### Linux

```bash
# Run the executable
./dist/MPC_RandoKitter

# Check console output for errors
# Test with sample directories
./dist/MPC_RandoKitter
# Use GUI to select a source folder of samples
# Verify the generated kit structure is correct
```

## Distribution

### macOS

**Option 1: DMG Disk Image (Recommended)**
```bash
# Create DMG with create-dmg
create-dmg --volname "MPC RandoKitter" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  dist/MPC_RandoKitter.dmg \
  dist/MPC_RandoKitter.app

# Upload DMG to GitHub Releases
```

**Option 2: ZIP Archive**
```bash
cd dist
zip -r MPC_RandoKitter-macOS.zip MPC_RandoKitter.app
```

### Linux

**Tarball Archive:**
```bash
cd dist
tar -czf MPC_RandoKitter-linux-$(uname -m).tar.gz MPC_RandoKitter

# Upload to GitHub Releases
```

**AppImage** (advanced):
```bash
# Use appimagetool to create AppImage
# See: https://appimage.org/
```

## GitHub Releases

### Manual Release

1. Go to GitHub repository
2. Click "Releases" -> "Create a new release"
3. Tag version (e.g., `v0.1.0`)
4. Upload build artifacts:
   - `MPC_RandoKitter.dmg` (macOS)
   - `MPC_RandoKitter-linux-x86_64.tar.gz` (Linux)
5. Add release notes
6. Publish release

### Automated Builds (GitHub Actions)

See `.github/workflows/build.yml` for automated builds on:
- Push to main branch
- New version tags
- Pull requests

## Version Information

Update version in these files before building:

1. `mpc_randokitter/__init__.py`:
   ```python
   __version__ = "0.1.0"
   ```

2. `MPC_RandoKitter.spec`:
   ```python
   'CFBundleShortVersionString': '0.1.0',
   'CFBundleVersion': '0.1.0',
   ```

3. `README.md`:
   ```markdown
   **Current Version:** v0.1.0
   ```

## Build Script Reference

### build.sh Commands

```bash
./build.sh build    # Build application (default)
./build.sh clean    # Remove build artifacts
./build.sh rebuild  # Clean then build
```

### Environment Variables

```bash
# Verbose output
VERBOSE=1 ./build.sh

# Skip UPX compression
UPX=0 pyinstaller MPC_RandoKitter.spec

# Custom PyInstaller options
PYINSTALLER_OPTS="--debug all" ./build.sh
```

## Further Reading

- [PyInstaller Documentation](https://pyinstaller.org/)
- [CustomTkinter PyInstaller Guide](https://github.com/TomSchimansky/CustomTkinter/wiki/Packaging)
- [Apple Code Signing Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)

## Support

For build issues:
1. Check this document's Troubleshooting section
2. Check [GitHub Issues](https://github.com/aTanguay/MPC_RandoKitter/issues)
3. Open a new issue with:
   - Platform and version
   - Python version
   - Build command used
   - Full error output
   - PyInstaller log files from `build/` directory
