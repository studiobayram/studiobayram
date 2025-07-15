import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# Flask Uygulaması
app = Flask(__name__)

# SECRET KEY (env'den al, yoksa varsayılan)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'varsayilan_secret_key')

# DATABASE_URL (Render veya localde env'den al)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instance/studio.db')

# Eğer postgres:// ile başlıyorsa düzelt
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload klasörü ve izin verilen dosya uzantıları
UPLOAD_FOLDER = os.path.join('static', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Veritabanı ve login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'

# -------------------- MODELLER --------------------

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    sifre = db.Column(db.String(255), nullable=False)
    kayit_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f"admin-{self.id}"

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(150), nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    github_link = db.Column(db.String(255))
    proje_img = db.Column(db.String(255))
    eklenme_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    id = db.Column(db.Integer, primary_key=True)
    isim = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    gonderme_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------- LOGIN MANAGER --------------------

@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith("admin-"):
        return Admin.query.get(int(user_id.split("-")[1]))
    return None

# -------------------- YARDIMCI FONKSİYON --------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------- İLK ADMIN OLUŞTURMA --------------------

with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(kullanici_adi="bayram").first():
        yeni_admin = Admin(
            kullanici_adi="bayram",
            email="bayramgucer9@gmail.com",
            sifre=generate_password_hash("samsun55")
        )
        db.session.add(yeni_admin)
        db.session.commit()
        print("Admin kullanıcı başarıyla oluşturuldu.")

# -------------------- ROUTELAR --------------------

@app.route('/')
def index():
    projeler = Project.query.order_by(Project.eklenme_tarihi.desc()).all()
    return render_template('index.html', projeler=projeler)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/projects')
def projects():
    projeler = Project.query.order_by(Project.eklenme_tarihi.desc()).all()
    return render_template('projects.html', projeler=projeler)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        isim = request.form.get('isim')
        email = request.form.get('email')
        mesaj = request.form.get('mesaj')

        if not isim or not email or not mesaj:
            flash("Lütfen tüm alanları doldurun.", "danger")
            return redirect(url_for('contact'))

        yeni_mesaj = ContactMessage(isim=isim, email=email, mesaj=mesaj)
        db.session.add(yeni_mesaj)
        db.session.commit()
        flash("Mesajınız başarıyla gönderildi.", "success")
        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        admin = Admin.query.filter_by(kullanici_adi=kullanici_adi).first()

        if admin and check_password_hash(admin.sifre, sifre):
            login_user(admin)
            flash("Yönetici olarak giriş yapıldı.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Kullanıcı adı veya şifre hatalı!", "danger")

    return render_template('admin_login.html')

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    projeler = Project.query.order_by(Project.eklenme_tarihi.desc()).all()
    return render_template('admin_dashboard.html', projeler=projeler)

@app.route('/admin-dashboard/messages')
@login_required
def admin_messages():
    mesajlar = ContactMessage.query.order_by(ContactMessage.gonderme_tarihi.desc()).all()
    return render_template('admin_messages.html', mesajlar=mesajlar)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for('admin_login'))

@app.route('/admin-dashboard/add-project', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        baslik = request.form.get('baslik')
        aciklama = request.form.get('aciklama')
        github_link = request.form.get('github_link')
        file = request.files.get('proje_img')

        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

        yeni_proje = Project(
            baslik=baslik,
            aciklama=aciklama,
            github_link=github_link,
            proje_img=filename
        )
        db.session.add(yeni_proje)
        db.session.commit()
        flash("Proje başarıyla eklendi.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('add_project.html')

@app.route('/admin-dashboard/delete-project/<int:proje_id>', methods=['POST'])
@login_required
def delete_project(proje_id):
    proje = Project.query.get_or_404(proje_id)
    if proje.proje_img:
        dosya_yolu = os.path.join(app.config['UPLOAD_FOLDER'], proje.proje_img)
        if os.path.exists(dosya_yolu):
            os.remove(dosya_yolu)
    db.session.delete(proje)
    db.session.commit()
    flash("Proje ve görsel dosyası başarıyla silindi.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-dashboard/delete-message/<int:mesaj_id>', methods=['POST'])
@login_required
def delete_message(mesaj_id):
    mesaj = ContactMessage.query.get_or_404(mesaj_id)
    db.session.delete(mesaj)
    db.session.commit()
    flash("Mesaj başarıyla silindi.", "success")
    return redirect(url_for('admin_messages'))

# -------------------- ANA PROGRAM --------------------

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
