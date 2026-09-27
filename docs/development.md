# CodeMemory Development & Testing Guide

For the Windows product and public website, use the current
[desktop/release guide](windows-release.md) and [website guide](../website/README.md).
The studio commands below remain developer tools. Keep test exports isolated:
run pytest from `build/tests` with `../../tests` as the target.

## Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/PranavGadge01/CodeMemory.git
   cd codememory
   ```

2. Install in editable mode with development dependencies:
   ```bash
   pip install -e .[dev]
   ```

## Running Automated Tests

Run the full pytest suite:
```bash
python -m pytest ../../tests -v
```

Run test suite with test coverage:
```bash
python -m pytest ../../tests --cov=codememory
```

## Running the Web App

Launch Streamlit interactive developer studio:
```bash
codememory ui
# or
streamlit run src/codememory/app/app.py
```

## Seeding Demo Data

Populate local dataset with 22 classic DSA practice problems:
```bash
codememory seed
```
