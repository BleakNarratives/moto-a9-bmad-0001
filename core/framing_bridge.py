import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'staging'))
from copywriter import generate_copy
from front_desk_lady import FrontDeskLady

class FramingBridge:
    def __init__(self):
        self.fdl = FrontDeskLady()

    def frame_market_play(self, sim_data: str) -> str:
        # Use front_desk_lady logic + copywriter
        pkg = {"name": "Market Play", "description": sim_data}
        return generate_copy(pkg, "Nostr")
