#!/usr/bin/env bash
#
# Build script for MPC_RandoKitter
# Creates a standalone executable for the current platform
#
# Usage:
#   ./build.sh          # Build for current platform
#   ./build.sh clean    # Clean build artifacts
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Print colored message
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Clean build artifacts
clean() {
    print_info "Cleaning build artifacts..."
    rm -rf build dist __pycache__
    rm -rf mpc_randokitter/__pycache__
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    print_info "Clean complete!"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Build the application
build() {
    print_info "Starting MPC_RandoKitter build..."
    echo

    # Check Python version
    print_info "Checking Python version..."
    if ! command_exists python3; then
        print_error "Python 3 not found! Please install Python 3.7 or later."
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
        print_error "Python 3.7 or later required. Found: $PYTHON_VERSION"
        exit 1
    fi
    print_info "Python version: $PYTHON_VERSION ✓"

    # Check if PyInstaller is installed
    if ! command_exists pyinstaller; then
        print_error "PyInstaller not found!"
        print_info "Installing build requirements..."
        python3 -m pip install -r requirements-build.txt
    fi

    # Verify package version
    print_info "Verifying package version..."
    PACKAGE_VERSION=$(python3 -c "import mpc_randokitter; print(mpc_randokitter.__version__)" 2>/dev/null || echo "unknown")
    if [ "$PACKAGE_VERSION" != "unknown" ]; then
        print_info "Package version: $PACKAGE_VERSION"
    else
        print_warn "Could not verify package version (package may not be installed)"
    fi

    # Clean previous builds
    print_info "Cleaning previous builds..."
    rm -rf build dist

    # Detect platform
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PLATFORM="macOS"
        OUTPUT_NAME="MPC_RandoKitter.app"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        PLATFORM="Linux"
        OUTPUT_NAME="MPC_RandoKitter"
    else
        PLATFORM="Unknown"
        OUTPUT_NAME="MPC_RandoKitter"
    fi

    print_info "Building for $PLATFORM..."
    echo

    # Run PyInstaller
    print_info "Running PyInstaller..."
    pyinstaller --clean MPC_RandoKitter.spec

    # Check if build succeeded
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [ -d "dist/MPC_RandoKitter.app" ]; then
            print_info "Build successful! ✓"
            print_info "Application: dist/MPC_RandoKitter.app"

            # Show build size
            BUILD_SIZE=$(du -sh dist/MPC_RandoKitter.app 2>/dev/null | awk '{print $1}')
            print_info "Build size: $BUILD_SIZE"

            echo
            print_info "To run:"
            echo "  open dist/MPC_RandoKitter.app"
            echo
            print_info "To create DMG (requires create-dmg):"
            echo "  create-dmg --volname 'MPC_RandoKitter' \\"
            echo "    --window-pos 200 120 --window-size 800 400 \\"
            echo "    --icon-size 100 --app-drop-link 600 185 \\"
            echo "    dist/MPC_RandoKitter.dmg dist/MPC_RandoKitter.app"
        else
            print_error "Build failed! Application not found."
            exit 1
        fi
    else
        if [ -f "dist/MPC_RandoKitter" ]; then
            # Make executable
            chmod +x dist/MPC_RandoKitter

            print_info "Build successful! ✓"
            print_info "Executable: dist/MPC_RandoKitter"

            # Show build size
            BUILD_SIZE=$(du -sh dist/MPC_RandoKitter 2>/dev/null | awk '{print $1}')
            print_info "Build size: $BUILD_SIZE"

            echo
            print_info "To run:"
            echo "  ./dist/MPC_RandoKitter"
            echo
            print_info "To create portable archive:"
            echo "  cd dist && tar -czf MPC_RandoKitter-linux-$(uname -m).tar.gz MPC_RandoKitter"
        else
            print_error "Build failed! Executable not found."
            exit 1
        fi
    fi

    echo
    print_info "Build artifacts:"
    du -sh dist/* 2>/dev/null || true
}

# Test the built application
test_build() {
    print_info "Testing built application..."
    echo

    if [[ "$OSTYPE" == "darwin"* ]]; then
        if [ ! -d "dist/MPC_RandoKitter.app" ]; then
            print_error "Application not found! Build first with: ./build.sh build"
            exit 1
        fi

        print_info "Verifying app bundle structure..."
        if [ ! -f "dist/MPC_RandoKitter.app/Contents/MacOS/MPC_RandoKitter" ]; then
            print_error "Invalid app bundle structure!"
            exit 1
        fi

        print_info "Checking for code signature..."
        codesign -dv dist/MPC_RandoKitter.app 2>&1 | grep -q "Signature" && \
            print_info "App is code signed ✓" || \
            print_warn "App is not code signed (expected for local builds)"

        print_info "macOS app bundle structure is valid ✓"

    else
        if [ ! -f "dist/MPC_RandoKitter" ]; then
            print_error "Executable not found! Build first with: ./build.sh build"
            exit 1
        fi

        print_info "Checking executable permissions..."
        if [ -x "dist/MPC_RandoKitter" ]; then
            print_info "Executable permissions set ✓"
        else
            print_warn "Executable permissions not set"
            chmod +x dist/MPC_RandoKitter
        fi

        print_info "Checking dependencies..."
        ldd dist/MPC_RandoKitter 2>/dev/null | grep "not found" && \
            print_warn "Missing system libraries detected" || \
            print_info "All dependencies found ✓"
    fi

    echo
    print_info "Build test passed! ✓"
}

# Main script
case "${1:-build}" in
    clean)
        clean
        ;;
    build)
        build
        ;;
    rebuild)
        clean
        build
        ;;
    test)
        test_build
        ;;
    *)
        echo "Usage: $0 {build|clean|rebuild|test}"
        echo
        echo "Commands:"
        echo "  build    - Build the application (default)"
        echo "  clean    - Clean build artifacts"
        echo "  rebuild  - Clean and build"
        echo "  test     - Test the built application"
        exit 1
        ;;
esac
