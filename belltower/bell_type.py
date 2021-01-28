class BellType:
    """ The appearance and sounds of the bells in Ringing Room (either HAND_BELLS or TOWER_BELLS). """

    def __init__(self, is_hand: bool):
        self._is_hand = is_hand

    def is_handbells(self) -> bool:
        return self._is_hand

    def is_towerbells(self) -> bool:
        return not self._is_hand

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
