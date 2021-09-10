from collections import defaultdict

CORRECT = 100
WRONG = -50

class Lobby:
    def __init__(self, name, maxplayers, owner, questions):
        self.name = name
        self.maxplayers = maxplayers
        self.origOwner = owner
        self.curOwner = None
        self.approvedMembers = [owner]
        self.curMembers = []
        self.questions = questions
        self.user_answers = {}
        self.score = defaultdict(int)

    def approve_user(self, userid):
        if len(self.approvedMembers) < self.maxplayers and userid not in self.approvedMembers:
            self.approvedMembers.append(userid)
            if userid == self.origOwner or len(self.approvedMembers) == 1:
                self._change_owner(userid)
            return True
        else:
            return False

    def user_join(self, userid):
        if userid in self.approvedMembers:
            self.curMembers.append(userid)
            return True
        else:
            return False

    def leave(self, userid):
        if userid in self.approvedMembers:
            self.approvedMembers.remove(userid)
            self.curMembers.remove(userid)
            if userid == self.curOwner:
                self._change_owner(self.approvedMembers[0])
            return True
        else:
            return False


    def grade_answers(self):
        result = {}
        for user in self.curMembers:
            result[user] = CORRECT if self.user_answers[user] == self.questions[0]['correct'] else WRONG
            self.score[user] += result[user]

        return result


    def next_question(self):
        self.user_answers = {}
        self.questions.pop(0)

        if self.questions:
            return self.questions[0]
        else:
            return None

    def user_answer(self, user, ans):
        print("answered: ", user)
        self.user_answers[user] = ans

    def all_answered(self):
        return len(self.user_answers) == len(self.curMembers)

    def _change_owner(self, userid):
        self.curOwner = userid

