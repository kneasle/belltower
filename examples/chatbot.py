# Import the tower class
from time import sleep
from belltower import RingingRoomTower

# Create a new tower, and tell it to join tower ID 765432918
tower = RingingRoomTower(765432918)

# Register a function to be called when a chat message is posted
@tower.on_chat
def on_chat(user, message):
    print(f"{user} says '{message}'")
    # If the message is 'hello' in any capitalisation, send 'Hello <user>'.
    # The first argument is the name to put next to the chat message
    if message.lower() == "hello":
        tower.chat("RR ChatBot", f"Hello, {user}!")

# The 'with' block makes sure that 'tower' has a chance to gracefully shut
# down the connection if the program crashes
with tower:
    # Wait until the tower is loaded
    tower.wait_loaded()
    # Go into an infinite loop.  It doesn't matter what the main thread does,
    # but if it leaves the `with` block then the Tower's connection will
    # close and become unusable
    while True:
        sleep(1000)
