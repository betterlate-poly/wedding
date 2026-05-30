import os
import uuid
import json
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, send_from_directory, abort
)
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from PIL import Image
import sqlite3

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get('SECRET_KEY', 'zuka-mike-wedding-2024-secret-key')

# Session cookie settings – fixes redirect loop after gallery login
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = False   # set True if serving over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True

# ── Config ──────────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
DB_PATH       = os.path.join(BASE_DIR, 'instance', 'wedding.db')
MAX_CONTENT   = 200 * 1024 * 1024  # 200 MB

GALLERY_CODE  = '1298'
ADMIN_CODE    = 'admin2024'

ALLOWED_IMAGE = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
ALLOWED_VIDEO = {'mp4', 'mov', 'webm', 'avi'}
ALLOWED_ALL   = ALLOWED_IMAGE | ALLOWED_VIDEO

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)


# ── Database ─────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS media (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                filepath    TEXT NOT NULL,
                media_type  TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                file_size   INTEGER NOT NULL,
                mime_type   TEXT,
                width       INTEGER,
                height      INTEGER
            )
        ''')
        db.commit()


init_db()


# ── Helpers ──────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_ALL


def get_media_type(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    return 'video' if ext in ALLOWED_VIDEO else 'image'


def compress_image(filepath, max_dim=2400, quality=82):
    """Resize large images and re-save as JPEG/WEBP to save space."""
    try:
        with Image.open(filepath) as img:
            # Keep EXIF orientation
            try:
                from PIL import ImageOps
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            w, h = img.size
            if max(w, h) > max_dim:
                ratio = max_dim / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

            ext = os.path.splitext(filepath)[1].lower()
            if ext in ('.jpg', '.jpeg'):
                img = img.convert('RGB')
                img.save(filepath, 'JPEG', quality=quality, optimize=True)
            elif ext == '.webp':
                img.save(filepath, 'WEBP', quality=quality)
            elif ext == '.png':
                img.save(filepath, 'PNG', optimize=True)
    except Exception as e:
        print(f'Image compression failed: {e}')


def save_file(file):
    """Save uploaded file, returning (filename, media_type, size) or raise."""
    if not allowed_file(file.filename):
        raise ValueError(f'File type not allowed: {file.filename}')

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(filepath)

    media_type = get_media_type(unique_name)
    if media_type == 'image':
        compress_image(filepath)

    size = os.path.getsize(filepath)
    return unique_name, media_type, size


def insert_media(filename, media_type, size):
    filepath = os.path.join('static', 'uploads', filename)
    with get_db() as db:
        db.execute('''
            INSERT INTO media (filename, filepath, media_type, upload_time, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, filepath, media_type, datetime.utcnow().isoformat(), size))
        db.commit()


def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} TB'


# ── Routes: public ────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/camera')
def camera():
    return render_template('camera.html')


@app.route('/upload')
def upload():
    return render_template('upload.html')


@app.route('/gallery')
def gallery():
    if not session.get('gallery_auth'):
        return render_template('gallery_lock.html', error=None)
    return render_template('gallery.html')


@app.route('/gallery/auth', methods=['POST'])
def gallery_auth():
    code = request.form.get('code', '').strip()
    if code == GALLERY_CODE:
        session['gallery_auth'] = True
        session.modified = True
        resp = redirect(url_for('gallery'))
        resp.set_cookie('gallery_auth', 'true', samesite='Lax', httponly=True)
        return resp
    return render_template('gallery_lock.html', error='Incorrect code. Please try again.')


@app.route('/gallery/delete/<int:media_id>', methods=['POST'])
def gallery_delete(media_id):
    if not session.get('gallery_auth'):
        return jsonify({'error': 'Unauthorized'}), 403
    with get_db() as db:
        row = db.execute('SELECT * FROM media WHERE id=?', (media_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        try:
            os.remove(os.path.join(BASE_DIR, 'static', 'uploads', row['filename']))
        except FileNotFoundError:
            pass
        db.execute('DELETE FROM media WHERE id=?', (media_id,))
        db.commit()
    return jsonify({'success': True})


@app.route('/gallery/logout', methods=['GET', 'POST'])
def gallery_logout():
    session.pop('gallery_auth', None)
    if request.method == 'POST':
        return '', 204
    return redirect(url_for('index'))


# ── API: upload ───────────────────────────────────────────────────────────────
@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    files = request.files.getlist('files') or [request.files.get('file')]
    results = []

    for file in files:
        if not file or not file.filename:
            continue
        try:
            filename, media_type, size = save_file(file)
            insert_media(filename, media_type, size)
            results.append({
                'filename': filename,
                'media_type': media_type,
                'size': human_size(size),
                'url': url_for('static', filename=f'uploads/{filename}')
            })
        except ValueError as e:
            results.append({'error': str(e), 'original': file.filename})
        except Exception as e:
            results.append({'error': 'Upload failed', 'detail': str(e)})

    if not results:
        return jsonify({'error': 'No valid files uploaded'}), 400
    return jsonify({'uploaded': results}), 200


# ── API: gallery data ─────────────────────────────────────────────────────────
@app.route('/api/gallery')
def api_gallery():
    # Accept session auth OR gallery code passed as query param (fallback for
    # browsers that drop the session cookie on same-origin fetch)
    code_param = request.args.get('code', '')
    if not session.get('gallery_auth') and code_param != GALLERY_CODE:
        return jsonify({'error': 'Unauthorized', 'redirect': '/gallery'}), 403

    # Promote to session if authenticated via param
    if code_param == GALLERY_CODE:
        session['gallery_auth'] = True

    try:
        page  = max(1, int(request.args.get('page', 1)))
        limit = max(1, min(100, int(request.args.get('limit', 30))))
    except (ValueError, TypeError):
        page, limit = 1, 30

    offset = (page - 1) * limit

    try:
        with get_db() as db:
            rows  = db.execute(
                'SELECT * FROM media ORDER BY id DESC LIMIT ? OFFSET ?',
                (limit, offset)
            ).fetchall()
            total = db.execute('SELECT COUNT(*) FROM media').fetchone()[0]
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

    items = []
    for r in rows:
        items.append({
            'id':          r['id'],
            'filename':    r['filename'],
            'url':         f"/static/uploads/{r['filename']}",
            'media_type':  r['media_type'],
            'upload_time': r['upload_time'],
            'file_size':   human_size(r['file_size']),
        })
    return jsonify({'items': items, 'total': total, 'page': page, 'limit': limit})


# ── Admin ─────────────────────────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if not session.get('admin_auth'):
        return render_template('admin_login.html', error=None)
    with get_db() as db:
        rows  = db.execute('SELECT * FROM media ORDER BY id DESC').fetchall()
        total = db.execute('SELECT COUNT(*) FROM media').fetchone()[0]
        imgs  = db.execute("SELECT COUNT(*) FROM media WHERE media_type='image'").fetchone()[0]
        vids  = db.execute("SELECT COUNT(*) FROM media WHERE media_type='video'").fetchone()[0]
        size_b= db.execute('SELECT SUM(file_size) FROM media').fetchone()[0] or 0

    media = [dict(r) for r in rows]
    for m in media:
        m['file_size'] = human_size(m['file_size'])

    stats = {
        'total': total,
        'images': imgs,
        'videos': vids,
        'storage': human_size(size_b),
    }
    return render_template('admin.html', media=media, stats=stats)


@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form.get('password') == ADMIN_CODE:
        session['admin_auth'] = True
        return redirect(url_for('admin'))
    return render_template('admin_login.html', error='Incorrect password.')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_auth', None)
    return redirect(url_for('index'))


@app.route('/admin/delete/<int:media_id>', methods=['POST'])
def admin_delete(media_id):
    if not session.get('admin_auth'):
        abort(403)
    with get_db() as db:
        row = db.execute('SELECT * FROM media WHERE id=?', (media_id,)).fetchone()
        if row:
            try:
                os.remove(os.path.join(BASE_DIR, 'static', 'uploads', row['filename']))
            except FileNotFoundError:
                pass
            db.execute('DELETE FROM media WHERE id=?', (media_id,))
            db.commit()
    return redirect(url_for('admin'))


@app.route('/admin/api/stats')
def admin_stats():
    if not session.get('admin_auth'):
        return jsonify({'error': 'Unauthorized'}), 403
    with get_db() as db:
        rows = db.execute(
            "SELECT strftime('%Y-%m-%d', upload_time) as day, COUNT(*) as cnt "
            "FROM media GROUP BY day ORDER BY day"
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ── PWA ───────────────────────────────────────────────────────────────────────
@app.route('/manifest.json')
def manifest():
    data = {
        "name": "Zuka & Mike Wedding",
        "short_name": "Z&M Wedding",
        "description": "Share your memories from Zuka & Mike's wedding",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#faf8f3",
        "theme_color": "#c9a84c",
        "orientation": "portrait-primary",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    from flask import Response
    return Response(json.dumps(data), mimetype='application/json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'js'), 'sw.js',
                               mimetype='application/javascript')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
