from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv, os
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

base_dir = os.path.dirname(__file__)
data_dir = os.path.join(base_dir, 'data')
os.makedirs(data_dir, exist_ok=True)
WORKOUT_FILE = os.path.join(data_dir, 'workouts.csv')
FOOD_FILE = os.path.join(data_dir, 'foods.csv')
ENTRY_FILE = os.path.join(data_dir, 'entries.csv')
USERS_FILE = os.path.join(data_dir, 'users.csv')


def init_csv(path, headers, sample_rows=None):
    if not os.path.isfile(path):
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            if sample_rows:
                writer.writerows(sample_rows)

init_csv(WORKOUT_FILE, ['name','cals_per_hr','public','creator'],
         [['Running','600','True','system'],['Cycling','500','True','system'],['Yoga','200','True','system']])
init_csv(FOOD_FILE, ['name','calories','protein','carbs','fat','public','creator'],
         [['Apple','95','0.5','25','0.3','True','system'],['Chicken Breast','165','31','0','3.6','True','system'],['Rice','206','4.3','45','0.4','True','system']])
init_csv(ENTRY_FILE, ['date','user','calories','workouts','food_items','privacy'])
init_csv(USERS_FILE, ['username','password'])


def load_items(path):
    items=[]
    with open(path) as f:
        for row in csv.DictReader(f):
            if row['public']=='True' or row['creator']==session.get('user'):
                items.append(row)
    return items

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        u = request.form['username']
        p = request.form['password']
        # Prevent duplicate usernames
        with open(USERS_FILE) as f:
            for row in csv.DictReader(f):
                if row['username'] == u:
                    flash('Username already exists', 'error')
                    return render_template('signup.html')
        with open(USERS_FILE,'a',newline='') as f:
            csv.writer(f).writerow([u,p])
        flash('Registered successfully. Please log in.','success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u = request.form['username']; p = request.form['password']; valid=False
        with open(USERS_FILE) as f:
            for row in csv.DictReader(f):
                if row['username']==u and row['password']==p:
                    valid=True; break
        if valid:
            session['user']=u
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials','error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user',None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    entries = []
    with open(ENTRY_FILE) as f:
        for r in csv.DictReader(f):
            # Show public entries to all, private entries only to their creator
            if r.get('privacy', 'Private') == 'Public' or r['user'] == session['user']:
                entries.append(r)

    dates=sorted({e['date'] for e in entries},reverse=True)
    streak=0; today=date.today()
    for d in dates:
        try:
            dt=date.fromisoformat(d)
        except:
            continue
        if dt==today:
            streak+=1; today=today.fromordinal(today.toordinal()-1)
        else:
            break

    total=len(entries)
    cal_per_day = {}
    cal_list=[]
    wks=[]
    foods=[]
    for e in entries:
        val=e.get('workouts') or e.get('workout','')
        if val:
            wks.extend(val.split(';'))
        food_val=e.get('food_items','')
        if food_val:
            foods.extend(food_val.split(';'))
        c = e.get('calories','')
        if c.isdigit():
            cal_list.append(int(c))
            cal_per_day.setdefault(e['date'], 0)
            cal_per_day[e['date']] += int(c)

    avg = sum(cal_list)//len(cal_per_day) if cal_per_day else 0
    favorite = max(set(wks), key=wks.count) if wks else 'N/A'
    favorite_food = max(set(foods), key=foods.count) if foods else 'N/A'
    today_calories = cal_per_day.get(date.today().isoformat(), 0)

    return render_template('home.html',entries=entries,streak=streak,total_entries=total,
                           avg_calories=avg,favorite_workout=favorite,favorite_food=favorite_food,
                           today_calories=today_calories)

@app.route('/log', methods=['GET','POST'])
def log():
    if 'user' not in session:
        return redirect(url_for('login'))
    workouts=load_items(WORKOUT_FILE); foods=load_items(FOOD_FILE)
    if request.method=='POST':
        d=date.today().isoformat()
        wk_list=request.form.getlist('workouts')
        fd_list=request.form.getlist('foods')
        privacy=request.form.get('privacy', 'Private')

        food_dict = {f['name']: f for f in foods}
        total_cal = 0
        for food in fd_list:
            f = food_dict.get(food)
            if f and f['calories'].isdigit():
                total_cal += int(f['calories'])

        with open(ENTRY_FILE,'a',newline='') as f:
            csv.writer(f).writerow([d,session['user'],str(total_cal),';'.join(wk_list),';'.join(fd_list),privacy])
        return redirect(url_for('home'))
    return render_template('log.html',workouts=workouts,foods=foods)

@app.route('/add_workout', methods=['GET','POST'])
def add_workout():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method=='POST':
        n=request.form['name']; c=request.form['cals_per_hr']; public=request.form['privacy']=='Public'
        with open(WORKOUT_FILE,'a',newline='') as f:
            csv.writer(f).writerow([n,c,str(public),session['user']])
        return redirect(url_for('log'))
    return render_template('add_workout.html')

@app.route('/add_food', methods=['GET','POST'])
def add_food():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method=='POST':
        n=request.form['name']; cal=request.form['calories']; pr=request.form['protein']; cr=request.form['carbs']; fat=request.form['fat']; public=request.form['privacy']=='Public'
        with open(FOOD_FILE,'a',newline='') as f:
            csv.writer(f).writerow([n,cal,pr,cr,fat,str(public),session['user']])
        return redirect(url_for('log'))
    return render_template('add_food.html')

if __name__=='__main__':
    app.run(debug=True)