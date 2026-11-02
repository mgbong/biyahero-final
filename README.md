# Biyahero

A public transport navigation prototype for Cebu City.

---

## ⚠️ Important — Do NOT open HTML files directly or with Live Server

Always access the app through Flask. Opening files with VS Code Live Server
(port 5500) or by double-clicking the HTML file will break signups and login
because the API calls won't reach the Flask backend.

**Correct URL:** http://127.0.0.1:5000  
**Wrong:** http://127.0.0.1:5500 or file:///...

---

## Requirements

- Python 3.10 or newer — https://www.python.org/downloads/
- That's it. SQLite is built into Python.

## Setup (do this once on every machine)

1. Open a terminal in this folder.

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create the database (only needed the first time):
   ```
   python database/init_db.py
   ```

## Running the app

```
python app.py
```

Then open your browser and go to: **http://127.0.0.1:5000**

To stop the app, press `Ctrl + C` in the terminal.

---

## Accessing from another device on the same Wi-Fi

By default Flask only accepts connections from the same machine (127.0.0.1).
To let other devices on the same network open the app:

1. Run Flask with host 0.0.0.0:
   ```
   python app.py --host
   ```
2. Find your machine's local IP address:
   - Windows: run `ipconfig` in a terminal, look for IPv4 Address (e.g. 192.168.1.5)
3. On the other device, open: **http://192.168.1.5:5000**

---

## Notes

- The database file is at `database/biyahero.db`.
- Uploaded driver documents are saved in the `uploads/` folder.
- Do **not** expose this to the public internet — it uses Flask's development server.
