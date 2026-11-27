#!/usr/bin/env python3
"""
[DNA_TAG]
ORIGIN: Moto4
PILLAR: dynamic_auto_tag
PATH: arena_engine_v2.py
ROLE: Auto-tagged by Code Sentinel on directory traversal.
LAST_SYNC: 2026-08-01T19:15:00
[/DNA_TAG]
"""

#!/usr/bin/env python3
"""
THOROUGHBRED ARENA ENGINE
Agent vs Monster combat, with real‑time influence and genetic inheritance.
Author: K.M. Talbert / BleakNarratives
"""

import random
import math
import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from evolution_integration import AgentDNA, ThoroughbredForge
from wavelang_mapper import HelicalState

@dataclass
class CombatStats:
    health: float = 100.0
    attack: float = 10.0
    defense: float = 5.0
    speed: float = 1.0
    special: float = 0.0

@dataclass
class Combatant:
    dna: AgentDNA
    stats: CombatStats
    team: str
    state: HelicalState
    current_health: float = 100.0
    cooldown: float = 0.0

    @property
    def is_alive(self) -> bool:
        return self.current_health > 0

    def compute_damage(self, target: 'Combatant') -> float:
        base = self.stats.attack * (1.0 + 0.2 * self.state.r)
        reduction = target.stats.defense * (1.0 + 0.2 * target.state.thread_depth)
        raw = max(1.0, base - reduction)
        theta_diff = abs(self.state.theta - target.state.theta) % (2*math.pi)
        if theta_diff < 0.5 or theta_diff > 2*math.pi - 0.5:
            raw *= 1.5
        return raw

    def take_damage(self, amount: float):
        self.current_health -= amount
        if self.current_health < 0:
            self.current_health = 0

class Arena:
    def __init__(self, forge: ThoroughbredForge):
        self.forge = forge
        self.agents: List[Combatant] = []
        self.monsters: List[Combatant] = []
        self.round = 0
        self.active = False
        self.user_intent_bonus = 0.0

    def spawn_monster(self, difficulty: float = 1.0):
        monster_dna = AgentDNA(
            agent_id=f"monster_{random.randint(1000,9999)}",
            parent_ids=[],
            birth_r=random.uniform(0.5, 1.5),
            birth_theta=random.uniform(0, 2*math.pi),
            birth_z=random.uniform(-0.5, 0.5)
        )
        stats = CombatStats(
            health=80 + 40 * difficulty,
            attack=8 + 8 * difficulty,
            defense=4 + 4 * difficulty,
            speed=0.8 + 0.4 * difficulty,
            special=0.2 * difficulty
        )
        monster_state = HelicalState(
            r=monster_dna.birth_r,
            theta=monster_dna.birth_theta,
            z=monster_dna.birth_z
        )
        monster = Combatant(
            dna=monster_dna,
            stats=stats,
            team="monster",
            state=monster_state,
            current_health=stats.health
        )
        self.monsters.append(monster)

    def add_agent_from_dna(self, dna: AgentDNA):
        fitness = dna.compute_fitness()
        stats = CombatStats(
            health=80 + 20 * fitness,
            attack=10 + 10 * fitness,
            defense=5 + 5 * fitness,
            speed=0.8 + 0.4 * fitness,
            special=0.5 * fitness
        )
        state = HelicalState(
            r=dna.birth_r,
            theta=dna.birth_theta,
            z=dna.birth_z
        )
        agent = Combatant(
            dna=dna,
            stats=stats,
            team="agent",
            state=state,
            current_health=stats.health
        )
        self.agents.append(agent)

    def step(self, dt: float = 0.1):
        if not self.active:
            return

        for c in self.agents + self.monsters:
            c.cooldown = max(0, c.cooldown - dt)

        # Agents attack monsters
        for attacker in self.agents:
            if not attacker.is_alive or attacker.cooldown > 0:
                continue
            if not self.monsters:
                break
            target = random.choice([m for m in self.monsters if m.is_alive])
            if not target:
                continue
            damage = attacker.compute_damage(target)
            if self.user_intent_bonus > 0:
                damage *= (1.0 + 0.5 * self.user_intent_bonus)
            target.take_damage(damage)
            attacker.cooldown = 1.0 / attacker.stats.speed

        # Monsters attack agents
        for attacker in self.monsters:
            if not attacker.is_alive or attacker.cooldown > 0:
                continue
            if not self.agents:
                break
            target = random.choice([a for a in self.agents if a.is_alive])
            if not target:
                continue
            damage = attacker.compute_damage(target)
            if self.user_intent_bonus < 0:
                damage *= (1.0 - 0.5 * self.user_intent_bonus)
            target.take_damage(damage)
            attacker.cooldown = 1.0 / attacker.stats.speed

        self.agents = [a for a in self.agents if a.is_alive]
        self.monsters = [m for m in self.monsters if m.is_alive]

        if not self.monsters and self.agents:
            self._handle_victory("agents")
        elif not self.agents and self.monsters:
            self._handle_victory("monsters")

    def _handle_victory(self, winner: str):
        if winner == "agents":
            survivors = [a.dna for a in self.agents]
            for _ in range(3):
                self.spawn_monster(difficulty=self.round * 0.5)
            self.round += 1
            if len(survivors) >= 2:
                parent1, parent2 = random.sample(survivors, 2)
                offspring_dna = self.forge.crossover([parent1, parent2])
                self.add_agent_from_dna(offspring_dna)
        else:
            self.active = False

    def set_user_intent(self, intent_vector: tuple):
        self.user_intent_bonus = max(-1.0, min(1.0, intent_vector[2]))

    def get_state(self) -> Dict:
        return {
            "agents": [
                {
                    "id": a.dna.agent_id[:8],
                    "health": a.current_health,
                    "max_health": a.stats.health,
                    "r": a.state.r,
                    "theta": a.state.theta,
                    "z": a.state.z,
                    "attack": a.stats.attack,
                    "defense": a.stats.defense
                } for a in self.agents
            ],
            "monsters": [
                {
                    "id": m.dna.agent_id[:8],
                    "health": m.current_health,
                    "max_health": m.stats.health,
                    "r": m.state.r,
                    "theta": m.state.theta,
                    "z": m.state.z,
                    "attack": m.stats.attack,
                    "defense": m.stats.defense
                } for m in self.monsters
            ],
            "round": self.round,
            "active": self.active,
            "intent_bonus": self.user_intent_bonus
        }
