import random
import string

from flask import Flask, request, jsonify, send_from_directory, session
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler
from flask_cors import CORS, cross_origin
from flask_bcrypt import Bcrypt
import socketio

import database.main as database

app = Flask(__name__)

app.config['CORS_HEADERS'] = ['Content-Type']
app.config['CORS_SUPPORTS_CREDENTIALS'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PYBRAKE'] = dict(
    project_id=334820,
    project_key='4db666d0323aab24d367b3ff75c67bab',
)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

cors = CORS(app)

sio = socketio.Client()
bcrypt = Bcrypt(app)

database.db.app = app
database.db.init_app(app)
database.init_db()
database.Prizes.add_prize("Beer", 75, "Just beer")
database.Prizes.add_prize("Apple Beer 12", 150, "Double the price, half the reasons")
database.Questions.add_question("The first question", "first_answer", 1, "basic")
database.Questions.add_question("The second question", "second_answer", 1, "basic")
database.Questions.add_question("The third question", "third_answer", 1, "basic")
database.WrongAnswers.add_wrong_answers("not_first_answer1", 1)
database.WrongAnswers.add_wrong_answers("not_first_answer2", 1)
database.WrongAnswers.add_wrong_answers("not_first_answer3", 1)
database.WrongAnswers.add_wrong_answers("not_second_answer1", 2)
database.WrongAnswers.add_wrong_answers("not_second_answer2", 2)
database.WrongAnswers.add_wrong_answers("not_second_answer3", 2)
database.WrongAnswers.add_wrong_answers("not_third_answer1", 3)
database.WrongAnswers.add_wrong_answers("not_third_answer2", 3)
database.WrongAnswers.add_wrong_answers("not_third_answer3", 3)

@sio.on('connect')
def sock_connect():
    print("I'm connected!")
    sio.emit('add server')


@sio.on('connection_error')
def sock_connect_error(data):
    print("The connection failed!")


@sio.on('disconnect')
def sock_disconnect():
    print("I'm disconnected!")


@sio.on('update score')
def sock_update_score(data):
    print("updating scores", data)
    point_update(data)


while True:
    try:
        sio.connect('http://localhost:5001')
        break
    except socketio.exceptions.ConnectionError as e:
        continue


"""
If not otherwise specified, the exposed methods responds to GET requests with JSOn-encoded parameters.
Please ensure proper parameter names when sending your requests.

All responses are combination of HTTP response codes (see method description) and JSON-encoded result.

Most methods require providing user login token. this token is gained by either calling login or register methods.
This token should not be shared with third parties.
"""

db = {}


@app.route('/register', methods=['POST'])
def api_register():
    """
    Registers new user in the database.

    :param name: username string
    :param password: password string

    :return: code 200 if successful, 400 if the parameters sent are invalid, 409 if user already exists.
        If the request was successful, the response message will contain user token needed for further requests.
        This means that successful registration also works as a login, and calling login method immediately afterwards
        is therefore unnecessary.
    """

    json = request.get_json()
    if 'name' in json and 'password' in json:
        if register(json['name'], json['password']):
            session['username'] = json['name']
            return "", 200
        else:
            return "", 409
    else:
        return "", 400


@app.route('/login', methods=['POST'])
def api_login():
    """
    Logins existing user to the system.

    :param name: username string
    :param password: password string

    :return: code 200 if successful, 400 if fields are missing, 401 if credentials are incorrect.
        If the request was successful, the response message will contain user token.
    """
    json = request.get_json()
    if 'name' in json and 'password' in json:
        if login(json['name'], json['password']):
            session['username'] = json['name']
            return "", 200
        else:
            return "", 401
    else:
        return "", 400


@app.route('/logout', methods=['POST'])
def api_logout():
    """
    Logs out the user (invalidates the token)

    :param token: user token

    :return: code 200 if successful, 400 if the token is not valid.
    """
    if logout():
        return "", 200
    else:
        return "", 400

@app.route('/purchase', methods=['POST'])
def api_purchase():
    """
    purchase the item based on the itemnumber

    :param token: usertoken string
    :param itemnr : item number(unique)

    :return:
        200: success, item was added to user account
        400: invalid itemnumber
        402: insufficient coins
    """
    json = request.get_json()
    if 'itemnr' in json and json['itemnr']:
        if purchase(json['itemnr']):
            return "", 200
        else:
            return "", 402
    else:
        return "", 400



@app.route('/purchasecoin', methods=['POST'])
def api_purchase_coin():
    """
    purchase coin according to the amount

    :param token: usertoken string
    :param prize_id: id of item

    :return:
        200: successful
        400: invalid amount
    """
    json = request.get_json()
    if purchase_coin(json['prize_id']):
        return "", 200
    else:
        return "", 400

@app.route('/listitems', methods=['GET'])
def api_listitems():
    """
    list all items in the shop that can be bought

    :param token: usertoken string

    :return:
        200: [{ID, title, desc, price}, ...]
    """
    print("list session", session)
    result = []
    for prize in listitems():
        result.append({'title': prize.name, 'price': prize.cost,
                       'desc': prize.description,
                       'id': prize.id})

    print(result)
    return jsonify(result), 200


@app.route('/userinfo/userid', methods=['GET'])
def api_userinfo():
    """
    User info

    :param userid: usertoken string

    :return:
        200: {name, coins, items}
        404: user doesn't exist
    """
    result = {'name': userinfo().username, 'money': userinfo().points,
                     'items': "to be implemented"}
    print(result)
    if userinfo():
        return jsonify(result), 200
    else:
        return "", 404



@app.route('/createroom', methods=['POST'])
def api_create_room():
    """
    Creates a new room and assigns the current user (according to the token) as the owner.
    :param roomname: name of the room that will be listed in browse tab.
        Must be string between 2 and 64 characters long
    :param maxplayers: Maximum number of players allowed into the room.
        Must be integer between 2 and 10
    :return:
        200: {socketIp, socketPort, roomid} returns information how to connect to the assigned game server
        400: invalid roomname or maxplayers - see parameter specification above
        409: the roomanme is already taken
    """
    json = request.get_json()
    # todo verification
    if False:
        return "", 400

    q = load_question()
    print(q)
    if sio.call('create lobby',
                {'roomname': json['roomname'],
                 'maxplayers': json['maxplayers'],
                 'owner': session['username'],
                 'questions': q},
                ):
        return {**get_socket_address(), 'roomid': json['roomname']}, 200
    else:
        return "", 409


@app.route('/joinroom/<roomid>')
def api_join_room(roomid):
    """
    Adds the current user to selected room (if there is still space)
    :param roomid: id of the room
    :return:
        200: {socketIp, socketPort} returns information how to connect to the assigned game server
        404: room does not exist
        409: the room is already full
    """
    resp = sio.call('server join room', {
        'roomid': roomid,
        'userid': session['username']
    })
    if resp == 200:
        return {**get_socket_address(), 'roomid': roomid}, 200
    elif resp == 409:
        return "", 409
    else:
        return "", 404


@app.route('/listrooms')
def api_list_rooms():
    """
    Gives information about all the rooms currently open
    :return:
        200: [{roomid, nplayers, maxplayers, hostName, lobbyName}, ...]
    """
    resp = sio.call('server get info')

    return jsonify(resp), 200


def load_question():
    """
    List out a question and the corresponding set of answers and last returns the id of the correct answer.
    :return:
        200:[{question,answers[],correct}, ...]
    """

    #you need to add wrong answers before actually calling the load questions.
    result = []

    for question in database.Questions.get_all_questions():
        anslist = []
        for wrongans in question.wrong_ans:
            anslist.append(wrongans.answer_text)
        anslist.append(question.correct_ans)
        random.shuffle(anslist)
        result.append({'question': question.question, 'answers': anslist ,
                       'correct': anslist.index(question.correct_ans)})

    print(result)
    return result

def point_update(dict):
    """
    updates the points of the users accordingly
    :param {[username:points],[user2:points2], ...}
    :return: update to database,200
    """
    for data in dict:
        user = database.User.get_user_info(data)
        user.update_points(dict[data])
    return True


def register(name, password):
    return database.User.add_user(name, str(bcrypt.generate_password_hash(password), "UTF-8"))


def login(name, password):
    user = database.User.get_user_info(name)
    if user and bcrypt.check_password_hash(user.password, password):
        return True
    else:
        return False


def logout():
    if 'username' in session:
        session.pop('username')
        return True
    else:
        return False

def userid(token):
    return 1

def purchase(itemnr):
    if 'username' in session and itemnr:
        database.User.get_user_info(session['username']).purchase_prize(itemnr)
        return True
    else:
        return False

def purchase_coin(prize_id):
    if 'username' in session and prize_id:
        user = database.User.get_user_info(session['username'])
        try:
            user.purchase_prize(prize_id)
            return True
        except AttributeError:
            return True
    else:
        return False

def listitems():
    if 'username' in session:
        return database.Prizes.get_all_prizes()


def userinfo():
    if 'username' in session:
        return database.User.get_user_info(session['username'])

def get_socket_address():
    return {"socketIp": "localhost", "socketPort": 5001}


if __name__ == '__main__':
    app.debug = True
    http_server = WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

