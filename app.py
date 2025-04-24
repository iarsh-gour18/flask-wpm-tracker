from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone, UTC
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import random
from sqlalchemy import func

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///typemaster.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_photo = db.Column(db.String(255), default='default.jpg')
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    preferred_language = db.Column(db.String(10), default='en')
    keyboard_layout = db.Column(db.String(20), default='qwerty')
    daily_goal = db.Column(db.Integer, default=30)  # minutes
    last_practice = db.Column(db.DateTime)
    streak_days = db.Column(db.Integer, default=0)
    theme = db.Column(db.String(10), default='light')  # light/dark mode
    font_size = db.Column(db.Integer, default=16)  # in pixels
    high_contrast = db.Column(db.Boolean, default=False)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    privacy_settings = db.Column(db.JSON, default=lambda: {
        'show_profile': True,
        'show_stats': True,
        'show_achievements': True
    })
    tests = db.relationship('TypingTest', backref='user', lazy=True)
    achievements = db.relationship('UserAchievement', backref='user', lazy=True)
    practice_goals = db.relationship('PracticeGoal', backref='user', lazy=True)
    friends = db.relationship('Friendship', 
                            foreign_keys='Friendship.user_id',
                            backref='user', lazy=True)
    friend_of = db.relationship('Friendship',
                              foreign_keys='Friendship.friend_id',
                              backref='friend', lazy=True)
    custom_practices = db.relationship('CustomPractice', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class TypingTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wpm = db.Column(db.Float, nullable=False)
    accuracy = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    test_type = db.Column(db.String(20), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    language = db.Column(db.String(10), default='en')
    mistake_patterns = db.Column(db.JSON)
    duration = db.Column(db.Integer)
    points = db.Column(db.Integer, default=0)
    test_content = db.Column(db.Text)  # Store the actual text that was tested

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(255))
    criteria = db.Column(db.JSON)  # Store achievement requirements

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)
    achievement = db.relationship('Achievement')

class PracticeGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    goal_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    target_minutes = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)

class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CustomPractice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)

class DailyChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='medium')
    reward_points = db.Column(db.Integer, default=100)
    completions = db.Column(db.Integer, default=0)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    entry_fee = db.Column(db.Integer, default=0)
    prize_pool = db.Column(db.Integer, default=0)
    max_participants = db.Column(db.Integer)
    participants = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='upcoming')  # upcoming, active, completed

class TournamentParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    rank = db.Column(db.Integer)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

# Add practice content
PRACTICE_CONTENT = {
    'common_words': [
        "the be to of and a in that have I it for not on with he as you do at this but his by from",
        "they we say her she or an will my one all would there their what so up out if about who",
        "get which go she him after that into her then think come here over when again around both",
        "between each few more most other some such than that these through under until very while"
    ],
    'numbers_symbols': [
        "1234567890 !@#$%^&*()_+-=[]{}|;:'\",.<>/?",
        "1st 2nd 3rd 4th 5th 6th 7th 8th 9th 10th",
        "100 200 300 400 500 600 700 800 900 1000",
        "1+1=2 2+2=4 3+3=6 4+4=8 5+5=10 6+6=12 7+7=14 8+8=16 9+9=18 10+10=20"
    ],
    'programming': [
        "function helloWorld() { console.log('Hello, World!'); }",
        "for (let i = 0; i < 10; i++) { console.log(i); }",
        "const sum = (a, b) => a + b; console.log(sum(5, 3));",
        "class Person { constructor(name) { this.name = name; } }"
    ]
}

# Add achievement definitions
ACHIEVEMENTS = [
    {
        'name': 'First Steps',
        'description': 'Complete your first typing test',
        'criteria': {'tests_completed': 1}
    },
    {
        'name': 'Speed Demon',
        'description': 'Achieve 60 WPM in a test',
        'criteria': {'wpm': 60}
    },
    {
        'name': 'Accuracy Master',
        'description': 'Achieve 95% accuracy in a test',
        'criteria': {'accuracy': 95}
    },
    {
        'name': 'Consistent Practice',
        'description': 'Practice for 7 days in a row',
        'criteria': {'streak_days': 7}
    }
]

# Add more typing test content for variety
TYPING_TEST_CONTENT = [
    "The quick brown fox jumps over the lazy dog. This pangram contains every letter of the English alphabet at least once. Pangrams are often used to display font samples and test keyboards.",
    "In a world where technology is rapidly evolving, the ability to type quickly and accurately is becoming increasingly important. Practice makes perfect when it comes to improving your typing skills.",
    "Programming requires attention to detail. Every character, every semicolon, and every bracket matters. Good typing skills can significantly improve your coding efficiency and reduce errors.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. These words by Winston Churchill remind us that persistence is key to achieving our goals.",
    "The best way to predict the future is to create it. Technology and innovation are shaping our world, and those who can adapt quickly will thrive in this digital age.",
    "Learning to type efficiently is like learning to play a musical instrument. It requires practice, dedication, and the right technique. Start slow, focus on accuracy, and speed will follow naturally.",
    "The internet has revolutionized how we communicate, work, and learn. Being able to type quickly and accurately is no longer just a skill for secretaries - it's essential for everyone.",
    "Practice makes perfect. The more you type, the better you become. Focus on maintaining good posture, keeping your fingers on the home row, and looking at the screen instead of your hands.",
    "Coding is the language of the future. Every line of code you write is a step towards creating something new. Efficient typing skills can help you focus more on problem-solving and less on typing.",
    "Your typing journey is unique to you. Don't compare your progress to others. Focus on improving your own speed and accuracy, and celebrate your personal achievements along the way."
]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            return render_template('signup.html', error='Email already registered')
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get user's stats for today
        today = datetime.now(UTC).date()
        today_tests = TypingTest.query.filter(
            TypingTest.user_id == current_user.id,
            func.date(TypingTest.timestamp) == today
        ).all()
        
        # Get all-time stats
        all_tests = TypingTest.query.filter_by(user_id=current_user.id).all()
        recent_tests = TypingTest.query.filter_by(user_id=current_user.id).order_by(TypingTest.timestamp.desc()).limit(5).all()
        
        # Calculate stats
        stats = {
            'best_wpm': 0,
            'avg_wpm': 0,
            'avg_accuracy': 0,
            'total_tests': len(all_tests),
            'tests_today': len(today_tests),
            'practice_minutes': sum(t.duration for t in today_tests) // 60 if today_tests else 0,
            'daily_goal_progress': 0,
            'current_streak': current_user.streak_days
        }
        
        if all_tests:
            stats.update({
                'best_wpm': max(t.wpm for t in all_tests),
                'avg_wpm': sum(t.wpm for t in all_tests) / len(all_tests),
                'avg_accuracy': sum(t.accuracy for t in all_tests) / len(all_tests)
            })
        
        if current_user.daily_goal > 0:
            stats['daily_goal_progress'] = (stats['practice_minutes'] / current_user.daily_goal * 100)
        
        # Round floating point numbers
        stats['best_wpm'] = round(stats['best_wpm'], 1)
        stats['avg_wpm'] = round(stats['avg_wpm'], 1)
        stats['avg_accuracy'] = round(stats['avg_accuracy'], 1)
        stats['daily_goal_progress'] = round(stats['daily_goal_progress'], 1)
        
        return render_template('dashboard.html', stats=stats, recent_tests=recent_tests)
        
    except Exception as e:
        print(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard: ' + str(e), 'error')
        return redirect(url_for('index'))

@app.route('/typing-test')
@login_required
def typing_test():
    # Get recent tests to avoid repeating texts
    recent_tests = TypingTest.query.filter_by(user_id=current_user.id).order_by(TypingTest.timestamp.desc()).limit(3).all()
    recent_texts = [test.test_content for test in recent_tests if test.test_content]
    
    # Filter out recently used texts
    available_texts = [text for text in TYPING_TEST_CONTENT if text not in recent_texts]
    if len(available_texts) < 5:  # If not enough unique texts
        available_texts = TYPING_TEST_CONTENT
    
    # Select 5 random texts
    test_texts = random.sample(available_texts, min(5, len(available_texts)))
    
    return render_template('typing_test.html', 
                         test_text=test_texts[0],
                         test_texts=test_texts,
                         previous_tests=recent_tests)

@app.route('/practice/<practice_type>')
@login_required
def practice(practice_type):
    practice_texts = {
        'common_words': [
            "The quick brown fox jumps over the lazy dog.",
            "Pack my box with five dozen liquor jugs.",
            "How vexingly quick daft zebras jump!",
            "The five boxing wizards jump quickly.",
            "Sphinx of black quartz, judge my vow."
        ],
        'numbers': [
            "12345 67890 98765 43210",
            "1st 2nd 3rd 4th 5th 6th 7th 8th 9th 10th",
            "100% 75% 50% 25% 0% $100.00 €50.00 £25.00",
            "Chapter 1, Page 2, Section 3, Part 4",
            "Phone: +1-234-567-8900 Ext. 12345"
        ],
        'programming': [
            "def hello_world(): print('Hello, World!')",
            "for i in range(10): total += numbers[i]",
            "if (condition) { return true; } else { return false; }",
            "SELECT * FROM users WHERE age >= 18 ORDER BY name;",
            "<div class='container'><p>Hello World</p></div>"
        ]
    }
    
    if practice_type not in practice_texts:
        return redirect(url_for('typing_test'))
    
    return render_template('typing_test.html',
                         test_texts=practice_texts[practice_type],
                         practice_type=practice_type)

def check_user_achievements(user_id, test_result):
    # Get user's stats
    user = User.query.get(user_id)
    if not user:
        return None
        
    # Calculate user stats
    tests_completed = TypingTest.query.filter_by(user_id=user_id).count()
    best_wpm = db.session.query(func.max(TypingTest.wpm)).filter_by(user_id=user_id).scalar() or 0
    best_accuracy = db.session.query(func.max(TypingTest.accuracy)).filter_by(user_id=user_id).scalar() or 0
    
    # Check for achievements
    if test_result.wpm >= 100:
        return {'name': 'Speed Demon', 'description': 'Achieved 100+ WPM!'}
    elif test_result.wpm >= 80:
        return {'name': 'Fast Typer', 'description': 'Achieved 80+ WPM!'}
    elif test_result.wpm >= 60:
        return {'name': 'Quick Fingers', 'description': 'Achieved 60+ WPM!'}
    
    if test_result.accuracy >= 98:
        return {'name': 'Perfect Accuracy', 'description': 'Achieved 98%+ accuracy!'}
    elif test_result.accuracy >= 95:
        return {'name': 'Sharp Shooter', 'description': 'Achieved 95%+ accuracy!'}
    
    if user.streak_days >= 7:
        return {'name': 'Consistent', 'description': '7 day practice streak!'}
    elif user.streak_days >= 3:
        return {'name': 'Regular', 'description': '3 day practice streak!'}
    
    return None

def get_user_best_wpm(user_id):
    best_test = TypingTest.query.filter_by(user_id=user_id).order_by(TypingTest.wpm.desc()).first()
    return best_test.wpm if best_test else 0

@app.route('/save-test-result', methods=['POST'])
@login_required
def save_test_result():
    try:
        data = request.get_json()
        
        # Validate the data
        wpm = float(data['wpm'])
        accuracy = float(data['accuracy'])
        duration = int(data['duration'])
        test_content = data['test_content']
        
        if not test_content or wpm < 0 or accuracy < 0 or accuracy > 100 or duration <= 0:
            return jsonify({'success': False, 'error': 'Invalid test data'}), 400
        
        # Create new test result
        test_result = TypingTest(
            user_id=current_user.id,
            wpm=wpm,
            accuracy=accuracy,
            duration=duration,
            test_content=test_content,
            timestamp=datetime.now(UTC),
            test_type='standard',
            difficulty='medium'
        )
        db.session.add(test_result)
        
        # Update user's stats
        today = datetime.now(UTC).date()
        if current_user.last_practice is None:
            current_user.streak_days = 1
        elif current_user.last_practice.date() < today:
            if (today - current_user.last_practice.date()).days == 1:
                current_user.streak_days += 1
            else:
                current_user.streak_days = 1
        
        current_user.last_practice = datetime.now(UTC)
        
        # Get user's best WPM
        best_wpm = db.session.query(func.max(TypingTest.wpm)).filter_by(user_id=current_user.id).scalar() or 0
        
        # Check for achievements
        achievement = check_user_achievements(current_user.id, test_result)
        
        # Commit all changes
        db.session.commit()
        
        # Get updated stats for response
        today_tests = TypingTest.query.filter(
            TypingTest.user_id == current_user.id,
            func.date(TypingTest.timestamp) == today
        ).all()
        
        all_tests = TypingTest.query.filter_by(user_id=current_user.id).all()
        
        avg_wpm = sum(t.wpm for t in all_tests) / len(all_tests) if all_tests else 0
        avg_accuracy = sum(t.accuracy for t in all_tests) / len(all_tests) if all_tests else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'wpm': round(wpm, 1),
                'accuracy': round(accuracy, 1),
                'previous_best': round(best_wpm, 1),
                'current_streak': current_user.streak_days,
                'avg_wpm': round(avg_wpm, 1),
                'avg_accuracy': round(avg_accuracy, 1),
                'total_tests': len(all_tests),
                'tests_today': len(today_tests),
                'practice_minutes': sum(t.duration for t in today_tests) // 60
            },
            'achievement': achievement
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error saving test result: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/progress')
@login_required
def progress():
    # Get all user's tests
    tests = TypingTest.query.filter_by(user_id=current_user.id).order_by(TypingTest.timestamp.desc()).all()
    
    # Calculate daily averages
    daily_stats = {}
    for test in tests:
        date = test.timestamp.date()
        if date not in daily_stats:
            daily_stats[date] = {
                'wpm': [],
                'accuracy': [],
                'tests': 0,
                'minutes': 0
            }
        daily_stats[date]['wpm'].append(test.wpm)
        daily_stats[date]['accuracy'].append(test.accuracy)
        daily_stats[date]['tests'] += 1
        daily_stats[date]['minutes'] += test.duration // 60
    
    # Calculate averages
    for date in daily_stats:
        daily_stats[date]['avg_wpm'] = sum(daily_stats[date]['wpm']) / len(daily_stats[date]['wpm'])
        daily_stats[date]['avg_accuracy'] = sum(daily_stats[date]['accuracy']) / len(daily_stats[date]['accuracy'])
    
    # Sort by date
    sorted_stats = sorted(daily_stats.items(), key=lambda x: x[0], reverse=True)
    
    # Calculate overall stats
    if tests:
        overall_stats = {
            'avg_wpm': sum([test.wpm for test in tests]) / len(tests),
            'avg_accuracy': sum([test.accuracy for test in tests]) / len(tests),
            'total_tests': len(tests),
            'total_time': sum([test.duration for test in tests]) // 60,
            'best_wpm': max([test.wpm for test in tests]),
            'best_accuracy': max([test.accuracy for test in tests])
        }
    else:
        overall_stats = {
            'avg_wpm': 0,
            'avg_accuracy': 0,
            'total_tests': 0,
            'total_time': 0,
            'best_wpm': 0,
            'best_accuracy': 0
        }
    
    return render_template('progress.html', 
                         daily_stats=sorted_stats,
                         overall_stats=overall_stats,
                         tests=tests)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            if 'profile_photo' in request.files:
                file = request.files['profile_photo']
                if file and allowed_file(file.filename):
                    filename = secure_filename(f"{current_user.id}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    current_user.profile_photo = filename
            
            current_user.full_name = request.form.get('full_name', current_user.full_name)
            current_user.bio = request.form.get('bio', current_user.bio)
            
            # Handle password change
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if current_password and new_password:
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('profile'))
                
                current_user.set_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile: ' + str(e), 'error')
        
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/upload-profile-photo', methods=['POST'])
@login_required
def upload_profile_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.id}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        current_user.profile_photo = filename
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    current_user.full_name = data.get('full_name', current_user.full_name)
    current_user.bio = data.get('bio', current_user.bio)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/update-settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    current_user.theme = data.get('theme', current_user.theme)
    current_user.font_size = data.get('font_size', current_user.font_size)
    current_user.high_contrast = data.get('high_contrast', current_user.high_contrast)
    
    if data.get('two_factor'):
        if not current_user.two_factor_enabled:
            # Generate and store 2FA secret
            current_user.two_factor_secret = generate_2fa_secret()
        current_user.two_factor_enabled = True
    else:
        current_user.two_factor_enabled = False
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/add-friend', methods=['POST'])
@login_required
def add_friend():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    friend = User.query.filter_by(username=username).first()
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    
    if friend.id == current_user.id:
        return jsonify({'error': 'Cannot add yourself as a friend'}), 400
    
    # Check if friendship already exists
    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend.id)) |
        ((Friendship.user_id == friend.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if existing:
        return jsonify({'error': 'Friendship already exists'}), 400
    
    friendship = Friendship(user_id=current_user.id, friend_id=friend.id)
    db.session.add(friendship)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/remove-friend/<int:friend_id>', methods=['DELETE'])
@login_required
def remove_friend(friend_id):
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)) |
        ((Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if not friendship:
        return jsonify({'error': 'Friendship not found'}), 404
    
    db.session.delete(friendship)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/challenge-friend/<int:friend_id>', methods=['POST'])
@login_required
def challenge_friend(friend_id):
    friend = User.query.get(friend_id)
    if not friend:
        return jsonify({'error': 'Friend not found'}), 404
    
    # Create a new typing test session for the challenge
    test = TypingTest(
        user_id=current_user.id,
        opponent_id=friend_id,
        is_challenge=True,
        status='pending'
    )
    db.session.add(test)
    db.session.commit()
    
    return jsonify({'success': True, 'test_id': test.id})

@app.route('/create-custom-practice', methods=['POST'])
@login_required
def create_custom_practice():
    data = request.get_json()
    practice = CustomPractice(
        user_id=current_user.id,
        title=data.get('title'),
        content=data.get('content'),
        difficulty=data.get('difficulty', 'medium'),
        is_public=data.get('is_public', False)
    )
    db.session.add(practice)
    db.session.commit()
    
    return jsonify({'success': True, 'practice_id': practice.id})

@app.route('/edit-custom-practice/<int:practice_id>', methods=['PUT'])
@login_required
def edit_custom_practice(practice_id):
    practice = CustomPractice.query.get(practice_id)
    if not practice or practice.user_id != current_user.id:
        return jsonify({'error': 'Practice not found'}), 404
    
    data = request.get_json()
    practice.title = data.get('title', practice.title)
    practice.content = data.get('content', practice.content)
    practice.difficulty = data.get('difficulty', practice.difficulty)
    practice.is_public = data.get('is_public', practice.is_public)
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete-custom-practice/<int:practice_id>', methods=['DELETE'])
@login_required
def delete_custom_practice(practice_id):
    practice = CustomPractice.query.get(practice_id)
    if not practice or practice.user_id != current_user.id:
        return jsonify({'error': 'Practice not found'}), 404
    
    db.session.delete(practice)
    db.session.commit()
    return jsonify({'success': True})

def generate_2fa_secret():
    # Implement 2FA secret generation
    return 'dummy_secret'  # Replace with actual 2FA implementation

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/complete-practice', methods=['POST'])
@login_required
def complete_practice():
    data = request.get_json()
    practice_type = data.get('practice_type')
    minutes = data.get('minutes', 0)
    
    if practice_type and minutes > 0:
        # Update practice goals
        today = datetime.utcnow().date()
        daily_goal = PracticeGoal.query.filter_by(
            user_id=current_user.id,
            goal_type='daily',
            start_date=today
        ).first()
        
        if daily_goal:
            daily_goal.completed = minutes >= daily_goal.target_minutes
            db.session.commit()
        
        # Update streak
        if current_user.last_practice:
            last_practice_date = current_user.last_practice.date()
            if (today - last_practice_date).days == 1:
                current_user.streak_days += 1
            elif (today - last_practice_date).days > 1:
                current_user.streak_days = 1
        else:
            current_user.streak_days = 1
        
        current_user.last_practice = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Invalid data'}), 400

@app.route('/set-goal', methods=['POST'])
@login_required
def set_goal():
    data = request.get_json()
    goal = PracticeGoal(
        user_id=current_user.id,
        goal_type=data['type'],
        target_minutes=data['minutes'],
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=1 if data['type'] == 'daily' else 7)
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/check-achievements')
@login_required
def check_achievements():
    user_stats = {
        'tests_completed': TypingTest.query.filter_by(user_id=current_user.id).count(),
        'best_wpm': db.session.query(db.func.max(TypingTest.wpm)).filter_by(user_id=current_user.id).scalar() or 0,
        'best_accuracy': db.session.query(db.func.max(TypingTest.accuracy)).filter_by(user_id=current_user.id).scalar() or 0,
        'streak_days': current_user.streak_days
    }
    
    new_achievements = []
    for achievement in ACHIEVEMENTS:
        if not UserAchievement.query.filter_by(user_id=current_user.id, 
                                            achievement_id=achievement['id']).first():
            if all(user_stats[k] >= v for k, v in achievement['criteria'].items()):
                user_achievement = UserAchievement(
                    user_id=current_user.id,
                    achievement_id=achievement['id']
                )
                db.session.add(user_achievement)
                new_achievements.append(achievement['name'])
    
    if new_achievements:
        db.session.commit()
    
    return jsonify({'new_achievements': new_achievements})

@app.route('/challenges')
@login_required
def challenges():
    current_date = datetime.utcnow().date()
    daily_challenge = DailyChallenge.query.filter_by(date=current_date).first()
    
    active_tournaments = Tournament.query.filter(
        Tournament.status == 'active',
        Tournament.start_date <= datetime.utcnow(),
        Tournament.end_date > datetime.utcnow()
    ).all()
    
    upcoming_tournaments = Tournament.query.filter(
        Tournament.status == 'upcoming',
        Tournament.start_date > datetime.utcnow()
    ).order_by(Tournament.start_date).all()
    
    # Check which tournaments the user is participating in
    for tournament in active_tournaments:
        tournament.user_participating = TournamentParticipant.query.filter_by(
            tournament_id=tournament.id,
            user_id=current_user.id
        ).first() is not None
    
    return render_template('challenges.html',
                         daily_challenge=daily_challenge,
                         active_tournaments=active_tournaments,
                         upcoming_tournaments=upcoming_tournaments,
                         current_date=current_date)

@app.route('/start-daily-challenge', methods=['POST'])
@login_required
def start_daily_challenge():
    current_date = datetime.utcnow().date()
    challenge = DailyChallenge.query.filter_by(date=current_date).first()
    
    if not challenge:
        return jsonify({'error': 'No challenge available for today'}), 404
    
    # Check if user has already completed today's challenge
    if TypingTest.query.filter_by(
        user_id=current_user.id,
        test_type='daily_challenge',
        timestamp=current_date
    ).first():
        return jsonify({'error': 'You have already completed today\'s challenge'}), 400
    
    return jsonify({'success': True, 'challenge_id': challenge.id})

@app.route('/create-tournament', methods=['POST'])
@login_required
def create_tournament():
    data = request.get_json()
    
    # Validate entry fee
    if data.get('entry_fee', 0) < 0:
        return jsonify({'error': 'Entry fee cannot be negative'}), 400
    
    # Validate max participants
    if data.get('max_participants', 0) < 2:
        return jsonify({'error': 'Tournament must have at least 2 participants'}), 400
    
    # Validate start date
    start_date = datetime.fromisoformat(data.get('start_date'))
    if start_date <= datetime.utcnow():
        return jsonify({'error': 'Start date must be in the future'}), 400
    
    # Calculate end date
    duration_hours = int(data.get('duration', 1))
    end_date = start_date + timedelta(hours=duration_hours)
    
    tournament = Tournament(
        name=data.get('name'),
        description=data.get('description'),
        start_date=start_date,
        end_date=end_date,
        entry_fee=data.get('entry_fee', 0),
        max_participants=data.get('max_participants'),
        status='upcoming'
    )
    
    db.session.add(tournament)
    db.session.commit()
    
    return jsonify({'success': True, 'tournament_id': tournament.id})

@app.route('/join-tournament/<int:tournament_id>', methods=['POST'])
@login_required
def join_tournament(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    
    if tournament.status != 'active':
        return jsonify({'error': 'Tournament is not active'}), 400
    
    if tournament.participants >= tournament.max_participants:
        return jsonify({'error': 'Tournament is full'}), 400
    
    # Check if user is already participating
    if TournamentParticipant.query.filter_by(
        tournament_id=tournament_id,
        user_id=current_user.id
    ).first():
        return jsonify({'error': 'You are already participating in this tournament'}), 400
    
    # Check if user has enough points
    if current_user.points < tournament.entry_fee:
        return jsonify({'error': 'Not enough points to join'}), 400
    
    # Deduct entry fee
    current_user.points -= tournament.entry_fee
    tournament.prize_pool += tournament.entry_fee
    tournament.participants += 1
    
    participant = TournamentParticipant(
        tournament_id=tournament_id,
        user_id=current_user.id
    )
    
    db.session.add(participant)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/leave-tournament/<int:tournament_id>', methods=['POST'])
@login_required
def leave_tournament(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    
    if tournament.status != 'active':
        return jsonify({'error': 'Cannot leave a non-active tournament'}), 400
    
    participant = TournamentParticipant.query.filter_by(
        tournament_id=tournament_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        return jsonify({'error': 'You are not participating in this tournament'}), 400
    
    # Refund entry fee
    current_user.points += tournament.entry_fee
    tournament.prize_pool -= tournament.entry_fee
    tournament.participants -= 1
    
    db.session.delete(participant)
    db.session.commit()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 