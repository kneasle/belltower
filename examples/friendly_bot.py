"""
This example would allow someone to control Ringing Room entirely using the chat.  Every event is
reported in chat, and all actions can be invoked with chat messages.
"""

# Import the tower class, and 'time.sleep'
import time
from belltower import *

USER_NAME = "Friendly Bot"

# Create a new tower, and tell it to join tower ID 765432918
tower = RingingRoomTower(765432918)

# ===== REPORT EVENTS IN CHAT =====

# Helper function to send messages on chat with name 'Friendly Bot'
def make_chat(message):
    tower.chat(USER_NAME, message)


@tower.on_user_enter
def on_user_enter(user_id, username):
    # When a new user joins the room, welcome them graciously to the room
    make_chat(f"Welcome {username} to {tower.tower_name}!  You have ID {user_id}.")


@tower.on_user_leave
def on_user_leave(user_id, username):
    # When a new user joins the room, wish them goodbye
    make_chat(f"Goodbye {username}!")


@tower.on_bell_ring
def on_bell_ring(bell, stroke):
    # Note that 'bell' and 'stroke' are custom datatypes `Bell` and `Stroke` respectively
    make_chat(f"Bell {bell.number} rang at {stroke}")


@tower.on_set_at_hand
def on_set_at_hand():
    make_chat(f"Bells set at hand")


@tower.on_size_change
def on_size_change(new_size):
    make_chat(f"Tower now has {new_size} bells")


# This callback is called whenever the tower switches between hand- and tower-bells
@tower.on_bell_type_change
def on_bell_type_change(new_type):
    # Note that 'new_type' has type `belltower.BellType`
    make_chat(f"Now ringing {new_type}")


@tower.on_assign
def on_assign(user_id, username, bell):
    # Note that 'bell' is type 'belltower.Bell', not an integer
    make_chat(f"Bell {bell.number} now assigned to {username} (User #{user_id})")


@tower.on_unassign
def on_unassign(bell):
    # Note that 'bell' is type 'belltower.Bell', not an integer
    make_chat(f"Bell {bell.number} now unassigned")


# ===== CONVERT CHAT MESSAGES INTO ACTIONS =====


@tower.on_chat
def on_chat(user, message):
    # Early return if we sent the message
    if user == USER_NAME:
        return

    # Force the message to lower case for easier string checking
    message = message.lower()

    # We have some simple phrases that we can check
    if message == "ring tower bells":
        tower.set_bell_type(TOWER_BELLS)
    elif message == "ring hand bells":
        tower.set_bell_type(HAND_BELLS)
    elif message == "set at hand":
        tower.set_at_hand()
    elif message == "call bob":
        tower.call_bob()
    elif message == "call go":
        tower.call_go()
    elif message == "call look to":
        tower.call_look_to()
    elif message == "call single":
        tower.call_single()
    elif message == "call stand":
        tower.call_stand()
    elif message == "call that's all":
        tower.call_thats_all()
    else:
        # Split the message into words so that we can parse the meaning
        words = message.split(" ")

        if words[0] == "ring" and len(words) == 2:
            # 'ring <number>' should ring the appropriate bell
            assert tower.ring_bell(Bell.from_number(int(words[1])))
        if len(words) == 4 and words[0] == "assign" and words[2] == "to":
            # 'assign <bell> to <user id>' will assign a bell
            bell = Bell.from_number(int(words[1]))
            user_id = int(words[3])
            tower.assign(user_id, bell)
        if len(words) == 2 and words[0] == "unassign":
            # 'unassign <bell>' will clear the assignment
            bell = Bell.from_number(int(words[1]))
            tower.unassign(bell)
        if len(words) == 3 and words[0] == "set" and words[2] == "bells":
            # 'set <num> bells' will set the tower size
            tower.set_size(int(words[1]))
            

# The 'with' block makes sure that 'tower' has a chance to gracefully shut
# down the connection if the program crashes
with tower:
    # Wait until the tower is loaded
    tower.wait_loaded()
    # Report that the bot is ready
    print("Friendly bot is ready")
    # Go into an infinite loop.  It doesn't matter what the main thread does,
    # but if it leaves the `with` block then the Tower's connection will
    # close and become unusable
    while True:
        time.sleep(1000)
