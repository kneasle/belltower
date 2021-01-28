import time

from belltower import RingingRoomTower, call

tower = RingingRoomTower(389217546, "https://rr0.ringingroom.com")

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

with tower:
    tower.wait_loaded()
    while True:
        time.sleep(1000)
