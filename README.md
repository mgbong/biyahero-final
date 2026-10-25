# Biyahero

A public transport navigation prototype for Cebu City.

## Requirements

- Python 3.10 or newer — https://www.python.org/downloads/
- That's it. SQLite is built into Python.

## Setup (do this once on every machine)

1. Open a terminal in this folder.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create the database:
   ```
   python database/init_db.py
   ```

## Running the app

```
python app.py
```

Then open your browser and go to: **http://127.0.0.1:5000**

## Stopping the app

Press `Ctrl + C` in the terminal.

## Notes

- The database file is at `database/biyahero.db`.
- Uploaded driver documents are saved in the `uploads/` folder.
- Do **not** run this on a public server as-is — it uses Flask's development server.
