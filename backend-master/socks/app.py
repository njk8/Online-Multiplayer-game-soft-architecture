from flask import Flask, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
from lobby import Lobby
from flask_cors import CORS

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
CORS(app)

lobbies = {}

@socketio.on('add server')
def on_server_added():
    print('adding server')
    join_room("servers")


@socketio.on('connect')
def test_connect():
    print("connected")


@socketio.on('start')
def start_game():
    # todo check if user is owner
    q = lobbies[session['roomname']].questions[0]
    print("question", q)
    emit("start", q, to=session['roomname'])


@socketio.on('message')
def handle_message(message):
    print('message', message)


@socketio.on('answer')
def player_answer(data):
    answer = data['answer']
    lobby = lobbies[session['roomname']]
    lobby.user_answer(session['username'], answer)
    print("user ansered")
    print("all answered:", lobby.all_answered())

    if lobby.all_answered():
        answer = lobby.questions[0]['correct']
        points = lobby.grade_answers()
        socketio.emit('update score', points, to='servers')
        q = lobby.next_question()

        if q:
            emit("next question", {'answer': answer, 'question': q}, to=session['roomname'], include_self=True)
        else:
            print("game ended. Score:", dict(lobby.score))
            lobbies.pop(session['roomname'])
            emit('game ended', dict(lobby.score), to=session['roomname'], include_self=True)

    # TODO Check if correct, give points etc

    # TODO send list of players and points?
    # TODO send answer and question separately? (So that fronend can display the correct answer without knowing the next question)


@socketio.on('create lobby')
def server_create_lobby(data):
    print("making lobby", data)
    # join_room(data['roomname'])
    print(request)
    # assert all(map(lambda key : key in data, ['roomname', 'maxPlayers', 'hostName', 'lobbyDesc']))

    if data['roomname'] not in lobbies:
        lobbies[data['roomname']] = Lobby(data['roomname'], data['maxplayers'], data['owner'], data['questions'])
        emit("created lobby")
        return True
    else:
        return False


@socketio.on('server join room')
def server_join_room(data):
    if data['roomid'] not in lobbies:
        return 404
    lobbies[data['roomid']].approve_user(data['userid'])
    return 200


@socketio.on('server get info')
def server_get_info():
    return [{
        'roomid': roomid,
        'nplayers': len(room.approvedMembers),
        'maxplayers': room.maxplayers,
        'hostName': room.origOwner,
        'lobbyName': room.name
    } for roomid, room in lobbies.items()]


@socketio.on('join room')
def user_join_lobby(data):  # TODO send list of players connected to room?
    print("join room session", session)
    if data['roomname'] in lobbies:
        if lobbies[data['roomname']].user_join(session['username']):
            join_room(data['roomname'])
            session['roomname'] = data['roomname']
            emit('player joined', to=session['roomname'])
        else:
            return "lobby is full"
    else:
        return "lobby doesnt exist"


@socketio.on('leave room')
def user_leave_room(data):
    """
    Removes current user (according to the token) from the room he is in.
    :return:
        True: user successfully removed
        False: user was not found in any room
    """
    for roomid, room in lobbies.items():
        if session['usernmae'] in room.approvedMembers:
            room.leave(session['username'])
            session.pop('roomname')
            leave_room(roomid)
            return True
    return False


if __name__ == '__main__':
    app.debug = True
    socketio.run(app, port=5001)
