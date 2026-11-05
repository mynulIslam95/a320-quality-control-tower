# A320 Quality Control Tower

Interactive quality dashboard using fictional A320-family records. Independent portfolio project, not affiliated with Airbus and not connected to Skywise.

## Features

- Contour-inspired exploration of aircraft quality metrics and site comparisons
- Workshop-inspired aircraft investigations and corrective-action status updates
- Slate-inspired operational summary and CSV export
- Feature feasibility tracker for proposed improvements

## Run

Python 3.10+ is required. No external Python dependencies.

```bash
python -m app.backend
```

Open http://127.0.0.1:8501. The application creates synthetic sample records in `data/quality.db` on first launch.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project 1 compatibility

The application uses the same aircraft IDs and five-table relational structure as [A320 Quality Data Platform](https://github.com/mynulIslam95/a320-quality-data-platform). To open a **copy** of its validated database:

```bash
QUALITY_DB=/absolute/path/to/quality.db python -m app.backend
```

The application creates its own feature-request table in the selected database.

All aircraft and quality records are synthetic. The application runs locally without authentication and must not be exposed publicly. Its indicators are demonstrations, not airworthiness decisions.
