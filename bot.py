from slackclient import SlackClient
import requests
import time
import messages
import puzzles
import random
import config

# TODO: Make hints post to another channel of just admin, where admin can then respond to hints and bot auto DMs back the requester of the hint
# TODO: Show scoreboard that updates every so often in another channel maybe
# TODO: Show analytics on how many teams have solved each puzzle that updates every so often in another channel maybe?
# TODO: Verify that team creation/team joining works well
# TODO: Store and use timestamp of last solve to break ties
# TODO: Order scoreboard by decreasing score
# TODO: Make scoreboard output look pretty
# TODO: Make puzzled solved status output look pretty

BOT_ACCESS_TOKEN = config.BOT_ACCESS_TOKEN

slack_token = BOT_ACCESS_TOKEN
sc = SlackClient(slack_token)
team_code_to_team = {}
user_to_team_code = {}
team_code_to_score = {}
team_code_to_puzzles_solved = {}

def generate_team_code():
    team_code = str(random.randint(10000, 99999))
    while (team_code in team_code_to_team):
        team_code = str(random.randint(10000, 99999))
    return team_code

def update_score(user, puzzle_code):
    team_code = user_to_team_code[user]
    team_code_to_score[team_code] += puzzles.POINTS[puzzle_code]
    team_code_to_puzzles_solved[team_code][puzzle_code] = "Solved!"

def clean_guess(guess):
    guess = guess.replace(" ", "")
    guess = guess.upper()
    return guess

def scoreboard(user):
    resp = ""
    for team_code in team_code_to_score:
        team_name = team_code_to_team[team_code]
        team_score = team_code_to_score[team_code]
        resp +=  "`" + team_name + " "*(30 - len(team_name)) + str(team_score) + '

def puzzle_statuses(user):
    if user not in user_to_team_code:
        return messages.INVALID_USER
    team_code = user_to_team_code[user]

    resp = "Your Puzzles\n"
    puzzle_states = team_code_to_puzzles_solved[team_code]
    for puzzle_code in puzzle_states:
        puzzle_name = puzzles.PUZZLES[puzzle_code]
        resp += "`" + puzzle_name + " "*(20 - len(puzzle_name)) + puzzle_states[puzzle_code] + "`\n"
    return resp


def check_solution(puzzle_code, guess, user):
    if puzzle_code not in puzzles.ANSWERS:
        return messages.INVALID_CODE
    elif user not in user_to_team_code:
        return messages.INVALID_USER
    else:
        answer = puzzles.ANSWERS[puzzle_code]
        if (clean_guess(guess) != answer):
            return messages.WRONG_ANSWER
        else:
            update_score(user, puzzle_code)
            return messages.CORRECT_ANSWER

def create_team(team_name, user):
    # Verify this user is not already on a team
    if user in user_to_team_code:
        return messages.ALREADY_ON_TEAM
    team_code = generate_team_code()
    team_code_to_team[team_code] = team_name
    user_to_team_code[user] = team_code
    team_code_to_score[team_code] = 0
    team_code_to_puzzles_solved[team_code] = {}
    for puzzle in puzzles.PUZZLES:
        team_code_to_puzzles_solved[team_code][puzzle] = "Not solved"
    print messages.TEAM_CREATED + team_code + "`"
    return messages.TEAM_CREATED + team_code + "`"

def join_team(team_code, user):
    if user in user_to_team_code:
        return messages.ALREADY_ON_TEAM
    elif team_code not in team_code_to_team:
        return messages.TEAM_DOES_NOT_EXIST
    elif user_to_team_code.values().count(team_code) == 4:
        return messages.TEAM_FULL
    user_to_team_code[user] = team_code

def submit_hint(puzzle_code, hint_prompt, user):
    pass

def process_message(message, user):
    if message == "help":
        return messages.HELP
    elif "create team" in message:
        try:
            _1, _2, team_name = message.split(" ", 2)
            resp = create_team(team_name, user)
            return resp
        except:
            return messages.TEAM_PARSING_ERROR
    elif "join team" in message:
        try:
            _1, _2, team_code = messagesplit(" ", 2)
            resp = join_team(team_code, user)
            return resp
        except:
            return messages.TEAM_CODE_PARSING_ERROR
    elif message == "scoreboard":
        pass
    elif message == "solved":
        return puzzle_statuses(user)
    elif "hint" in message:
        try:
            _1, puzzle_code, hint_prompt = message.split(" ", 2)
            res = submit_hint(puzzle_code, hint_prompt, user)
            return res
        except:
            return messages.HINT_PARSING_ERROR
    else:
        try:
            puzzle_code, guess = message.split(" ", 1)
            res = check_solution(puzzle_code, guess, user)
            return res
        except:
            return messages.GUESS_PARSING_ERROR


def process_event(rtm_event):
    if (len(rtm_event) == 0):
        return
    event = rtm_event[0]
    if "type" in event and event["type"] == "message":
        if "username" in event and event["username"] == "Puzzle Bot":
            return
        DM_channel = event["channel"]
        DM_user = event["user"]
        DM_message = event["text"]
        resp = process_message(DM_message, DM_user)
        send_message(resp, DM_channel)

def send_message(message, channel):
    res = sc.api_call('chat.postMessage', channel=channel, text=message)

if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1
    if sc.rtm_connect():
        print "Puzzle Bot connected and running!"
        while True:
            process_event(sc.rtm_read())
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
