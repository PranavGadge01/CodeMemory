# CodeMemory Development & Testing Guide

## Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/codememory.git
   cd codememory
   ```

2. Install in editable mode with development dependencies:
   ```bash
   pip install -e .[dev]
   ```

## Running Automated Tests

Run the full pytest suite:
```bash
pytest -v
```

Run test suite with test coverage:
```bash
pytest --cov=codememory
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
