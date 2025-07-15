from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'studiobayram_secret')

# PostgreSQL veritabanı bağlantısı (Render environment variable'dan alıyor)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Yönetici bilgileri
ADMIN_USERNAME = 'bayram'
ADMIN_PASSWORD = 'samsun55'

# Model: İçerik
class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    filetype = db.Column(db.String(20), nullable=False)

# Model: Mesaj
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

# Giriş kontrolü dekoratörü
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Lütfen giriş yapınız.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Sayfalar
@app.route('/')
def index():
    photos = Content.query.filter_by(filetype='photo').limit(6).all()
    videos = Content.query.filter_by(filetype='video').limit(4).all()
    return render_template('index.html', photos=photos, videos=videos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Başarıyla giriş yapıldı.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Hatalı giriş bilgisi!', 'danger')
    return render_template('login.html')

@app.route('/hakkimizda')
def about():
    return render_template('about.html')

@app.route('/iletisim', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message_text = request.form.get('message')

        if name and email and subject and message_text:
            new_message = Message(
                name=name, email=email, subject=subject, message=message_text
            )
            db.session.add(new_message)
            db.session.commit()
            flash('Mesajınız başarıyla gönderildi.', 'success')
            return redirect(url_for('contact'))
        else:
            flash('Lütfen tüm alanları doldurun.', 'warning')

    return render_template('contact.html')

@app.route('/fotograflar')
def photos():
    photos = Content.query.filter_by(filetype='photo').all()
    return render_template('photos.html', files=photos)

@app.route('/videolar')
def videos():
    videos = Content.query.filter_by(filetype='video').all()
    return render_template('videos.html', files=videos)

@app.route('/dashboard')
@login_required
def dashboard():
    content_count = Content.query.count()
    photo_count = Content.query.filter_by(filetype='photo').count()
    video_count = Content.query.filter_by(filetype='video').count()
    message_count = Message.query.count()
    return render_template('dashboard.html', total=content_count, photos=photo_count, videos=video_count, messages=message_count)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            upload_folder = 'static/uploads/'
            os.makedirs(upload_folder, exist_ok=True)
            save_path = os.path.join(upload_folder, filename)

            if Content.query.filter_by(filename=filename).first():
                flash('Bu dosya zaten mevcut!', 'danger')
                return redirect(url_for('upload_file'))

            file.save(save_path)

            ext = os.path.splitext(filename)[1].lower()
            if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                filetype = 'photo'
            elif ext in ('.mp4', '.mov', '.avi', '.webm'):
                filetype = 'video'
            else:
                filetype = 'other'

            new_content = Content(filename=filename, filetype=filetype)
            db.session.add(new_content)
            db.session.commit()

            flash('Dosya başarıyla yüklendi.', 'success')
            return redirect(url_for('content_list'))
        else:
            flash('Lütfen bir dosya seçin!', 'warning')
    return render_template('upload.html')

@app.route('/contents')
@login_required
def content_list():
    files = Content.query.all()
    return render_template('content_list.html', files=files)

@app.route('/messages')
@login_required
def message_list():
    messages = Message.query.order_by(Message.created_at.desc()).all()
    return render_template('message_list.html', messages=messages)

@app.route('/delete/<int:content_id>')
@login_required
def delete_file(content_id):
    content = Content.query.get_or_404(content_id)
    file_path = os.path.join('static/uploads/', content.filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(content)
        db.session.commit()
        flash('Dosya başarıyla silindi.', 'success')
    except Exception as e:
        flash(f'Hata: {e}', 'danger')
    return redirect(url_for('content_list'))

@app.route('/delete_message/<int:message_id>')
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Mesaj silindi.', 'success')
    return redirect(url_for('message_list'))

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Çıkış yapıldı.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
