# Quickstart & Documentation

This file contains basic documentation for how to use BellTower.  If you learn best from examples,
or want code to copy/paste (we all do it :wink:), then look in the
[examples folder](https://github.com/kneasle/belltower/tree/master/examples).

## Table of Contents

- [**Some Important Things to Note**](#some-important-things-to-note)
- [**Getting Started**](#getting-started)
- [**Events**](#events)
  - [**Callbacks**](#callbacks)
  - [**Triggering Events**](#triggering-events)
  - [**Table of Events**](#table-of-events)
- [**Useful Functions**](#useful-functions)
- [**Useful Properties**](#useful-properties)

---

## Some Important Things to Note

1. The `RingingRoomTower` class only works if used inside a `with` block (see
   [examples](https://github.com/kneasle/belltower/tree/master/examples)).  If the main thread
   leaves that block, then the tower will shut its connection to Ringing Room and stop working.
2. If you perform an action in the room using this library (e.g. call a call), the callback for that
   action **will** be called.  As an example, if you ask for a bell to be rung, then you **will**
   recieve the callback for that event.
3. This library uses its own types for `Bell`s, `Stroke`s and `BellType`s (tower- or hand-bells).

## Getting Started

All the interactions with this library happen with a `RingingRoomTower` object.  This object will hold all
the state of a tower in Ringing Room, and allows you to both subscribe to and make Ringing Room
events (such as assigning users, ringing bells, making calls, etc.).

New `RingingRoomTower` objects can be created as follows:
```python
from belltower import *

tower = RingingRoomTower(765432918) # Insert your own tower ID here
```

The rest of this guide will assume that you have a `RingingRoomTower` object called `tower`.

## Events

An 'event' is any action that can happen in a Ringing Room tower (e.g. calls, bells ringing, users
being assigned are all events).

### Callbacks

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

### Triggering Events

All events (except users entering/leaving) can be triggered with the associated function.  For
example, the following code would ring the 3rd if it is at `HANDSTROKE`:
```python
tower.ring_bell(Bell.from_number(3), HANDSTROKE)
```

### Table of Events

| Event | Callback Decorator | Callback Params | Function Name & Params |
|---|---|---|---|
| Ring a bell | `@tower.on_bell_ring` | `(Bell, Stroke)` | `tower.ring_bell(Bell, Stroke)` |
| Set bells at hand | `@tower.on_set_at_hand` | None | `tower.set_at_hand()` |
| Change tower size | `@tower.on_size_change` | `new_size`: `int` | `tower.set_size(int)` |
| Change bell type | `@tower.on_bell_type_change` | `new_size`: `int` | `tower.set_bell_type(BellType)` |
| Assign a user to a bell | `@tower.on_assign` | `user_id: int, username: str, bell: Bell` | `tower.assign(user_id: int, bell: Bell)` |
| Bell is unassigned | `@tower.on_unassign` | `bell: Bell` | `tower.unassign(bell: Bell)` |
| Chat message | `@tower.on_chat` | `user: str, message: str` | `tower.chat(user: str, message: str)` |
| User enters | `@tower.on_user_enter` | `id: int, name: str` | N/A |
| User leaves | `@tower.on_user_leave` | `id: int, name: str` | N/A |
| Make a call | `@tower.on_call(str)` | None | `tower.make_call(str)` |

## Useful Functions

- `tower.wait_loaded()`: Pauses the thread until the tower's connection to Ringing Room is up and
  running.  This **must** be called before using the tower.
- `tower.user_name_from_id(user_id: int) -> (str|None)`: Gets the non-unique user name of a user,
  given their unique numerical ID.  Returns `None` if the user does not exist.
- `tower.get_stroke(bell: Bell) -> (Stroke|None)`: Gets the current stroke of a given bell,
  returning `None` if the bell is not in the tower.
- `tower.dump_debug_state()`: Dumps the entire internal state of the Tower to the console (to be
  precise, to stderr).  Useful for debugging.


## Useful Properties

Properties are read-only values attached to a given Tower

| Name | Type | Description |
|---|---|---|
| `tower.number_of_bells` | `int` | The number of bells currently in the tower. |
| `tower.bell_type` | `BellType` | The current type of the bells in the tower (`TOWER_BELLS` or `HAND_BELLS`). |
| `tower.tower_name` | `str` | The user-defined name of the tower. |
