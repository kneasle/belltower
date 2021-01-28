"""
A module to store functions related to parsing the HTML of the Ringing Room tower pages to find
things like the load-balanced URL of the socket-io server and the initial bell sounds.
"""

from typing import Tuple
import re

import urllib
import requests

from belltower import BellType


class TowerNotFoundError(ValueError):
    """ An error class created whenever the user inputs an incorrect room id. """

    def __init__(self, tower_id: int, url: str) -> None:
        super().__init__()

        self._id = tower_id
        self._url = url

    def __str__(self) -> str:
        return f"Tower {self._id} not found at '{self._url}'."

class InvalidURLError(Exception):
    """ An error class created whenever the user inputs a URL that is invalid. """

    def __init__(self, url: str) -> None:
        super().__init__()

        self._url = url

    def __str__(self) -> str:
        return f"Unable to make a connection to '{self._url}'."


def _fix_url(url: str) -> str:
    """ Add 'https://' to the start of a URL if necessary """
    corrected_url = url if url.startswith("http") else "https://" + url

    return corrected_url


def parse_page(tower_id: int, unfixed_http_server_url: str) -> Tuple[str, str, BellType]:
    """
    Parses the following things from the ringingroom.com page code:
    1. The URL of the socket server, Which (since the addition of load balancing) is not
       necessarily the same as the URL of the http server that people will put into their browser
       URL bars.
    2. The human-readable name of the tower (not to be confused with the tower ID)
    3. The initial BellType (tower or handbells).  This isn't sent as a socketio signal, and
       therefore must be parsed from the page.
    """
    http_server_url = _fix_url(unfixed_http_server_url)
    url = urllib.parse.urljoin(http_server_url, str(tower_id)) # type: ignore

    try:
        html = requests.get(url).text
    except requests.exceptions.ConnectionError as e:
        raise InvalidURLError(http_server_url) from e

    try:
        # Trying to extract the following line in the rendered html:
        # 
        # name: "{{tower_name}}",
        # ...
        # audio: "{{bell_type}}",
        # ...
        # server_ip: "{{server_ip}}",
        #
        # See https://github.com/lelandpaul/virtual-ringing-room/blob/
        #     ec00927ca57ab94fa2ff6a978ffaff707ab23a57/app/templates/ringing_room.html#L46
        load_balancing_url, = re.findall('server_ip: "(.*)"', html)
        tower_name, = re.findall(' name: "(.*)"', html)
        bell_type_str, = re.findall('audio: "(.*)"', html)
        return load_balancing_url, tower_name, BellType.from_ringingroom_name(bell_type_str)
    except ValueError as e:
        raise TowerNotFoundError(tower_id, http_server_url) from e
