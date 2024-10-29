from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from models import db, User, Person, Experience
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///people.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 创建所有数据库表
with app.app_context():
    db.create_all()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home():
    # 只获取当前用户的人员信息
    people = Person.query.filter_by(user_id=session['user_id']).order_by(Person.id.desc()).all()
    return render_template('index.html', username=session.get('username'), people=people)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('两次输入的密码不一致')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('register'))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('注册成功，请登录')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = username
            flash('登录成功！')
            return redirect(url_for('home'))
        else:
            flash('用户名或密码错误，请重试。')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录')
    return redirect(url_for('login'))

@app.route('/person/add', methods=['GET'])
@login_required
def add_person():
    return render_template('add_person.html')

@app.route('/person/save', methods=['POST'])
@login_required
def save_person():
    try:
        name = request.form['name']
        birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
        gender = request.form['gender']
        experiences = request.form.getlist('experiences[]')
        experience_starts = request.form.getlist('experience_start[]')
        experience_ends = request.form.getlist('experience_end[]')

        person = Person(
            name=name, 
            birth_date=birth_date, 
            gender=gender,
            user_id=session['user_id']
        )
        db.session.add(person)
        db.session.flush()

        for i in range(len(experiences)):
            if experiences[i].strip():
                start_date = datetime.strptime(experience_starts[i], '%Y-%m-%d').date()
                end_date = None
                if experience_ends[i]:
                    end_date = datetime.strptime(experience_ends[i], '%Y-%m-%d').date()
                
                experience = Experience(
                    description=experiences[i],
                    start_date=start_date,
                    end_date=end_date,
                    person_id=person.id
                )
                db.session.add(experience)

        db.session.commit()
        flash('人员信息保存成功！')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash('保存失败：' + str(e))
        return redirect(url_for('add_person'))

@app.route('/person/edit/<int:id>', methods=['GET'])
@login_required
def edit_person(id):
    person = Person.query.get_or_404(id)
    # 确保只能编辑自己创建的人员信息
    if person.user_id != session['user_id']:
        flash('您没有权限编辑此信息')
        return redirect(url_for('home'))
    return render_template('edit_person.html', person=person)

@app.route('/person/update/<int:id>', methods=['POST'])
@login_required
def update_person(id):
    try:
        person = Person.query.get_or_404(id)
        if person.user_id != session['user_id']:
            flash('您没有权限编辑此信息')
            return redirect(url_for('home'))

        person.name = request.form['name']
        person.birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
        person.gender = request.form['gender']
        
        # 删除原有的经历记录
        Experience.query.filter_by(person_id=person.id).delete()
        
        # 添加新的经历记录
        experiences = request.form.getlist('experiences[]')
        experience_starts = request.form.getlist('experience_start[]')
        experience_ends = request.form.getlist('experience_end[]')

        for i in range(len(experiences)):
            if experiences[i].strip():
                start_date = datetime.strptime(experience_starts[i], '%Y-%m-%d').date()
                end_date = None
                if experience_ends[i]:
                    end_date = datetime.strptime(experience_ends[i], '%Y-%m-%d').date()
                
                experience = Experience(
                    description=experiences[i],
                    start_date=start_date,
                    end_date=end_date,
                    person_id=person.id
                )
                db.session.add(experience)

        db.session.commit()
        flash('人员信息更新成功！')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash('更新失败：' + str(e))
        return redirect(url_for('edit_person', id=id))

if __name__ == '__main__':
    app.run(debug=True) 