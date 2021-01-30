# BellTower

A super-simple Python library for interacting with [Ringing Room](https://ringingroom.com).

This library is quite W.I.P., and its development is mostly driven by its potential use in
[Wheatley](https://github.com/kneasle/wheatley) and other (as of yet unreleased) projects of mine.
The library seems to be quite stable, but the API could change at any moment whilst I'm developing
it.

If you have any queries, then please leave 
[an issue](https://github.com/kneasle/belltower/issues/new).  Pull requests are very welcome, but if
you are making any large-scale changes then it may be worth suggesting them in an issue first.

## Why use this simple library?

- Simple libraries are just nicer to use!
- No knowledge of Ringing Room internals is needed to do cool things with Ringing Room.
- If the internals of Ringing Room change (which they have done), then fixing those breakages is as
  simple as changing to the newest version of BellTower.
- This library doesn't have to be specific to Ringing Room (though Ringing Room is far and away the
  most popular online ringing platform, so for the time being it is the only supported platform).

### Some important things to note

1. The `RingingRoomTower` class only works if used inside a `with` block (see examples).  If the
   main thread leaves that block, then the tower will shut its connection to Ringing Room and stop
   working.
2. If you perform an action in the room using this library (e.g. call a call), the callback for that
   action **will** be called.
3. This library uses its own types for `Bell`s, `Stroke`s and `BellType`s (tower- or hand-bells).

## Example: A simple chatbot

A chatbot which, whenever anyone says `Hello` in the chat, replies with `Hello, <username>`:
```python
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
```
