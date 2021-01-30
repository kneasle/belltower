# Import the tower class, and 'time.sleep'
import time
from belltower import *

# Number of seconds between each bell stroke
BELL_GAP = 0.3
# Number of strokes that would fit into the handstroke gap
HANDSTROKE_GAP = 1

# Create a new tower, and tell it to join tower ID 765432918
tower = RingingRoomTower(765432918)

# The 'with' block makes sure that 'tower' has a chance to gracefully shut
# down the connection if the program crashes
with tower:
    # Wait until the tower is loaded
    tower.wait_loaded()

    # Set the bells at hand, call look to and wait for the sound to finish
    tower.set_at_hand()
    tower.call_look_to()
    time.sleep(3)

    # Keep count of how many rows have been rung
    row_index = 0
    while True:
        # Figure out what stroke we're on
        stroke = Stroke.from_index(row_index)

        # Implement handstroke gap
        if stroke.is_hand():
            time.sleep(BELL_GAP * HANDSTROKE_GAP)

        # Ring the row, expecting the bells to be on the right strokes
        for i in range(tower.number_of_bells):
            tower.ring_bell(Bell.from_index(i), stroke)
            time.sleep(BELL_GAP)

        # Increase the row count
        row_index += 1
