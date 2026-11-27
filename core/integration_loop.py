import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'staging'))
from state_io import StateIO
from knose_mvp import KNOSE
from arena_engine_v2 import Arena
from framing_bridge import FramingBridge

class ForgeMock:
    def crossover(self, parents): return parents[0]

state = StateIO(os.path.expanduser("~/hydrogen_think_tank"))
knose = KNOSE()
arena = Arena(forge=ForgeMock())
bridge = FramingBridge()

async def run_loop():
    while True:
        try:
            report = await knose.sniff_narrative("Market Anomaly")
            if report.bs_score < 40:
                arena.spawn_monster(1.0)
                arena.step()
                sim_res = arena.get_state()
                framed = bridge.frame_market_play(str(sim_res))
                state.log_event("market_play", {"report": report.bs_score, "framed": framed})
            await asyncio.sleep(60)
        except Exception as e:
            state.log_event("error", str(e))
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_loop())
