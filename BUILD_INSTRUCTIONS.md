# Build Instructions for disk-analyzer-cli

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager) or uv (recommended for faster installs)

## Local Build (Windows)

### 1. Install Dependencies

**Using pip:**
```bash
pip install -e .[dev]
```

**Using uv (faster alternative):**
```bash
# Install uv first if you haven't
pip install uv
# Then install dependencies
uv pip install -e .[dev]
```

This installs all runtime dependencies (rich, questionary) and development dependencies (pyinstaller, pytest, black, ruff).

### 2. Build Executable

**Option A: Using command line**
```bash
pyinstaller --name disk-analyzer-cli --onefile --console --clean --noconfirm --hidden-import rich --hidden-import questionary --hidden-import chardet --add-data "README.md;." main.py
```

**Option B: Using spec file**
```bash
pyinstaller disk-analyzer-cli.spec
```

The executable will be created in the `dist/` directory as `disk-analyzer-cli.exe`.

### 3. Test the Executable

```bash
.\dist\disk-analyzer-cli.exe --help
```

## CI/CD Build (GitHub Actions)

The repository includes a GitHub Actions workflow that automatically builds the Windows executable:

- **On Push/PR**: Builds and uploads the executable as an artifact (available for 14 days)
- **On Release**: Builds and attaches the executable as a release asset

### To trigger a build:

1. Push code to `main` or `master` branch
2. Create a pull request
3. Create a GitHub release

### To download artifacts:

1. Go to the Actions tab in your GitHub repository
2. Select the workflow run
3. Download the artifact from the "Artifacts" section

## PyInstaller Configuration

The build uses the following optimizations:

- `--onefile`: Creates a single executable file
- `--console`: Shows console window for CLI interaction
- `--clean`: Clean temporary files before building
- `--noconfirm`: Skip confirmation prompts
- `upx=True`: Compress executable using UPX (reduces size by ~60%)

## Hidden Imports

The following modules are explicitly included to ensure all features work:

- `rich` and all submodules (console, progress, table, tree, etc.)
- `questionary` and submodules (prompts, types)
- `chardet` (character encoding detection)

## Troubleshooting

### Missing module errors
If you encounter "ModuleNotFoundError" at runtime, add the missing module to the `--hidden-import` list in the PyInstaller command or spec file.

### Large executable size
- Ensure UPX compression is enabled
- Remove unnecessary hidden imports
- Consider excluding unused modules with `--exclude-module`

### Antivirus false positives
This is common with PyInstaller executables. Solutions:
1. Sign the executable with a code signing certificate
2. Submit the executable to antivirus vendors for whitelisting
3. Build on a clean system to avoid contamination

## File Structure After Build

```
disk-analyzer-cli/
├── dist/
│   └── disk-analyzer-cli.exe    # Standalone executable
├── build/                        # Temporary build files (can be deleted)
├── *.spec                        # PyInstaller spec file
├── main.py                       # Entry point
├── scanner.py                    # Core scanning engine
├── tui.py                        # Terminal UI components
├── exporter.py                   # Export functionality
├── junk_detector.py              # Smart junk detection
└── pyproject.toml                # Project metadata and dependencies (PEP 621)
```

## Distribution

### For Development/Testing
- Share the artifact from GitHub Actions
- Distribute via internal network share

### For Public Release
1. Create a GitHub Release
2. The CI/CD pipeline will automatically attach the executable
3. Users can download from the Releases page

### Version Information
Consider adding version information using:
```bash
pyinstaller --version-info=file_version_info.txt ...
```

Create `file_version_info.txt` with product details for professional distribution.
