import time
from belltower import *
from belltower import call

tower = RingingRoomTower(389217546)

@tower.on_user_enter
def on_enter(_id, name):
    print(f"User #{_id}:'{name}' entered.")

@tower.on_user_leave
def on_leave(_id, name):
    print(f"User #{_id}:'{name}' left.")
        
@tower.on_unassign
def on_unassign(bell):
    print(f"{bell.number} unassigned.")

@tower.on_assign
def on_assign(_id, name, bell):
    print(f"User #{_id}:'{name}' assigned to {bell.number}.")

@tower.on_call(call.BOB)
def on_bob():
    print("BOB!")

@tower.on_call(call.SINGLE)
def on_single():
    print("SINGLE!")
    tower.dump_debug_state()

@tower.on_call(call.LOOK_TO)
def on_look_to():
    print("LOOK TO!")
    tower.set_bell_type(HAND_BELLS)

@tower.on_bell_ring
def on_bell(bell, stroke):
    print(bell, stroke)

@tower.on_size_change
def on_size_change(new_size):
    print(f"Changing tower size to {new_size}!")
    tower.call_bob()

@tower.on_bell_type_change
def on_bell_type_change(new_type):
    print(f"Changing bell type to {new_type}!")

@tower.on_set_at_hand
def on_set_at_hand():
    print("Setting bells at hand")

@tower.on_chat
def on_chat(user, message):
    print(f"{user} says '{message}'")
    if message.lower() == "hello":
        tower.chat("RR ChatBot", f"Hello, {user}!")

with tower:
    tower.wait_loaded()
    while True:
        time.sleep(1000)
