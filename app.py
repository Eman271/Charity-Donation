from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2, os
from functools import wraps
from config import Config
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =====================
# DB HELPERS
# =====================
def get_db():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def rows_to_dicts(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def row_to_dict(cursor, row):
    if row is None:
        return {}
    return dict(zip([col[0] for col in cursor.description], row))

# =====================
# AUTH DECORATORS
# =====================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# =====================
# PUBLIC ROUTES
# =====================
@app.route('/')
def index():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM view_campaigncards ORDER BY "DaysLeft" ASC LIMIT 6')
    campaigns = rows_to_dicts(cur)
    cur.execute('SELECT * FROM view_recentdonations')
    recent = rows_to_dicts(cur)
    cur.execute('SELECT COUNT(*) FROM campaigns')
    total_campaigns = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM ngos WHERE "IsVerified"=true')
    verified_ngos = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(SUM("Amount"),0) FROM donations')
    total_raised = float(cur.fetchone()[0])
    conn.close()
    return render_template('index.html',
        campaigns=campaigns, recent=recent,
        total_campaigns=total_campaigns,
        verified_ngos=verified_ngos,
        total_raised=total_raised)

@app.route('/campaigns')
def campaigns():
    conn   = get_db()
    cur    = conn.cursor()
    search = request.args.get('q', '').strip()
    if search:
        cur.execute(
            'SELECT * FROM view_campaigncards WHERE "Title" ILIKE %s OR "Description" ILIKE %s ORDER BY "DaysLeft" ASC',
            (f'%{search}%', f'%{search}%')
        )
    else:
        cur.execute('SELECT * FROM view_campaigncards ORDER BY "DaysLeft" ASC')
    campaigns = rows_to_dicts(cur)
    conn.close()
    return render_template('campaigns.html', campaigns=campaigns, search=search)

@app.route('/campaign/<int:campaign_id>')
def campaign_detail(campaign_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM view_campaigncards WHERE "CampaignID" = %s', (campaign_id,))
    campaign = row_to_dict(cur, cur.fetchone())
    if not campaign:
        conn.close()
        flash('Campaign not found.', 'danger')
        return redirect(url_for('campaigns'))
    cur.execute('SELECT * FROM beneficiaries WHERE "CampaignID" = %s', (campaign_id,))
    beneficiaries = rows_to_dicts(cur)
    cur.execute("""
        SELECT u."FullName", d."Amount", d."DonationDate"
        FROM donations d
        JOIN users u ON d."DonorID" = u."UserID"
        WHERE d."CampaignID" = %s
        ORDER BY d."DonationDate" DESC
    """, (campaign_id,))
    donations = rows_to_dicts(cur)
    conn.close()
    return render_template('campaign_detail.html',
        campaign=campaign, beneficiaries=beneficiaries, donations=donations)

# =====================
# AUTH ROUTES
# =====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            'SELECT "UserID", "FullName", "UserRole", "PasswordHash" FROM users WHERE "Email" = %s', (email,)
        )
        user = cur.fetchone()
        conn.close()
        if user and user[3] == password:
            if user[2] == 'Admin':
                flash('Please use the Admin Portal to login.', 'warning')
                return redirect(url_for('admin_login'))
            session['user_id']   = user[0]
            session['full_name'] = user[1]
            session['role']      = user[2]
            flash(f'Welcome back, {user[1]}! 👋', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/admin-portal', methods=['GET', 'POST'])
def admin_login():
    if session.get('role') == 'Admin':
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        secret   = request.form.get('admin_secret', '')

        ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'HOPE@ADMIN2026')

        if secret != ADMIN_SECRET:
            flash('Invalid admin access code.', 'danger')
            return render_template('admin_login.html')

        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT \"UserID\", \"FullName\", \"UserRole\", \"PasswordHash\", \"ProfilePicture\" FROM users WHERE \"Email\"=%s AND \"UserRole\"='Admin'",
            (email,)
        )
        user = cur.fetchone()
        conn.close()
        if user and user[3] == password:
            session['user_id']         = user[0]
            session['full_name']       = user[1]
            session['role']            = user[2]
            session['profile_picture'] = user[4]
            flash(f'Welcome, Administrator {user[1]}! 🔐', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name        = request.form.get('full_name', '').strip()
        email            = request.form.get('email', '').strip()
        password         = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role             = request.form.get('role', 'Donor')
        mission          = request.form.get('mission', '').strip()
        tax_id           = request.form.get('tax_id', '').strip()

        if not full_name or not email or not password:
            flash('Please fill in all required fields.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html')

        if role == 'NGO' and not tax_id:
            flash('Tax ID is required for NGO registration.', 'danger')
            return render_template('register.html')

        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO users ("FullName", "Email", "PasswordHash", "UserRole") VALUES (%s,%s,%s,%s) RETURNING "UserID"',
                (full_name, email, password, role)
            )
            user_id = cur.fetchone()[0]
            if role == 'NGO':
                cur.execute(
                    'INSERT INTO ngos ("UserID", "Mission", "TaxID", "IsVerified") VALUES (%s,%s,%s,false)',
                    (user_id, mission, tax_id)
                )
            conn.commit()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Email or Tax ID already registered.', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Registration failed: {e}', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    name = session.get('full_name', '')
    session.clear()
    flash(f'Goodbye, {name}! You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current  = request.form.get('current_password', '')
        new_pw   = request.form.get('new_password', '')
        confirm  = request.form.get('confirm_password', '')

        if not current or not new_pw or not confirm:
            flash('Please fill in all fields.', 'danger')
            return render_template('change_password.html')
        if new_pw != confirm:
            flash('New passwords do not match.', 'danger')
            return render_template('change_password.html')
        if len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'danger')
            return render_template('change_password.html')

        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute('SELECT "PasswordHash" FROM users WHERE "UserID" = %s', (session['user_id'],))
            row = cur.fetchone()
            if not row or row[0] != current:
                flash('Current password is incorrect.', 'danger')
                return render_template('change_password.html')
            cur.execute('UPDATE users SET "PasswordHash" = %s WHERE "UserID" = %s', (new_pw, session['user_id']))
            conn.commit()
            flash('Password changed successfully! ✅', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Could not update password: {e}', 'danger')
        finally:
            conn.close()
    return render_template('change_password.html')

# =====================
# DASHBOARD ROUTER
# =====================
@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'Admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'NGO':
        return redirect(url_for('ngo_dashboard'))
    return redirect(url_for('donor_dashboard'))

# ========================================
# DONOR ROUTES
# ========================================
@app.route('/donor/dashboard')
@login_required
@role_required('Donor')
def donor_dashboard():
    uid  = session['user_id']
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM view_donorsummary WHERE "UserID" = %s', (uid,))
    summary = row_to_dict(cur, cur.fetchone())
    cur.execute("""
        SELECT c."Title", d."Amount", d."DonationDate", nu."FullName" AS "NGOName",
               c."CampaignID",
               (c."CurrentAmount" * 100.0 / c."TargetGoal") AS "ProgressPercent"
        FROM donations d
        JOIN campaigns c  ON d."CampaignID" = c."CampaignID"
        JOIN ngos n       ON c."NGOID" = n."NGOID"
        JOIN users nu     ON n."UserID" = nu."UserID"
        WHERE d."DonorID" = %s
        ORDER BY d."DonationDate" DESC
    """, (uid,))
    history = rows_to_dicts(cur)
    cur.execute("""
        SELECT COUNT(DISTINCT c."NGOID")
        FROM donations d
        JOIN campaigns c ON d."CampaignID" = c."CampaignID"
        WHERE d."DonorID" = %s
    """, (uid,))
    ngos_supported = cur.fetchone()[0]
    cur.execute('SELECT * FROM view_recentdonations')
    recent = rows_to_dicts(cur)
    cur.execute("""
        SELECT * FROM view_campaigncards
        WHERE "CampaignID" NOT IN (
            SELECT "CampaignID" FROM donations WHERE "DonorID" = %s
        )
        ORDER BY "DaysLeft" ASC
        LIMIT 3
    """, (uid,))
    suggested = rows_to_dicts(cur)
    conn.close()
    return render_template('donor/dashboard.html',
        summary=summary, history=history,
        ngos_supported=ngos_supported,
        recent=recent, suggested=suggested)

@app.route('/donor/profile', methods=['GET', 'POST'])
@login_required
@role_required('Donor')
def donor_profile():
    conn = get_db()
    cur  = conn.cursor()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone     = request.form.get('phone', '').strip()
        address   = request.form.get('address', '').strip()
        pic_filename = None

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"donor_{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                pic_filename = filename

        try:
            if pic_filename:
                cur.execute("""
                    UPDATE users SET "FullName"=%s, "Phone"=%s, "Address"=%s, "ProfilePicture"=%s
                    WHERE "UserID"=%s
                """, (full_name, phone, address, pic_filename, session['user_id']))
                session['profile_picture'] = pic_filename
            else:
                cur.execute("""
                    UPDATE users SET "FullName"=%s, "Phone"=%s, "Address"=%s
                    WHERE "UserID"=%s
                """, (full_name, phone, address, session['user_id']))
            conn.commit()
            session['full_name'] = full_name
            flash('Profile updated! ✅', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('donor_profile'))

    cur.execute("""
        SELECT "UserID", "FullName", "Email", "Phone", "Address", "ProfilePicture", "CreatedAt"
        FROM users WHERE "UserID" = %s
    """, (session['user_id'],))
    profile = row_to_dict(cur, cur.fetchone())
    conn.close()
    return render_template('donor/profile.html', profile=profile)

@app.route('/donate/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
@role_required('Donor')
def donate(campaign_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM view_campaigncards WHERE "CampaignID" = %s', (campaign_id,))
    campaign = row_to_dict(cur, cur.fetchone())
    if not campaign:
        conn.close()
        flash('Campaign not found.', 'danger')
        return redirect(url_for('campaigns'))
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount', 0))
            if amount <= 0:
                raise ValueError
            cur.execute(
                'INSERT INTO donations ("DonorID", "CampaignID", "Amount") VALUES (%s,%s,%s)',
                (session['user_id'], campaign_id, amount)
            )
            conn.commit()
            conn.close()
            flash(f'Thank you! Your donation of PKR {amount:,.0f} has been recorded. ❤', 'success')
            return redirect(url_for('campaign_detail', campaign_id=campaign_id))
        except ValueError:
            flash('Please enter a valid donation amount.', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Donation failed: {e}', 'danger')
    conn.close()
    return render_template('donor/donate.html', campaign=campaign)

# ========================================
# NGO ROUTES
# ========================================
def get_ngo_id(user_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT "NGOID", "IsVerified" FROM ngos WHERE "UserID" = %s', (user_id,))
    row = cur.fetchone()
    conn.close()
    return (row[0], bool(row[1])) if row else (None, False)

@app.route('/ngo/dashboard')
@login_required
@role_required('NGO')
def ngo_dashboard():
    ngo_id, is_verified = get_ngo_id(session['user_id'])
    if not ngo_id:
        flash('NGO profile not found.', 'danger')
        return redirect(url_for('index'))
    session['ngo_id'] = ngo_id
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT * FROM view_ngostats WHERE "NGOID" = %s', (ngo_id,))
    stats = row_to_dict(cur, cur.fetchone())
    cur.execute("""
        SELECT cc.*, c."StartDate", c."EndDate", c."NGOID"
        FROM view_campaigncompletion cc
        JOIN campaigns c ON cc."CampaignID" = c."CampaignID"
        WHERE c."NGOID" = %s
        ORDER BY c."StartDate" DESC
    """, (ngo_id,))
    campaigns = rows_to_dicts(cur)
    cur.execute("""
        SELECT u."FullName" AS "DonorName", c."Title" AS "CampaignTitle",
               d."Amount", d."DonationDate"
        FROM donations d
        JOIN users u ON d."DonorID" = u."UserID"
        JOIN campaigns c ON d."CampaignID" = c."CampaignID"
        WHERE c."NGOID" = %s
        ORDER BY d."DonationDate" DESC
        LIMIT 5
    """, (ngo_id,))
    recent_donations = rows_to_dicts(cur)
    conn.close()
    return render_template('ngo/dashboard.html',
        stats=stats, campaigns=campaigns,
        is_verified=is_verified,
        recent_donations=recent_donations)

@app.route('/ngo/campaign/create', methods=['GET', 'POST'])
@login_required
@role_required('NGO')
def ngo_create_campaign():
    ngo_id, is_verified = get_ngo_id(session['user_id'])
    if not is_verified:
        flash('Your NGO must be verified by an Admin before creating campaigns.', 'warning')
        return redirect(url_for('ngo_dashboard'))
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        start_date  = request.form.get('start_date', '')
        end_date    = request.form.get('end_date', '')
        try:
            target_goal = float(request.form.get('target_goal', 0))
            if target_goal <= 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid fundraising goal.', 'danger')
            return render_template('ngo/create_campaign.html')
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO campaigns
                    ("NGOID", "Title", "Description", "TargetGoal", "CurrentAmount", "StartDate", "EndDate")
                VALUES (%s,%s,%s,%s,0,%s,%s)
            """, (ngo_id, title, description, target_goal, start_date, end_date))
            conn.commit()
            flash('Campaign launched successfully! 🎉', 'success')
            return redirect(url_for('ngo_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'Could not create campaign: {e}', 'danger')
        finally:
            conn.close()
    return render_template('ngo/create_campaign.html')

@app.route('/ngo/campaign/edit/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
@role_required('NGO')
def ngo_edit_campaign(campaign_id):
    ngo_id, _ = get_ngo_id(session['user_id'])
    conn = get_db()
    cur  = conn.cursor()
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        end_date    = request.form.get('end_date', '')
        try:
            target_goal = float(request.form.get('target_goal', 0))
        except ValueError:
            flash('Invalid goal amount.', 'danger')
            conn.close()
            return redirect(url_for('ngo_edit_campaign', campaign_id=campaign_id))
        try:
            cur.execute("""
                UPDATE campaigns
                SET "Title"=%s, "Description"=%s, "TargetGoal"=%s, "EndDate"=%s
                WHERE "CampaignID"=%s AND "NGOID"=%s
            """, (title, description, target_goal, end_date, campaign_id, ngo_id))
            conn.commit()
            flash('Campaign updated! ✅', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('ngo_dashboard'))
    cur.execute('SELECT * FROM campaigns WHERE "CampaignID"=%s AND "NGOID"=%s', (campaign_id, ngo_id))
    campaign = row_to_dict(cur, cur.fetchone())
    conn.close()
    if not campaign:
        flash('Campaign not found.', 'danger')
        return redirect(url_for('ngo_dashboard'))
    return render_template('ngo/edit_campaign.html', campaign=campaign)

@app.route('/ngo/campaign/delete/<int:campaign_id>', methods=['POST'])
@login_required
@role_required('NGO')
def ngo_delete_campaign(campaign_id):
    ngo_id, _ = get_ngo_id(session['user_id'])
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute('DELETE FROM campaigns WHERE "CampaignID"=%s AND "NGOID"=%s', (campaign_id, ngo_id))
        conn.commit()
        flash('Campaign deleted.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Delete failed: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('ngo_dashboard'))

@app.route('/ngo/beneficiary/add/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
@role_required('NGO')
def add_beneficiary(campaign_id):
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        details = request.form.get('details', '').strip()
        if not name:
            flash('Beneficiary name is required.', 'danger')
            return render_template('ngo/add_beneficiary.html', campaign_id=campaign_id)
        conn = get_db()
        cur  = conn.cursor()
        try:
            cur.execute(
                'INSERT INTO beneficiaries ("CampaignID", "BeneficiaryName", "Details") VALUES (%s,%s,%s)',
                (campaign_id, name, details)
            )
            conn.commit()
            flash('Beneficiary added! ✅', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('ngo_dashboard'))
    return render_template('ngo/add_beneficiary.html', campaign_id=campaign_id)

@app.route('/ngo/profile', methods=['GET', 'POST'])
@login_required
@role_required('NGO')
def ngo_profile():
    conn = get_db()
    cur  = conn.cursor()
    if request.method == 'POST':
        mission   = request.form.get('mission', '').strip()
        full_name = request.form.get('full_name', '').strip()
        phone     = request.form.get('phone', '').strip()
        address   = request.form.get('address', '').strip()
        pic_filename = None

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"ngo_{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                pic_filename = filename

        try:
            if pic_filename:
                cur.execute("""
                    UPDATE ngos SET "Mission"=%s, "Phone"=%s, "Address"=%s, "ProfilePicture"=%s
                    WHERE "UserID"=%s
                """, (mission, phone, address, pic_filename, session['user_id']))
                session['profile_picture'] = pic_filename
            else:
                cur.execute("""
                    UPDATE ngos SET "Mission"=%s, "Phone"=%s, "Address"=%s
                    WHERE "UserID"=%s
                """, (mission, phone, address, session['user_id']))
            cur.execute('UPDATE users SET "FullName"=%s WHERE "UserID"=%s', (full_name, session['user_id']))
            conn.commit()
            session['full_name'] = full_name
            flash('Profile updated! ✅', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('ngo_profile'))

    cur.execute("""
        SELECT u."FullName", u."Email", n."Mission", n."TaxID", n."IsVerified",
               n."Phone", n."Address", n."ProfilePicture"
        FROM users u
        JOIN ngos n ON u."UserID" = n."UserID"
        WHERE u."UserID" = %s
    """, (session['user_id'],))
    profile = row_to_dict(cur, cur.fetchone())
    conn.close()
    return render_template('ngo/profile.html', profile=profile)

# ========================================
# ADMIN ROUTES
# ========================================
@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def admin_profile():
    conn = get_db()
    cur  = conn.cursor()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone     = request.form.get('phone', '').strip()
        address   = request.form.get('address', '').strip()
        pic_filename = None

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"admin_{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                pic_filename = filename

        try:
            if pic_filename:
                cur.execute("""
                    UPDATE users SET "FullName"=%s, "Phone"=%s, "Address"=%s, "ProfilePicture"=%s
                    WHERE "UserID"=%s
                """, (full_name, phone, address, pic_filename, session['user_id']))
                session['profile_picture'] = pic_filename
            else:
                cur.execute("""
                    UPDATE users SET "FullName"=%s, "Phone"=%s, "Address"=%s
                    WHERE "UserID"=%s
                """, (full_name, phone, address, session['user_id']))
            conn.commit()
            session['full_name'] = full_name
            flash('Profile updated! ✅', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Update failed: {e}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('admin_profile'))

    cur.execute("""
        SELECT "UserID", "FullName", "Email", "Phone", "Address", "ProfilePicture", "CreatedAt"
        FROM users WHERE "UserID" = %s
    """, (session['user_id'],))
    profile = row_to_dict(cur, cur.fetchone())
    conn.close()
    return render_template('admin/profile.html', profile=profile)

@app.route('/admin/dashboard')
@login_required
@role_required('Admin')
def admin_dashboard():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE \"UserRole\"='Donor'")
    total_donors = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM campaigns')
    total_campaigns = cur.fetchone()[0]
    cur.execute('SELECT COALESCE(SUM("Amount"),0) FROM donations')
    total_donated = float(cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM ngos WHERE "IsVerified"=true')
    verified_ngos = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM ngos WHERE "IsVerified"=false')
    pending_ngos = cur.fetchone()[0]
    cur.execute("""
        SELECT n."NGOID", u."FullName", u."Email", n."TaxID", n."IsVerified", n."Mission"
        FROM ngos n JOIN users u ON n."UserID" = u."UserID"
        ORDER BY n."IsVerified" ASC, u."FullName"
    """)
    ngos = rows_to_dicts(cur)
    cur.execute('SELECT * FROM view_recentdonations')
    recent_donations = rows_to_dicts(cur)
    cur.execute('SELECT "UserID", "FullName", "Email", "UserRole", "CreatedAt" FROM users ORDER BY "CreatedAt" DESC')
    users = rows_to_dicts(cur)
    cur.execute('SELECT * FROM view_ngostats ORDER BY "TotalRaised" DESC')
    ngo_stats = rows_to_dicts(cur)
    cur.execute("""
        SELECT c."CampaignID", c."Title", c."TargetGoal", c."CurrentAmount",
               (c."CurrentAmount" * 100.0 / c."TargetGoal") AS "ProgressPercent",
               u."FullName" AS "NGOName", c."StartDate", c."EndDate"
        FROM campaigns c
        JOIN ngos n  ON c."NGOID" = n."NGOID"
        JOIN users u ON n."UserID" = u."UserID"
        ORDER BY c."StartDate" DESC
    """)
    all_campaigns = rows_to_dicts(cur)
    conn.close()
    return render_template('admin/dashboard.html',
        total_users=total_users, total_donors=total_donors,
        total_campaigns=total_campaigns, total_donated=total_donated,
        verified_ngos=verified_ngos, pending_ngos=pending_ngos,
        ngos=ngos, recent_donations=recent_donations,
        users=users, ngo_stats=ngo_stats, all_campaigns=all_campaigns)

@app.route('/admin/ngo/verify/<int:ngo_id>', methods=['POST'])
@login_required
@role_required('Admin')
def verify_ngo(ngo_id):
    action = request.form.get('action')
    val    = True if action == 'approve' else False
    conn   = get_db()
    cur    = conn.cursor()
    try:
        cur.execute('UPDATE ngos SET "IsVerified"=%s WHERE "NGOID"=%s', (val, ngo_id))
        conn.commit()
        flash('NGO approved! ✅' if val else 'NGO verification revoked.', 'success' if val else 'warning')
    except Exception as e:
        conn.rollback()
        flash(f'Action failed: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard') + '#ngos')

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin')
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_dashboard'))
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute('DELETE FROM users WHERE "UserID"=%s', (user_id,))
        conn.commit()
        flash('User deleted.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Delete failed: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard') + '#users')

@app.route('/admin/campaign/delete/<int:campaign_id>', methods=['POST'])
@login_required
@role_required('Admin')
def admin_delete_campaign(campaign_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute('DELETE FROM campaigns WHERE "CampaignID"=%s', (campaign_id,))
        conn.commit()
        flash('Campaign removed.', 'info')
    except Exception as e:
        conn.rollback()
        flash(f'Delete failed: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard') + '#campaigns')

@app.route('/api/campaign/<int:campaign_id>/progress')
def api_campaign_progress(campaign_id):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT "CurrentAmount", "TargetGoal",
               ("CurrentAmount" * 100.0 / "TargetGoal") AS "ProgressPercent"
        FROM campaigns WHERE "CampaignID" = %s
    """, (campaign_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'current': float(row[0]),
        'goal':    float(row[1]),
        'percent': round(float(row[2]), 2)
    })

if __name__ == '__main__':
    app.run(debug=os.environ.get('DEBUG', 'False').lower() == 'true')
