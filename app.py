from flask import Flask, request, render_template, redirect, url_for
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_jsonrpc import JSONRPC
from db import db
from db.models import User, Transaction
from datetime import datetime

app = Flask(__name__)

jsonrpc = JSONRPC(app, '/api', enable_web_browsable_api=True)

app.secret_key = "123"
user_db = "tsoiolga"
host_ip = "127.0.0.1"
host_port = "5432"
database_name = "rgz"
password = "123"

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_form = request.form['login']
        password_form = request.form['password']
        user = User.query.filter_by(login=username_form, password=password_form).first()
        if user:
            login_user(user)
            if user.role == 'client':
                return redirect(url_for('client'))
            else:
                return redirect(url_for('manager'))
    return render_template('login.html')


@app.route('/client')
@login_required
def client():
    user_id = current_user.id
    account_info = get_account_info(user_id)
    return render_template('client.html', account_info=account_info)


@app.route('/manager')
@login_required
def manager():
    return render_template('manager.html')


@app.route('/transactions')
@login_required
def transactions():
    user_id = current_user.id
    transactions_list = get_transactions(user_id)
    return render_template('transactions.html', transactions=transactions_list)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@jsonrpc.method('get_account_info')
def get_account_info(user_id: int) -> dict:
    user = User.query.filter_by(id=user_id, role='client').first()
    if user:
        return {'name': user.name, 'phone': user.phone, 'account': user.account, 'balance': user.balance}
    return {'error': 'Пользователь не найден!'}


@jsonrpc.method('transfer_money')
def transfer_money(sender_id: int, recipient_account: str = None, recipient_phone: str = None, amount: int = 0) -> bool:
    sender = User.query.filter_by(id=sender_id, role='client').first()
    recipient = None
    if recipient_account:
        recipient = User.query.filter_by(account=recipient_account).first()
    elif recipient_phone:
        recipient = User.query.filter_by(phone=recipient_phone).first()
    if sender and recipient and sender.balance >= amount:
        sender.balance -= amount
        recipient.balance += amount
        transaction = Transaction(sender_id=sender.id, recipient_id=recipient.id, amount=amount, timestamp=datetime.now())
        db.session.add(transaction)
        db.session.commit()
        return True
    return False


@jsonrpc.method('get_transactions')
def get_transactions(user_id: int) -> list:
    transactions_list = Transaction.query.filter((Transaction.sender_id == user_id) |
                                                 (Transaction.recipient_id == user_id)).all()
    return [{'sender': t.sender.name, 'recipient': t.recipient.name, 'amount': t.amount,
             'timestamp': t.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for t in transactions_list]


@jsonrpc.method('create_user')
def create_user(name: str, login: str, password: str, phone: str, balance: int, role: str) -> dict:
    if role == 'client':
        account = f'AC{User.query.count() + 1:06}'
        user = User(name=name, login=login, password=password, phone=phone, account=account, balance=balance, role=role)
    else:
        user = User(name=name, login=login, password=password, role=role)
    db.session.add(user)
    db.session.commit()
    return {'id': user.id, 'name': user.name, 'role': user.role}


@jsonrpc.method('update_user')
def update_user(user_id: int, name: str, login: str, password: str, phone: str, balance: int) -> bool:
    user = User.query.get(user_id)
    if user:
        user.name = name
        user.login = login
        user.password = password
        user.phone = phone
        user.balance = balance
        db.session.commit()
        return True
    return False


@jsonrpc.method('delete_user')
def delete_user(user_id: int) -> bool:
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False


@jsonrpc.method('get_users')
def get_users() -> list:
    users = User.query.all()
    return [{'id': user.id, 'name': user.name, 'login': user.login, 'phone': user.phone, 'balance': user.balance,
             'role': user.role} for user in users]


if __name__ == '__main__':
    app.run()
