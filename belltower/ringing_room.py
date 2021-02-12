import collections
import logging
import datetime
from time import sleep
from typing import Optional, Callable, Dict, List, Any

import socketio # type: ignore
import requests
import urllib
import json

from belltower import call, Bell, Stroke, HANDSTROKE, BellType, HAND_BELLS, TOWER_BELLS
from belltower.page_parsing import parse_page

# A type alias for untyped JSON
JSON = Dict[str, Any]

class RingingRoomTower:
    """ A Tower for Ringing Room. """

    logger_name = "TOWER"
    EXPECTED_RR_MAJOR = 1
    EXPECTED_RR_MINOR = 0

    def __init__(self, tower_id: int, url: str = "ringingroom.com",
                 run_version_check: bool = True) -> None:
        """ Initialise a tower with a given room id and url. """
        self.tower_id = tower_id
        self._url, self._tower_name, self._bell_type = parse_page(tower_id, url)
        self._socket_io_client: Optional[socketio.Client] = None
        # This is used by `_on_global_bell_state` to determine whether or not a `s_global_state`
        # signal is caused by us entering the tower or by a user setting the bells at handstroke
        self._waiting_for_first_global_state = True

        # Check that RR has a compatible version
        if run_version_check:
            self.check_version()

        # === CURRENT TOWER STATE ===
        self._bell_state: List[Stroke] = []
        self._assigned_users: Dict[Bell, int] = {}
        # A map from user IDs to the corresponding user name
        self._user_name_map: Dict[int, str] = {}

        # === CALLBACK LISTS ===
        # While-ringing actions
        self._invoke_on_call: Dict[str, List[Callable[[], Any]]] = collections.defaultdict(list)
        self._invoke_on_bell_ring: List[Callable[[Bell, Stroke], Any]] = []
        # Between-touch actions
        self._invoke_on_size_change: List[Callable[[int], Any]] = []
        self._invoke_on_set_at_hand: List[Callable[[], Any]] = []
        # User callbacks
        self._invoke_on_type_change: List[Callable[[], Any]] = []
        self._invoke_on_user_enter: List[Callable[[int, str], Any]] = []
        self._invoke_on_user_leave: List[Callable[[int, str], Any]] = []
        self._invoke_on_assign: List[Callable[[int, str, Bell], Any]] = []
        self._invoke_on_unassign: List[Callable[[Bell], Any]] = []
        self._invoke_on_chat: List[Callable[[str, str], Any]] = []

        # Code specific to the Wheatley/RR interface
        self._invoke_on_setting_change: List[Callable[[str, Any], Any]] = []
        self._invoke_on_row_gen_change: List[Callable[[Any], Any]] = []
        self._invoke_on_stop_touch: List[Callable[[], Any]] = []

        self.logger = logging.getLogger(self.logger_name)

    # ===== MISC =====

    def wait_loaded(self) -> None:
        """ Pause the current thread until this Tower's connection is open and stable. """
        if self._socket_io_client is None or not self._socket_io_client.connected:
            raise SocketIOClientError("Not Connected")

        iteration = 0
        # Wait up to 2 seconds
        while iteration < 20:
            if self._bell_state:
                break
            iteration += 1
            sleep(0.1)
        else:
            raise SocketIOClientError("Not received bell state from RingingRoom")

    def user_name_from_id(self, user_id: int) -> Optional[str]:
        """
        Converts a numerical user ID into the corresponding user name, returning None if user_id is
        not in the tower.
        """
        return self._user_name_map.get(user_id)

    def get_assignment(self, bell: Bell) -> Optional[int]:
        """
        Returns the user ID of the user assigned to a given Bell, or None if that bell is either
        unassigned or doesn't exist.
        """
        return self._assigned_users.get(bell)

    @property
    def all_users(self) -> Dict[int, str]:
        """ Returns a list of one user-(id, name) pair for each user in the tower. """
        return dict(self._user_name_map)

    @property
    def number_of_bells(self) -> int:
        """ Returns the number of bells currently in the tower. """
        return len(self._bell_state)

    @property
    def bell_type(self) -> BellType:
        """ Returns the current bell type (hand or tower bells). """
        return self._bell_type

    @property
    def tower_name(self) -> str:
        """ Returns the human-readable name of the current tower. """
        return self._tower_name

    def get_stroke(self, bell: Bell) -> Optional[Stroke]:
        """ Returns the stroke of a given Bell, or None if the bell is not in the tower. """
        if bell.index >= len(self._bell_state) or bell.index < 0:
            self.logger.error(f"Bell {bell} not in tower")
            return None
        return self._bell_state[bell.index]

    def dump_debug_state(self, log_level: str = logging.WARNING) -> None:
        """ Dump the entire state of this tower to the console for debugging. """
        # Create a string of the bell strokes (separated into blocks of 4)
        stroke_string = ""
        for i, stroke in enumerate(self._bell_state):
            if i % 4 == 0 and i > 0:
                stroke_string += " "
            stroke_string += "H" if stroke.is_hand() else "B"
        # Print debug messages
        self.logger.log(log_level, "===== RR TOWER DEBUG DUMP =====")
        self.logger.log(log_level, f"Joined tower #{self.tower_id}: '{self._tower_name}'")
        self.logger.log(log_level, f"SocketIO connected to {self._url}")
        self.logger.log(log_level, f"Ringing on {self.number_of_bells} {self._bell_type}")
        self.logger.log(log_level, f"Users: {self._user_name_map}")
        self.logger.log(log_level, f"Bell strokes: {stroke_string}")
        if len(self._assigned_users) == 0:
            self.logger.log(log_level, f"No bells assigned")
        else:
            for b, i in self._assigned_users.items():
                self.logger.log(log_level, f"Bell {b} assigned to #{i}/{self.user_name_from_id(i)}")

    # ===== CALLBACK DECORATORS =====

    def on_bell_ring(self, func: Callable[[Bell, Stroke], Any]) -> Callable[[Bell, Stroke], Any]:
        """
        Adds a given function as a callback for a bell being rung.  Note that the stroke refers to
        the state of the bell **before** it rang (meaning that the first blows after setting at hand
        will be considered to be a handstroke).
        """
        self._invoke_on_bell_ring.append(func)
        return func

    def on_call(self, call: str):
        """ Adds a given function as a callback for a given call. """
        def f(func: Callable[[], Any]) -> Callable[[], Any]:
            self._invoke_on_call[call].append(func)
            return func
        return f

    def on_size_change(self, func: Callable[[int], Any]) -> Callable[[int], Any]:
        """
        Adds a given function as a callback for the tower size changing. Note that this is also
        called when the tower is created.
        """
        self._invoke_on_size_change.append(func)
        return func

    def on_bell_type_change(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """ Adds a callback for a user changing the BellType (TOWER_BELLS or HAND_BELLS). """
        self._invoke_on_type_change.append(func)
        return func

    def on_set_at_hand(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """ Adds a callback for a user setting the bells at hand. """
        self._invoke_on_set_at_hand.append(func)
        return func

    def on_user_enter(self, func: Callable[[int, str], Any]) -> Callable[[int, str], Any]:
        """
        Adds a callback for a user entering the tower.  The callback passes both a unique numerical
        ID and a non-unique user name.
        """
        self._invoke_on_user_enter.append(func)
        return func

    def on_user_leave(self, func: Callable[[int, str], Any]) -> Callable[[int, str], Any]:
        """
        Adds a callback for a user leaving the tower.  The callback passes both a unique numerical
        ID and a non-unique user name.
        """
        self._invoke_on_user_leave.append(func)
        return func

    def on_assign(self, func: Callable[[int, str, Bell], Any]) -> Callable[[int, str, Bell], Any]:
        """
        Adds a callback for a user being assigned to a bell.  The callback passes both a unique numerical
        ID and a non-unique user name, as well as the Bell that was assigned to.
        """
        self._invoke_on_assign.append(func)
        return func

    def on_unassign(self, func: Callable[[Bell], Any]) -> Callable[[Bell], Any]:
        """ Adds a callback for a bell being unassigned. """
        self._invoke_on_unassign.append(func)
        return func

    def on_chat(self, func: Callable[[str, str], Any]) -> Callable[[str, str], Any]:
        """ Adds a callback for a bell being unassigned. """
        self._invoke_on_chat.append(func)
        return func

    # ===== ACTIONS =====

    def ring_bell(self, bell: Bell, expected_stroke: Optional[Stroke] = None) -> bool:
        """
        Send a request to the the server if the bell can be rung on the given stroke.  Returns
        `true` if the bell was rung successfully.
        """
        try:
            stroke = self.get_stroke(bell)
            if expected_stroke is not None and stroke != expected_stroke:
                self.logger.error(f"Bell {bell} on opposite stroke")
                return False
            bell_num: int = bell.number
            is_handstroke: bool = stroke.is_hand()
            self._emit("c_bell_rung", {"bell": bell_num, "stroke": is_handstroke, "tower_id": self.tower_id})
            return True
        except Exception as e:
            self.logger.error(e)
            return False

    def set_at_hand(self) -> None:
        """ Sets all the bells at handstroke. """
        self.logger.info("(EMIT): Setting bells at handstroke")
        self._emit("c_set_bells", {"tower_id": self.tower_id})
    
    def set_size(self, number: int) -> None:
        """ Set the number of bells in the tower. """
        self.logger.info(f"(EMIT): Setting size to {number}")
        self._emit("c_size_change", {"new_size": number, "tower_id": self.tower_id})

    def set_bell_type(self, new_type: BellType):
        """ Set the bell type (tower or hand) of the current tower. """
        self.logger.info(f"(EMIT): Setting bell type to {new_type}")
        self._emit("c_audio_change", {
            "new_audio": new_type.ringingroom_name(),
            "tower_id": self.tower_id
        })

    def assign(self, user_id: Optional[int], bell: Bell) -> None:
        """ Assign a user to a given bell. """
        if bell.number > self.number_of_bells:
            raise ValueError(f"Bell {bell.number} exceeds tower size of {self.number_of_bells}")
        if user_id is None:
            self.logger.info(f"(EMIT): Unassigning bell {bell.number}")
        else:
            user_name = self.user_name_from_id(user_id)
            if user_name is None:
                raise ValueError(f"Assigning non-existent user #{user_id} to bell {bell.number}")
            self.logger.info(f"(EMIT): Assigning user #{user_id}('{user_name}') to {bell.number}")
        self._emit("c_assign_user", {
            "bell": bell.number,
            "user": user_id or '',
            "tower_id": self.tower_id
        })

    def unassign(self, bell: Bell) -> None:
        """ Clear the assignment for a given bell. """
        self.assign(None, bell)

    def unassign_all(self) -> None:
        """ Unassign all the bells. """
        for b in range(self.number_of_bells):
            self.assign(None, Bell.from_index(b))

    def chat(self, user: str, message: str, email: str = "<belltower.py>") -> None:
        """ Sends a message on chat, using given user name (which doesn't have to valid). """
        self.logger.info(f"(EMIT): Making chat msg as '{user}'/{email}: {message}")
        self._emit("c_msg_sent", {
            "user": user,
            "msg": message,
            "email": email,
            "time": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "tower_id": self.tower_id
        })

    def check_version(self) -> bool:
        # Get version from RR's API
        url = urllib.parse.urljoin(self._url, "api/version")
        response = requests.get(url)
        versions = json.loads(response.text)
        semver = versions["socketio-version"].split(".")
        # Unpack the major/minor versions from the semver string
        rr_major = int(semver[0])
        rr_minor = int(semver[1]) if len(semver) > 1 else 0
        # Check that it's compatible with our version
        if not (rr_major == self.EXPECTED_RR_MAJOR and rr_minor >= self.EXPECTED_RR_MINOR):
            raise InvalidRRVersionError(
                f"{rr_major}.{rr_minor}",
                f"{self.EXPECTED_RR_MAJOR}.{self.EXPECTED_RR_MINOR}"
            )

    # ===== CALLS =====

    def make_call(self, call: str) -> None:
        """
        Broadcast a given call to all the users in the Tower.  This does not have to have a
        corresponding sound (like 'Bob', 'Single', 'Look To', etc.), any string can be passed and
        will appear in the centre of everyone's screens.
        """
        self.logger.info(f"(EMIT): Calling '{call}'")
        self._emit("c_call", {"call": call, "tower_id": self.tower_id})

    def call_bob(self) -> None:
        """ Calls a 'Bob' in the current tower.  Identical to `Tower.make_call(call.BOB)`. """
        self.make_call(call.BOB)

    def call_single(self) -> None:
        """ Calls a 'Single' in the current tower.  Identical to `Tower.make_call(call.SINGLE)`. """
        self.make_call(call.SINGLE)

    def call_look_to(self) -> None:
        """ Calls 'Look To' in the current tower.  Identical to `Tower.make_call(call.LOOK_TO)`. """
        self.make_call(call.LOOK_TO)

    def call_go(self) -> None:
        """ Calls 'Go' in the current tower.  Identical to `Tower.make_call(call.GO)`. """
        self.make_call(call.GO)

    def call_thats_all(self) -> None:
        """ Calls 'That's All' in the current tower.  Identical to `Tower.make_call(call.THATS_ALL)`. """
        self.make_call(call.THATS_ALL)

    def call_stand(self) -> None:
        """ Calls 'Stand' in the current tower.  Identical to `Tower.make_call(call.STAND)`. """
        self.make_call(call.STAND)

    # ===== HELPER FUNCTIONS =====

    def _emit(self, event: str, data: Any) -> None:
        """ Emit a socket-io signal. """
        if self._socket_io_client is None or not self._socket_io_client.connected:
            raise SocketIOClientError("Not Connected")
        self._socket_io_client.emit(event, data)

    @staticmethod
    def _bells_set_at_hand(number: int) -> List[Stroke]:
        """ Returns the representation of `number` bells, all set at handstroke. """
        return [HANDSTROKE for _ in range(number)]

    def _update_bell_state(self, bell_state: List[Stroke]) -> None:
        self._bell_state = bell_state
        self.logger.debug(f"RECEIVED: Bells '{''.join([s.char() for s in bell_state])}'")

    # === INTERNAL CALLBACKS ===

    def _on_bell_ring(self, data: JSON) -> None:
        """ Callback called when the client receives a signal that a bell has been rung. """
        # Unpack the data and assign it expected types
        global_bell_state: List[bool] = data['global_bell_state']
        who_rang_raw: int = data["who_rang"]
        who_rang = Bell.from_number(who_rang_raw)
        # Overwrite the bellstate with the new information
        self._update_bell_state([Stroke(b) for b in global_bell_state])
        # Only run the callbacks if the bells exist
        new_stroke = self.get_stroke(who_rang)
        if new_stroke is None:
            self.logger.warning(
                f"Bell {who_rang} rang, but the tower only has {self.number_of_bells} bells."
            )
        else:
            for bell_ring_callback in self._invoke_on_bell_ring:
                # Call the callback with the stroke of the bell **before** it rang, so that it is
                # less confusing for the consumer of the library
                bell_ring_callback(who_rang, new_stroke.opposite())

    def _on_call(self, data: Dict[str, str]) -> None:
        """ Callback called when a call is made. """
        call = data["call"]
        self.logger.info(f"RECEIVED: Call '{call}'")

        callbacks = self._invoke_on_call.get(call)
        if callbacks is None:
            self.logger.warning(f"No callback found for '{call}'")
        else:
            for c in callbacks:
                c()

    def _on_user_enter(self, data: JSON) -> None:
        """ Called when the server receives a new user. """
        # Unpack the data and assign it expected types
        user_id: int = data['user_id']
        username: str = data['username']
        # Add the new user to the user list, so we can match up their ID with their username
        self._user_name_map[user_id] = username
        # Run callbacks
        for c in self._invoke_on_user_enter:
            c(user_id, username)

    def _on_user_leave(self, data: JSON) -> None:
        """ Called when the server broadcasts that a user has left. """
        # Unpack the data and assign it the expected types
        user_id_that_left: int = data["user_id"]
        user_name_that_left: str = data["username"]

        # Remove the user ID that left from our user list
        if user_id_that_left not in self._user_name_map:
            self.logger.warning(
                f"User #{user_id_that_left}:'{user_name_that_left}' left, but wasn't in the user list."
            )
        elif self._user_name_map[user_id_that_left] != user_name_that_left:
            self.logger.warning(f"User #{user_id_that_left}:'{user_name_that_left}' left, but that ID was \
logged in as '{self._user_name_map[user_id_that_left]}'.")
            del self._user_name_map[user_id_that_left]

        bells_unassigned: List[Bell] = []

        # Unassign all instances of that user
        for bell, user in self._assigned_users.items():
            if user == user_id_that_left:
                bells_unassigned.append(bell)
        for bell in bells_unassigned:
            del self._assigned_users[bell]

        self.logger.info(
            f"RECEIVED: User #{user_id_that_left}:'{user_name_that_left}' left from bells {bells_unassigned}."
        )
        # Run callbacks
        for c in self._invoke_on_user_leave:
            c(user_id_that_left, user_name_that_left)

    def _on_user_list(self, user_list: JSON) -> None:
        """ Called when the server broadcasts a user list when Wheatley joins a tower. """
        for user in user_list['user_list']:
            self._on_user_enter(user)

    def _on_assign_user(self, data: JSON) -> None:
        """ Callback called when a bell assignment is changed. """
        raw_bell: int = data["bell"]
        bell: Bell = Bell.from_number(raw_bell)
        user: Optional[int] = data["user"] or None

        assert isinstance(user, int) or user is None, \
               f"User ID {user} is not an integer (it has type {type(user)})."

        if user is None:
            self.logger.info(f"RECEIVED: Unassigned bell '{bell}'")
            if bell in self._assigned_users:
                del self._assigned_users[bell]
            # Invoke the '**un**assign' callback if a bell is being unassigned
            for c in self._invoke_on_unassign:
                c(bell)
        else:
            self._assigned_users[bell] = user
            self.logger.info(f"RECEIVED: Assigned bell '{bell}' to '{self.user_name_from_id(user)}'")
            # Invoke the 'assign' callback if a bell is being assigned
            for c in self._invoke_on_assign:
                c(user, self.user_name_from_id(user), bell)

    def _on_global_bell_state(self, data: JSON) -> None:
        """
        Callback called when receiving an update to the global tower state.
        """
        global_bell_state: List[bool] = data["global_bell_state"]
        self._update_bell_state([Stroke(x) for x in global_bell_state])

        # These are sent for one of two reasons:
        # 1. A 's_global_state' is sent by the server to all new users so that they get a picture of
        #   what the bells are doing
        # 2. When the user sets the bells at hand, it is sent to the clients as a global state change
        # The only way to tell these two reasons apart is that the first 's_global_state' is in case
        # (1), whereas all subsequent ones can be assumed to result from bells setting at handstroke
        if not self._waiting_for_first_global_state:
            for c in self._invoke_on_set_at_hand:
                c()
        self._waiting_for_first_global_state = False

    def _on_size_change(self, data: JSON) -> None:
        """ Callback called when the number of bells in the room changes. """
        new_size: int = data["size"]
        if new_size != self.number_of_bells:
            # Remove the user who's bells have been removed (so that returning to a stage doesn't make
            # Wheatley think the bells are still assigned)
            self._assigned_users = {
                bell: user
                for (bell, user) in self._assigned_users.items()
                if bell.number <= new_size
            }
            # Set the bells at handstroke
            self._bell_state = self._bells_set_at_hand(new_size)
            # Handle all the callbacks
            self.logger.info(f"RECEIVED: New tower size '{new_size}'")
            for invoke_callback in self._invoke_on_size_change:
                invoke_callback(new_size)

    def _on_audio_change(self, data: JSON) -> None:
        """ Callback called when the bell/audio type switches between tower/hand. """
        try:
            new_bell_type = BellType.from_ringingroom_name(data["new_audio"])
        except ValueError as e:
            self.logger.warning(e)
        # It seems like Ringing Room sometimes sends the s_new_audio signal multiple times, and so
        # we only generate callbacks when the bell type is actually changed
        if new_bell_type != self._bell_type:
            self._bell_type = new_bell_type
            # Invoke the callbacks
            for c in self._invoke_on_type_change:
                c(self._bell_type)

    def _on_chat(self, data: JSON) -> None:
        """ Callback called when a chat message is received. """
        user_name = data["user"]
        message = data["msg"]
        for c in self._invoke_on_chat:
            c(user_name, message)

    # === INITIALISATION CODE ===

    def _create_client(self) -> None:
        """ Generates the socket-io client and attaches callbacks. """
        self._socket_io_client = socketio.Client()
        self._socket_io_client.connect(self._url)
        self.logger.debug(f"Connected to {self._url}")

        self._socket_io_client.on("s_call", self._on_call)
        # Bell state callbacks
        self._socket_io_client.on("s_bell_rung", self._on_bell_ring)
        self._socket_io_client.on("s_global_state", self._on_global_bell_state)
        self._socket_io_client.on("s_size_change", self._on_size_change)
        self._socket_io_client.on("s_audio_change", self._on_audio_change)
        # User change callbacks
        self._socket_io_client.on("s_user_entered", self._on_user_enter)
        self._socket_io_client.on("s_user_left", self._on_user_leave)
        self._socket_io_client.on("s_set_userlist", self._on_user_list)
        self._socket_io_client.on("s_assign_user", self._on_assign_user)
        self._socket_io_client.on("s_msg_sent", self._on_chat)
        """
        # Wheatley specific callbacks
        self._socket_io_client.on("s_wheatley_setting", self._on_setting_change)
        self._socket_io_client.on("s_wheatley_row_gen", self._on_row_gen_change)
        self._socket_io_client.on("s_wheatley_stop_touch", self._on_stop_touch)
        """

        self._join_tower()
        self._request_global_state()

    def _join_tower(self) -> None:
        """ Joins the tower as an anonymous user. """
        self.logger.info(f"(EMIT): Joining tower {self.tower_id}")
        self._emit(
            "c_join",
            {"anonymous_user": True, "tower_id": self.tower_id},
        )

    def _request_global_state(self) -> None:
        """ Send a request to the server to get the current state of the tower. """
        self.logger.debug("(EMIT): Requesting global state.")
        self._emit('c_request_global_state', {"tower_id": self.tower_id})

    # === ENTER/EXIT FOR 'WITH' BLOCKS ===

    def __enter__(self) -> Any:
        """ Called when entering a 'with' block.  Opens the socket-io connection. """
        self.logger.debug("ENTER")

        if self._socket_io_client is not None:
            raise Exception("Trying to connect twice")

        self._create_client()

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """ Called when finishing a 'with' block.  Clears up the object and disconnects the session. """
        self.logger.debug("EXIT")
        if self._socket_io_client:
            self.logger.info("Disconnect")
            self._socket_io_client.disconnect()
            self._socket_io_client = None


class SocketIOClientError(Exception):
    """Errors related to SocketIO Client"""


class InvalidRRVersionError(Exception):
    """ Error created if the RR server has an incompatible version. """

    def __init__(self, rr_ver: str, exp_ver: str):
        self.rr_ver = rr_ver
        self.exp_ver = exp_ver

    def __str__(self):
        return f"RingingRoom version {self.rr_ver} won't work with expected version {self.exp_ver}"
