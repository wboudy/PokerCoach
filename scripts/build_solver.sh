#!/usr/bin/env bash
# Build script for TexasSolver GTO poker solver (console version)
# This script clones, builds, and installs TexasSolver to bin/texas_solver
#
# Usage: ./scripts/build_solver.sh
#
# Requirements (installed automatically on macOS with Homebrew):
#   - cmake
#   - git
#   - libomp (for OpenMP support)
#   - C++ compiler (clang/g++)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/.solver_build"
BIN_DIR="$PROJECT_ROOT/bin"
SOLVER_REPO="https://github.com/bupticybee/TexasSolver.git"
SOLVER_BRANCH="console"
SOLVER_BINARY="$BIN_DIR/texas_solver"

echo "=== TexasSolver Build Script ==="
echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Target binary: $SOLVER_BINARY"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install dependencies on macOS
install_deps_macos() {
    if command_exists brew; then
        echo "Installing dependencies via Homebrew..."
        if ! command_exists cmake; then
            echo "  Installing cmake..."
            brew install cmake
        fi
        if ! command_exists git; then
            echo "  Installing git..."
            brew install git
        fi
        # libomp is required for OpenMP on macOS
        if ! brew list libomp &>/dev/null; then
            echo "  Installing libomp (for OpenMP support)..."
            brew install libomp
        fi
    else
        echo "ERROR: Homebrew not found. Please install cmake, git, and libomp manually."
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  brew install cmake git libomp"
        exit 1
    fi
}

# Install dependencies on Linux
install_deps_linux() {
    if command_exists apt-get; then
        echo "Installing dependencies via apt..."
        sudo apt-get update
        sudo apt-get install -y cmake git build-essential libomp-dev
    elif command_exists yum; then
        echo "Installing dependencies via yum..."
        sudo yum install -y cmake git gcc-c++ make libomp-devel
    elif command_exists dnf; then
        echo "Installing dependencies via dnf..."
        sudo dnf install -y cmake git gcc-c++ make libomp-devel
    elif command_exists pacman; then
        echo "Installing dependencies via pacman..."
        sudo pacman -S --noconfirm cmake git base-devel openmp
    else
        echo "ERROR: Could not detect package manager. Please install cmake, git, and OpenMP manually."
        exit 1
    fi
}

# Check and install dependencies
check_dependencies() {
    echo "Checking dependencies..."

    case "$(uname -s)" in
        Darwin)
            install_deps_macos
            ;;
        Linux)
            # Check what's missing on Linux
            local missing=()
            command_exists cmake || missing+=("cmake")
            command_exists git || missing+=("git")
            if [ ${#missing[@]} -gt 0 ]; then
                install_deps_linux
            fi
            ;;
        *)
            echo "ERROR: Unsupported platform: $(uname -s)"
            exit 1
            ;;
    esac

    echo "All dependencies satisfied."
    echo "  cmake: $(cmake --version | head -1)"
    echo "  git: $(git --version)"
    echo ""
}

# Clone the repository
clone_repo() {
    if [ -d "$BUILD_DIR/TexasSolver" ]; then
        echo "TexasSolver already cloned."
        cd "$BUILD_DIR/TexasSolver"
        # Ensure we're on the console branch
        local current_branch
        current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
        if [ "$current_branch" != "$SOLVER_BRANCH" ]; then
            echo "  Switching to $SOLVER_BRANCH branch..."
            git fetch origin "$SOLVER_BRANCH:$SOLVER_BRANCH" --depth=1 2>/dev/null || true
            git checkout "$SOLVER_BRANCH"
        fi
        echo "  Pulling latest changes..."
        git pull --ff-only 2>/dev/null || echo "  Warning: Could not pull latest (may be on detached HEAD)"
    else
        echo "Cloning TexasSolver ($SOLVER_BRANCH branch)..."
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        git clone --depth 1 --branch "$SOLVER_BRANCH" "$SOLVER_REPO"
    fi
    echo ""
}

# Build the solver
build_solver() {
    echo "Building TexasSolver..."
    cd "$BUILD_DIR/TexasSolver"

    # Clean previous build if exists
    rm -rf build
    mkdir -p build
    cd build

    # Configure cmake with platform-specific settings
    echo "  Configuring with cmake..."

    local cmake_args=(
        "-DCMAKE_BUILD_TYPE=Release"
        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"  # Required for old googletest in TexasSolver
    )

    if [ "$(uname -s)" = "Darwin" ]; then
        # macOS-specific: help cmake find libomp from Homebrew
        local homebrew_prefix
        homebrew_prefix=$(brew --prefix 2>/dev/null || echo "/opt/homebrew")
        local libomp_prefix
        libomp_prefix=$(brew --prefix libomp 2>/dev/null || echo "$homebrew_prefix/opt/libomp")

        if [ -d "$libomp_prefix" ]; then
            echo "  Using libomp from: $libomp_prefix"
            cmake_args+=(
                "-DOpenMP_C_FLAGS=-Xpreprocessor -fopenmp -I$libomp_prefix/include"
                "-DOpenMP_CXX_FLAGS=-Xpreprocessor -fopenmp -I$libomp_prefix/include"
                "-DOpenMP_C_LIB_NAMES=omp"
                "-DOpenMP_CXX_LIB_NAMES=omp"
                "-DOpenMP_omp_LIBRARY=$libomp_prefix/lib/libomp.dylib"
                # Important: Link flags to include libomp at link time
                "-DCMAKE_EXE_LINKER_FLAGS=-L$libomp_prefix/lib -lomp"
                "-DCMAKE_SHARED_LINKER_FLAGS=-L$libomp_prefix/lib -lomp"
            )
        fi
    fi

    cmake .. "${cmake_args[@]}"

    # Build
    echo "  Building..."
    local num_cores
    num_cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    cmake --build . --config Release -j "$num_cores"

    echo "Build complete."
    echo ""
}

# Install the binary
install_binary() {
    echo "Installing binary..."

    mkdir -p "$BIN_DIR"

    # The console version produces 'console_solver'
    local built_binary="$BUILD_DIR/TexasSolver/build/console_solver"

    if [ ! -f "$built_binary" ]; then
        # Try to find it elsewhere
        echo "  Searching for built executable..."
        built_binary=$(find "$BUILD_DIR/TexasSolver/build" -type f -name "console_solver" 2>/dev/null | head -1 || true)

        if [ -z "$built_binary" ] || [ ! -f "$built_binary" ]; then
            echo "  Contents of build directory:"
            ls -la "$BUILD_DIR/TexasSolver/build" 2>/dev/null || true
            echo ""
            echo "ERROR: Could not find built solver binary 'console_solver'."
            echo "Please check the build output above for errors."
            exit 1
        fi
    fi

    echo "  Found binary: $built_binary"
    cp "$built_binary" "$SOLVER_BINARY"
    chmod +x "$SOLVER_BINARY"

    # Also copy resources directory if it exists (needed for solver)
    if [ -d "$BUILD_DIR/TexasSolver/resources" ]; then
        echo "  Copying resources..."
        cp -r "$BUILD_DIR/TexasSolver/resources" "$BIN_DIR/"
    fi

    echo "  Installed to: $SOLVER_BINARY"
    echo ""
}

# Verify installation
verify_installation() {
    echo "Verifying installation..."

    if [ ! -f "$SOLVER_BINARY" ]; then
        echo "ERROR: Binary not found at $SOLVER_BINARY"
        exit 1
    fi

    if [ ! -x "$SOLVER_BINARY" ]; then
        echo "ERROR: Binary is not executable"
        exit 1
    fi

    echo "  Binary exists and is executable"
    echo "  Binary size: $(ls -lh "$SOLVER_BINARY" | awk '{print $5}')"

    # Try to run the binary to see if it loads
    # Note: console_solver requires a config file, so we just test it starts
    if "$SOLVER_BINARY" 2>&1 | head -1 | grep -q "command"; then
        echo "  Binary runs successfully (awaiting config file)"
    fi

    echo ""
    echo "=== Installation Complete ==="
    echo "TexasSolver installed to: $SOLVER_BINARY"
    echo ""
    echo "Usage: $SOLVER_BINARY <config_file>"
    echo "See: https://github.com/bupticybee/TexasSolver/tree/console#usage"
}

# Cleanup function
cleanup() {
    echo ""
    echo "To save disk space, you can remove the build directory:"
    echo "  rm -rf $BUILD_DIR"
}

# Main execution
main() {
    check_dependencies
    clone_repo
    build_solver
    install_binary
    verify_installation
    cleanup
}

main "$@"
