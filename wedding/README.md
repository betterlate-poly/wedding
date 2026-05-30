# Zuka & Mike Wedding – Photo & Video Sharing Site

A private, mobile-first wedding gallery for Zuka & Mike.

---

## Quick Start

### 1. Clone / copy the project

```
wedding/
├── app.py
├── requirements.txt
├── instance/          ← auto-created (SQLite DB lives here)
├── static/
│   ├── css/           main.css, admin.css
│   ├── js/            main.js, camera.js, upload.js, gallery.js, sw.js
│   └── uploads/       ← auto-created (uploaded media)
└── templates/         ← all HTML templates
```

### 2. Create a virtual environment & install

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run (development)

```bash
python app.py
```
The site is now at **http://localhost:5000**

### 4. Run (production / accessible on your network)

```bash
# Expose to all devices on your WiFi:
flask run --host=0.0.0.0 --port=5000

# Or use Gunicorn (recommended for production):
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

### 5. QR Code

Generate a QR code pointing to your server's IP, e.g.
`http://192.168.1.42:5000`
and print it for the tables / signage at the wedding.

---

## Access Codes

| What                     | Code          |
|--------------------------|---------------|
| Gallery (View Memories)  | **1298**      |
| Admin Dashboard          | **admin2024** |
| Camera page              | (none needed) |
| Upload page              | (none needed) |

To change codes, edit `app.py`:
```python
GALLERY_CODE = '1298'
ADMIN_CODE   = 'admin2024'
```

---

## URLs

| URL         | Purpose                        |
|-------------|--------------------------------|
| `/`         | Landing page                   |
| `/camera`   | In-browser camera (no code)    |
| `/upload`   | File upload page (no code)     |
| `/gallery`  | Photo gallery (code required)  |
| `/admin`    | Admin dashboard (password req) |

---

## Deployment Tips

- **HTTPS is required** for camera access on mobile. Use a reverse proxy (nginx/Caddy) with a certificate, or expose with a tunnel like ngrok / Cloudflare Tunnel.
- **Max upload size**: 200 MB per file (configurable in `app.py`).
- **Supported formats**: JPG, JPEG, PNG, WEBP (images) · MP4, MOV, WEBM (videos).
- Images are automatically compressed/resized to max 2400 px on the long edge.

---

## Customisation

| Thing to change          | Where                         |
|--------------------------|-------------------------------|
| Couple's names           | `templates/index.html`        |
| Gallery/admin codes      | `app.py` top of file          |
| Max file size            | `app.py` MAX_CONTENT variable |
| Colour palette           | `static/css/main.css` :root   |
| Fonts                    | CSS import + `--font-*` vars  |
