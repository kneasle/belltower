# BellTower

A super-simple Python library for interacting with [Ringing Room](https://ringingroom.com).

This library is quite W.I.P., and its development is mostly driven by its potential use in
[Wheatley](https://github.com/kneasle/wheatley) and other (as of yet unreleased) projects of mine.
The library seems to be quite stable, but the API could change at any moment whilst I'm developing
it.

If you have any queries, then please leave [an issue](...).  Pull requests are very welcome, but if
you are making any large-scale changes then it may be worth suggesting them in an issue first.

## Why use this simple library?

- Simple libraries are just nicer to use!
- No knowledge of Ringing Room internals is needed to do cool things with Ringing Room.
- If the internals of Ringing Room change (which they have done), then fixing those breakages is as
  simple as changing to the newest version of BellTower.
- This library doesn't have to be specific to Ringing Room (though Ringing Room is far and away the
  most popular online ringing platform, so for the time being it is the only supported platform).

## How to use

All the interactions with this library happen with the `RingingRoomTower` class.  This will hold all
the state of a tower in Ringing Room, and allows you to both subscribe to and create Ringing Room
events (such as assigning users, ringing bells, making calls, etc.).  The rest of the documentation
will assume a tower created like this:
```python
from belltower import *

tower = RingingRoomTower(765432918) # Insert your own tower ID here
```

### Some important things to note

1. The `RingingRoomTower` class only works if used inside a `with` block (see examples).  If the
   main thread leaves that block, then the tower will shut its connection to Ringing Room and stop
   working.
2. If you perform an action in the room using this library (e.g. call a call), the callback for that
   action **will** be called.
3. This library uses its own types for `Bell`s, `Stroke`s and `BellType`s (tower- or hand-bells).

---

### Events

An 'event' is any action that can happen in a Ringing Room tower (e.g. calls, bells ringing, users
being assigned are all events).

#### Callbacks

All events can have callbacks attached to them, so that user-defined functions will get run when
such events occur.  Functions can be registered as callbacks in two ways:
1.  Use a decorator:
    ```python
    @tower.on_bell_ring
    def bell_ring_callback(bell, stroke):
        print(f"Bell {bell} rang at {stroke}")
    ```
2.  Assign the function manually:
    ```python
    def bell_ring_callback(bell, stroke):
        print(f"Bell {bell} rang at {stroke}")

    tower.on_bell_ring(bell_ring_callback)
    ```

#### Triggering events

All events (except users entering/leaving) can be triggered with the associated function.  For
example, the following code would ring the 3rd (expecting it to be at `HANDSTROKE`):
```python
tower.ring_bell(Bell.from_number(3), HANDSTROKE)
```

#### All events

| Event | Callback Decorator | Callback Params | Function Name & Params |
|---|---|---|---|
| Ring a bell | `@tower.on_bell_ring` | `(Bell, Stroke)` | `tower.ring_bell(Bell, Stroke)` |
| Set bells at hand | `@tower.on_set_at_hand` | None | `tower.set_at_hand()` |
| Change tower size | `@tower.on_size_change` | `new_size`: `int` | `tower.set_size(int)` |
| Change bell type | `@tower.on_bell_type_change` | `new_size`: `int` | `tower.set_bell_type(BellType)` |
| Assign a user to a bell | `@tower.on_assign` | `new_size`: `int` | `tower.assign_user(user_id: int, bell: Bell)` |
| Bell is unassigned | `@tower.on_unassign` | `bell: Bell` | `tower.assign_user(None, bell: Bell)` |
| Chat message | `@tower.on_chat` | `user: str, message: str` | `tower.chat(user: str, message: str)` |
| User enters | `@tower.on_user_enter` | `id: int, name: str` | N/A |
| User leaves | `@tower.on_user_leave` | `id: int, name: str` | N/A |
| Make a call | `@tower.on_call(str)` | None | `tower.make_call(str)` |

---

### Useful functions

- `tower.wait_loaded()`: Pauses the thread until the tower's connection to Ringing Room is up and
  running.  This **must** be called before using the tower.
- `tower.user_name_from_id(user_id: int) -> (str|None)`: Gets the non-unique user name of a user,
  given their unique numerical ID.  Returns `None` if the user does not exist.
- `tower.get_stroke(bell: Bell) -> (Stroke|None)`: Gets the current stroke of a given bell,
  returning `None` if the bell is not in the tower.
- `tower.dump_debug_state()`: Dumps the entire internal state of the Tower to stderr.  Useful for
  debugging.

### Useful properties

Properties are read-only values attached to a given Tower

| Name | Type | Description |
|---|---|---|
| `tower.number_of_bells` | `int` | The number of bells currently in the tower. |
| `tower.bell_type` | `BellType` | The current type of the bells in the tower (`TOWER_BELLS` or `HAND_BELLS`). |
| `tower.tower_name` | `str` | The user-defined name of the tower. |

## Examples

### #1: A simple chatbot

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
