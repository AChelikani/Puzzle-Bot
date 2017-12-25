from slackclient import SlackClient
import requests
import time
import messages
import puzzles
import random
import config

# TODO: Make it so hint_code is not required when responding to hint
# TODO: Add rate limits to teams asking for hints maybe?
# TODO: Add rate limits to teams guessing many times?
# TODO: Show scoreboard that updates every so often in another channel maybe
# TODO: Show analytics on how many teams have solved each puzzle that updates every so often in another channel maybe?
# TODO: Verify that team creation/team joining works well
# TODO: Make the message strings templates, so that we can insert variable values into them to make more meaningful messages


BOT_ACCESS_TOKEN = config.BOT_ACCESS_TOKEN
BOT_USERNAME = "Puzzle Bot"

slack_token = BOT_ACCESS_TOKEN
sc = SlackClient(slack_token)
team_code_to_team_name = {}
user_to_team_code = {}
team_code_to_score = {} # code -> (score, timestamp of latest solve)
team_code_to_puzzles_solved = {}
hint_code_to_hint = {} # code -> (puzzle_code, description, user, channel_id)

hint_channel_id = ""
groups = sc.api_call("groups.list")
for group in groups["groups"]:
    if group["name"] == "hints":
        hint_channel_id = group["id"]

def team_info(user):
    if user not in user_to_team_code:
        return messages.INVALID_USER
    resp = ""
    team_code = user_to_team_code[user]
    team_members = [member for member in user_to_team_code if user_to_team_code[member] == team_code]
    for x in range(len(team_members)):
        team_members[x] = get_user_name(team_members[x])
    print team_members
    team_name = team_code_to_team_name[team_code]
    resp += "Team Name: `" + team_name + "`\n"
    resp += "Team Members: "
    for member in team_members:
        resp += "`" + member + "` "
    return resp

def get_user_name(user):
    try:
        res = sc.api_call('users.info', user=user)
        return res["user"]["real_name"]
    except:
        return "Name not found!"

def generate_team_code():
    team_code = str(random.randint(10000, 99999))
    while (team_code in team_code_to_team_name):
        team_code = str(random.randint(10000, 99999))
    return team_code

def generate_hint_code():
    hint_code = str(random.randint(10000, 99999))
    while (hint_code in hint_code_to_hint):
        hint_code = str(random.randint(10000, 99999))
    return hint_code

def update_score(user, puzzle_code):
    team_code = user_to_team_code[user]
    score, _1 = team_code_to_score[team_code]
    team_code_to_score[team_code] = (score + puzzles.POINTS[puzzle_code], time.time())
    team_code_to_puzzles_solved[team_code][puzzle_code] = "Solved!"

def clean_guess(guess):
    guess = guess.replace(" ", "")
    guess = guess.upper()
    return guess

def scoreboard():
    resp = "Scoreboard\n"
    scores = zip(team_code_to_score.keys(), team_code_to_score.values())
    scores = sorted(scores, key=lambda x: (-x[1][0], x[1][1]))
    rank = 1
    for team in scores:
        team_code, team_score_and_timestamp = team
        team_score = team_score_and_timestamp[0]
        team_name = team_code_to_team_name[team_code]
        resp +=  "`" + str(rank) + "`. `" + team_name + " "*(30 - len(team_name)) + str(team_score) + "`"
        rank += 1
    return resp

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
    team_code_to_team_name[team_code] = team_name
    user_to_team_code[user] = team_code
    team_code_to_score[team_code] = (0, time.time())
    team_code_to_puzzles_solved[team_code] = {}
    for puzzle in puzzles.PUZZLES:
        team_code_to_puzzles_solved[team_code][puzzle] = "Not solved"
    print messages.TEAM_CREATED + team_code + "`"
    return messages.TEAM_CREATED + team_code + "`"

def join_team(team_code, user):
    if user in user_to_team_code:
        return messages.ALREADY_ON_TEAM
    elif team_code not in team_code_to_team_name:
        return messages.TEAM_DOES_NOT_EXIST
    elif user_to_team_code.values().count(team_code) == 4:
        return messages.TEAM_FULL
    user_to_team_code[user] = team_code

def submit_hint(puzzle_code, hint_request, user, response_channel):
    if user not in user_to_team_code:
        return messages.INVALID_USER
    elif puzzle_code not in puzzles.PUZZLES:
        return messages.INVALID_CODE
    hint_code = generate_team_code()
    hint_code_to_hint[hint_code] = (puzzle_code, hint_request, user, response_channel)
    puzzle_name = puzzles.PUZZLES[puzzle_code]
    send_message("`" + hint_code + "`\n For puzzle: `" + puzzle_name + "`.\n *Hint request was:* " + hint_request, hint_channel_id)
    return messages.HINT_REQUESTED

def process_message(message, user, channel):
    if message == "help":
        return messages.HELP
    elif "create team" in message:
        try:
            _1, _2, team_name = message.split(" ", 2)
            if (len(team_name) > 30):
                return messages.TEAM_NAME_TOO_LONG
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
        return scoreboard()
    elif message == "solved":
        return puzzle_statuses(user)
    elif message == "team info":
        return team_info(user)
    elif "hint" in message:
        try:
            _1, puzzle_code, hint_prompt = message.split(" ", 2)
            resp = submit_hint(puzzle_code, hint_prompt, user, channel)
            return resp
        except:
            return messages.HINT_PARSING_ERROR
    else:
        try:
            puzzle_code, guess = message.split(" ", 1)
            res = check_solution(puzzle_code, guess, user)
            return res
        except:
            return messages.GUESS_PARSING_ERROR


def process_hint_response(message):
    try:
        hint_code, hint_response = message.split(" ", 1)
        if hint_code not in hint_code_to_hint:
            return messages.INVALID_HINT_CODE
        puzzle_code, hint_request, _1, response_channel = hint_code_to_hint[hint_code]
        puzzle_name = puzzles.PUZZLES[puzzle_code]
        msg_text = "Your hint for `" + puzzle_name + "` has been answered.\n *Request:* " + hint_request + "\n *Response:* " + message[6:] # Ignore hint code and space after hint code
        send_message(msg_text, response_channel)
        return messages.HINT_SENT
    except:
        return messages.INVALID_HINT_RESPONSE

def process_event(rtm_event):
    if (len(rtm_event) == 0):
        return
    event = rtm_event[0]
    if "type" in event and event["type"] == "message":
        if "username" in event and event["username"] == BOT_USERNAME:
            return
        DM_channel = event["channel"]
        DM_user = event["user"]
        DM_message = event["text"]
        if (DM_channel == hint_channel_id):
            if "thread_ts" not in event:
                return
            thread_ts = event["thread_ts"]
            resp = process_hint_response(DM_message)
            send_message_in_thread(resp, DM_channel, thread_ts)
        else:
            resp = process_message(DM_message, DM_user, DM_channel)
            send_message(resp, DM_channel)

def send_message(message, channel):
    res = sc.api_call('chat.postMessage', channel=channel, text=message)
    return res

def send_message_in_thread(message, channel, thread_ts):
    res = sc.api_call('chat.postMessage', channel=channel, text=message, thread_ts=thread_ts)
    return res


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1
    if sc.rtm_connect():
        print "Puzzle Bot connected and running!"
        while True:
            try:
                process_event(sc.rtm_read())
            except:
                continue
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
