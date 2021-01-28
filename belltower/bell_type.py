class BellType:
    """ The appearance and sounds of the bells in Ringing Room (either HAND_BELLS or TOWER_BELLS). """

    def __init__(self, is_hand: bool):
        self._is_hand = is_hand

    def is_handbells(self) -> bool:
        """ Returns True if the tower is using hand bells. """
        return self._is_hand

    def is_towerbells(self) -> bool:
        """ Returns True if the tower is using tower bells. """
        return not self._is_hand

    def ringingroom_name(self) -> str:
        """
        Returns the name of this BellType expected by the Ringing Room server (i.e. "Tower" or
        "Hand").
        """
        return "Hand" if self._is_hand else "Tower"

    @classmethod
    def from_ringingroom_name(cls, name: str) -> "BellType":
        if name == "Tower":
            return TOWER_BELLS
        elif name == "Hand":
            return HAND_BELLS
        else:
            raise ValueError(f"Unknown tower type '{name}'")

    def __str__(self) -> str:
        return "handbells" if self._is_hand else "tower bells"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other) -> bool:
        return isinstance(other, BellType) and other._is_hand == self._is_hand

    def __hash__(self) -> int:
        """ Generates a has of a Bell. """
        return hash(self._is_hand)

HAND_BELLS = BellType(True)
TOWER_BELLS = BellType(False)
