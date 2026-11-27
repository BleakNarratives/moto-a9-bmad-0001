# knose_mvp.py
"""
KNOSE MVP - single-file prototype
- BayesianDeceptionModel : Bayesian updater for Twoie-deception probability
- Async KNOSE pipeline    : concurrent verification / debunking searches + Twoie integration (stubbed)
- SourceGraphBuilder     : builds a source co-mention graph, derives credibility scores via PageRank-like signals
- Tuner / Simulator      : simple labeled-simulation harness for tuning credibility->likelihood mappings

How to use:
    python knose_mvp.py            # runs a demo sniff on a sample claim
    import knose_mvp as km
    # use KNOSE class programmatically

Notes:
- TwoieStub simulates Twoie.execute_task. Replace TwoieStub with real Twoie client by implementing execute_task(task_name, payload).
- This file avoids heavy external libs; it uses numpy & pandas (common). If you want zero deps, remove pandas usage.
"""

from __future__ import annotations
import asyncio
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
import time
import numpy as np
import pandas as pd
import pprint

# -------------------------
# Data structures
# -------------------------
@dataclass
class EvidenceItem:
    source: str
    credibility: float  # 0..1: higher means more cred
    snippet: str
    type: str  # 'support' or 'counter'
    twoie_claimed: bool = True  # whether Twoie claims to have used/visited this item

@dataclass
class SniffReport:
    claim: str
    twoie_deception_prior: float
    twoie_deception_posterior: float
    bs_score: float
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    counter_evidence: List[Dict[str, Any]] = field(default_factory=list)
    confidence_interval: float = 0.0
    source_credibility_map: Dict[str, float] = field(default_factory=dict)
    source_graph_summary: Dict[str, Any] = field(default_factory=dict)

# -------------------------
# Bayesian deception model
# -------------------------
class BayesianDeceptionModel:
    """
    Simple Bayesian updater for P(lie). Represented in odds form for multiplicative LR updates.
    Likelihoods are heuristically derived from evidence credibility, but can be learned/tuned.
    """

    def __init__(self, prior: float = 0.55):
        self.initial_prior = float(np.clip(prior, 1e-6, 1 - 1e-6))
        self.prior = self.initial_prior

    def reset(self):
        self.prior = self.initial_prior

    def update_with_evidence(self, evidence: EvidenceItem, lie_penalty_multiplier: float = 1.5) -> float:
        """
        Update posterior probability of 'lie' after seeing evidence.
        Heuristic likelihoods:
          - support evidence:
               P(e | truthful) = credibility
               P(e | lie) = 1 - credibility
          - counter evidence: inverted
        Additional adjustments:
          - If twoie_claimed is False (evidence exists but Twoie didn't actually claim it), we treat it as suspicious
            and multiply P(e | lie) by lie_penalty_multiplier
        Returns new posterior.
        """
        prior = self.prior
        prior_odds = prior / (1 - prior)

        c = float(np.clip(evidence.credibility, 0.001, 0.999))

        if evidence.type == 'support':
            p_e_given_truth = c
            p_e_given_lie = 1 - c
        else:  # counter
            p_e_given_truth = 1 - c
            p_e_given_lie = c

        if not evidence.twoie_claimed:
            p_e_given_lie *= lie_penalty_multiplier

        # Avoid zeros
        p_e_given_truth = max(p_e_given_truth, 1e-9)
        p_e_given_lie = max(p_e_given_lie, 1e-9)

        LR = p_e_given_lie / p_e_given_truth
        posterior_odds = prior_odds * LR
        posterior = posterior_odds / (1 + posterior_odds)
        posterior = float(np.clip(posterior, 1e-9, 1 - 1e-9))

        # Update internal prior to chain updates
        self.prior = posterior
        return posterior

    def batch_update(self, evidence_list: List[EvidenceItem], shuffle: bool = True) -> float:
        if shuffle:
            random.shuffle(evidence_list)
        for ev in evidence_list:
            self.update_with_evidence(ev)
        return self.prior

# -------------------------
# Boolean query generator
# -------------------------
class BooleanSearchGenerator:
    def __init__(self):
        self.default_excludes = ['pinterest.com', 'tiktok.com']

    def generate_query(self, topic: str, focus: str = 'verification', exclude_sites: List[str] = None) -> str:
        excludes = exclude_sites if exclude_sites is not None else self.default_excludes
        exclusion = " ".join([f"-site:{s}" for s in excludes])
        topic_clean = topic.strip().lower()
        if focus == 'verification':
            q = f'"{topic_clean}" AND (proof OR "peer-reviewed" OR "study" OR "data") (site:edu OR site:gov OR site:org) {exclusion}'
        elif focus == 'debunking':
            q = f'"{topic_clean}" AND (hoax OR "fake news" OR debunked OR "not true") {exclusion}'
        elif focus == 'narrative_actors':
            q = f'"{topic_clean}" AND (narrative OR push OR trending OR "coordinated") (site:reddit.com OR site:twitter.com OR site:news)'
        else:
            q = f'"{topic_clean}" {exclusion}'
        return q

# -------------------------
# TwoieStub (replace with real twoie client)
# -------------------------
class TwoieStub:
    """
    Simulates Twoie.execute_task(task_name, payload).
    It returns structured 'resource_orchestration' results containing 'data' items that look like EvidenceItem dicts.
    Replace `execute_task` with a real asynchronous Twoie client method.
    """

    def __init__(self, rng_seed: int = None):
        self.rng = random.Random(rng_seed)

    async def execute_task(self, task_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate variable latency and produce 'data' results.
        payload could include 'query' and hints like focus.
        """
        await asyncio.sleep(self.rng.uniform(0.1, 0.45))  # simulate network latency

        query = payload.get('query', '')
        # Simulate between 2-6 hits
        n_hits = self.rng.randint(2, 6)
        results = []
        for i in range(n_hits):
            # Randomly pick domain quality
            domain_roll = self.rng.random()
            if domain_roll > 0.85:
                domain = 'random-blog.xyz'
                cred = round(self.rng.uniform(0.05, 0.25), 2)
            elif domain_roll > 0.6:
                domain = 'forum.reddit.com'
                cred = round(self.rng.uniform(0.1, 0.35), 2)
            elif domain_roll > 0.35:
                domain = 'preprint-server.org'
                cred = round(self.rng.uniform(0.4, 0.7), 2)
            else:
                domain = 'nature.com' if self.rng.random() > 0.5 else 'cdc.gov'
                cred = round(self.rng.uniform(0.8, 0.98), 2)

            # Decide whether it's support or counter depending on query type heuristics
            if 'debunk' in query or 'hoax' in query or 'fake' in query:
                typ = 'counter' if self.rng.random() > 0.4 else 'support'
            else:
                typ = 'support' if self.rng.random() > 0.45 else 'counter'

            # Simulate Twoie sometimes claiming it used a source when it didn't
            twoie_claimed = self.rng.random() > 0.08

            snippet = f"Simulated snippet {i} for `{task_name}` hitting {domain}"
            results.append({
                'source': domain,
                'credibility': cred,
                'snippet': snippet,
                'type': typ,
                'twoie_claimed': twoie_claimed
            })

        return {'resource_orchestration': {'result': {'data': results}, 'meta': {'query': query}}}

# -------------------------
# Simple Source Graph + Credibility Learner
# -------------------------
class SourceGraphBuilder:
    """
    Builds a source co-mention graph and computes a credibility score per source.
    - Co-mention edges: sources that appear in the same search results are connected.
    - Node weights initialised by simple heuristics (domain-quality guesses from evidence)
    - Runs a PageRank-like iteration to produce final credibility scores in [0,1].
    """

    def __init__(self):
        self.adj: Dict[str, Dict[str, float]] = {}  # adjacency with weights
        self.node_base: Dict[str, float] = {}  # base credibility prior per node

    def add_result_batch(self, evidence_dicts: List[Dict[str, Any]]):
        # evidence_dicts: list of evidence item dicts from same result batch/search
        sources = [d['source'] for d in evidence_dicts]
        # set base cred if missing
        for d in evidence_dicts:
            if d['source'] not in self.node_base:
                # initialize base with reported credibility if present else 0.5
                self.node_base[d['source']] = float(d.get('credibility', 0.5))

        # add edges among co-mentioned sources
        for i in range(len(sources)):
            for j in range(i + 1, len(sources)):
                a = sources[i]
                b = sources[j]
                # symmetry: increment weight
                self.adj.setdefault(a, {}).setdefault(b, 0.0)
                self.adj.setdefault(b, {}).setdefault(a, 0.0)
                self.adj[a][b] += 1.0
                self.adj[b][a] += 1.0

    def compute_pagerank_like(self, damping: float = 0.85, iters: int = 50) -> Dict[str, float]:
        # init scores from node_base normalized
        nodes = list(self.node_base.keys())
        if not nodes:
            return {}
        base_vals = np.array([self.node_base[n] for n in nodes], dtype=float)
        # normalize positive base
        if base_vals.sum() == 0:
            base_vals = np.ones_like(base_vals)
        base_vals = base_vals / base_vals.sum()
        scores = {n: float(base_vals[i]) for i, n in enumerate(nodes)}

        # build adjacency matrix-like for propagation
        for _ in range(iters):
            new_scores = {}
            for n in nodes:
                rank_sum = 0.0
                # incoming neighbors
                for m, w in self.adj.get(n, {}).items():
                    # normalize outgoing of m
                    out_sum = sum(self.adj.get(m, {}).values()) or 1.0
                    rank_sum += scores.get(m, 0.0) * (w / out_sum)
                new_scores[n] = (1 - damping) * base_vals[nodes.index(n)] + damping * rank_sum
            # normalize
            total = sum(new_scores.values()) or 1.0
            for n in nodes:
                scores[n] = new_scores[n] / total
        # scale 0..1
        min_s = min(scores.values())
        max_s = max(scores.values())
        if max_s - min_s < 1e-9:
            return {n: 0.5 for n in nodes}
        scaled = {n: (scores[n] - min_s) / (max_s - min_s) for n in nodes}
        return scaled

    def build_from_batches(self, batches: List[List[Dict[str, Any]]]):
        for batch in batches:
            self.add_result_batch(batch)
        return self.compute_pagerank_like()

# -------------------------
# KNOSE core (async sniff pipeline)
# -------------------------
class KNOSE:
    def __init__(self, twoie_agent=None, prior: float = 0.55):
        self.twoie = twoie_agent if twoie_agent is not None else TwoieStub()
        self.gen = BooleanSearchGenerator()
        self.bayes = BayesianDeceptionModel(prior=prior)
        self.source_graph = SourceGraphBuilder()

    async def _run_search_task(self, focus: str, claim: str) -> List[Dict[str, Any]]:
        query = self.gen.generate_query(claim, focus=focus)
        task_name = f"search_{focus}"
        payload = {'query': query, 'focus': focus}
        res = await self.twoie.execute_task(task_name, payload)
        data = res.get('resource_orchestration', {}).get('result', {}).get('data', [])
        # standardize shape
        std = []
        for d in data:
            std.append({
                'source': d.get('source', 'unknown'),
                'credibility': float(d.get('credibility', 0.5)),
                'snippet': d.get('snippet', ''),
                'type': d.get('type', focus),  # fallback
                'twoie_claimed': bool(d.get('twoie_claimed', True))
            })
        return std

    async def sniff_narrative(self, claim: str, run_source_graph: bool = True) -> SniffReport:
        """
        Orchestrates concurrent verification / debunking / narrative search tasks,
        runs Bayesian updates on results, computes bs_score, builds source graph, and returns SniffReport.
        """
        # Reset model
        self.bayes.reset()

        # Spawn parallel tasks
        tasks = [
            asyncio.create_task(self._run_search_task('verification', claim)),
            asyncio.create_task(self._run_search_task('debunking', claim)),
            asyncio.create_task(self._run_search_task('narrative_actors', claim))
        ]
        # Wait
        done = await asyncio.gather(*tasks)
        # done[0]=verification, done[1]=debunking, done[2]=narrative_actors
        verification_results, debunking_results, narrative_results = done

        # Convert to EvidenceItems lists
        support_items: List[EvidenceItem] = []
        counter_items: List[EvidenceItem] = []
        all_batches = []

        for d in verification_results + narrative_results + debunking_results:
            item = EvidenceItem(
                source=d['source'],
                credibility=d['credibility'],
                snippet=d['snippet'],
                type=d['type'],
                twoie_claimed=d['twoie_claimed']
            )
            if item.type == 'support':
                support_items.append(item)
            else:
                counter_items.append(item)

        # For source graph, keep batches (per search result we received earlier)
        all_batches.append(verification_results)
        all_batches.append(debunking_results)
        all_batches.append(narrative_results)

        # Build source graph credibility map
        source_cred_map = {}
        if run_source_graph:
            try:
                source_cred_map = self.source_graph.build_from_batches(all_batches)
            except Exception as e:
                print("SourceGraph build failed:", e)
                source_cred_map = {}

        # Use source_cred_map to optionally override per-item cred (blend)
        def blended_cred(item: EvidenceItem):
            base = item.credibility
            srcscore = source_cred_map.get(item.source)
            if srcscore is not None:
                # blend 70% node score + 30% original cred (example weight)
                return 0.7 * srcscore + 0.3 * base
            return base

        # Update evidence credibilities with blending
        support_items = [EvidenceItem(ev.source, blended_cred(ev), ev.snippet, ev.type, ev.twoie_claimed)
                         for ev in support_items]
        counter_items = [EvidenceItem(ev.source, blended_cred(ev), ev.snippet, ev.type, ev.twoie_claimed)
                         for ev in counter_items]

        # Run Bayesian updates: combine support+counter and update
        combined = support_items + counter_items
        # Sort combined: high-cred first to stabilize updates (optional)
        combined.sort(key=lambda x: x.credibility, reverse=True)
        posterior = self.bayes.batch_update(combined, shuffle=False)

        # Compute bs_score heuristic:
        support_weight = sum([(1 - ev.credibility) for ev in support_items])  # low-cred supports increase BS
        counter_weight = sum([(1 - ev.credibility) for ev in counter_items])
        total = support_weight + counter_weight + 1e-9
        bs_score = (support_weight / total) * 100 if total > 0 else 50.0

        confidence = max(0.0, 1.0 - posterior)

        report = SniffReport(
            claim=claim,
            twoie_deception_prior=self.bayes.initial_prior,
            twoie_deception_posterior=posterior,
            bs_score=round(bs_score, 2),
            supporting_evidence=[ev.__dict__ for ev in support_items],
            counter_evidence=[ev.__dict__ for ev in counter_items],
            confidence_interval=round(confidence, 3),
            source_credibility_map=source_cred_map,
            source_graph_summary={'nodes': len(source_cred_map)}
        )
        return report

# -------------------------
# Simple tuner / simulator
# -------------------------
def simulation_tune(num_sims: int = 100, seed: int = 1337) -> Tuple[float, float]:
    """
    Simple parameter scan to test how choices affect BS detection.
    This is intentionally low-skill: it runs random synthetic claims and measures
    correlation between true label and bs_score for different lie_penalty multipliers.
    Returns best parameters found (placeholder).
    """
    rng = random.Random(seed)
    multipliers = [1.0, 1.2, 1.5, 2.0]
    best = None
    best_score = -1.0

    for mult in multipliers:
        corr_sum = 0.0
        for s in range(num_sims):
            # make a synthetic ground-truth label (0=truthful,1=bs)
            ground_bs = rng.random() > 0.7  # 30% BS
            # craft evidence mixture
            support = []
            counter = []
            if ground_bs:
                # BS: low-cred support, high-cred counter
                support = [EvidenceItem("random-blog.xyz", rng.uniform(0.05, 0.3), "claiming", "support", True)
                           for _ in range(rng.randint(1, 3))]
                counter = [EvidenceItem("nature.com", rng.uniform(0.8, 0.98), "refuting", "counter", True)
                           for _ in range(rng.randint(1, 2))]
            else:
                # truth: high-cred support, low-cred counter
                support = [EvidenceItem("cdc.gov", rng.uniform(0.8, 0.98), "study", "support", True)
                           for _ in range(rng.randint(1, 3))]
                counter = [EvidenceItem("forum.reddit.com", rng.uniform(0.05, 0.3), "noise", "counter", True)
                           for _ in range(rng.randint(1, 2))]

            # run model
            b = BayesianDeceptionModel(prior=0.55)
            # hand-apply multiplier by toggling twoie_claimed randomly to create lie signal
            for ev in support + counter:
                if rng.random() < 0.05:
                    ev.twoie_claimed = False
            # update sequentially
            combined = support + counter
            b.batch_update(combined, shuffle=True)
            # heuristic bs_score
            support_weight = sum([(1 - ev.credibility) for ev in support])
            counter_weight = sum([(1 - ev.credibility) for ev in counter])
            total = support_weight + counter_weight + 1e-9
            bs_score = (support_weight / total) * 100

            # define detection quality: high bs_score when ground_bs True
            corr = bs_score if ground_bs else (100 - bs_score)
            corr_sum += corr
        avg = corr_sum / num_sims
        if avg > best_score:
            best_score = avg
            best = mult
    return best, best_score

# -------------------------
# Demo / CLI-style runner
# -------------------------
async def demo_run():
    print("KNOSE MVP demo booting...")
    twoie = TwoieStub(rng_seed=42)
    knose = KNOSE(twoie_agent=twoie, prior=0.55)
    claim = "Claim: X causes Y"  # sample claim
    report = await knose.sniff_narrative(claim)

    pp = pprint.PrettyPrinter(indent=2, width=120)
    print("\n=== SniffReport ===")
    print(f"Claim: {report.claim}")
    print(f"Twoie deception prior: {report.twoie_deception_prior}")
    print(f"Twoie deception posterior: {report.twoie_deception_posterior:.4f}")
    print(f"BS score (0-100, higher => more likely BS): {report.bs_score}")
    print(f"Confidence (1 - posterior): {report.confidence_interval}")
    print("\nSupporting Evidence:")
    print(pd.DataFrame(report.supporting_evidence).to_string(index=False))
    print("\nCounter Evidence:")
    print(pd.DataFrame(report.counter_evidence).to_string(index=False))
    print("\nSource credibility map (top entries):")
    s_map = report.source_credibility_map
    items = sorted(s_map.items(), key=lambda kv: kv[1], reverse=True)[:12]
    for src, sc in items:
        print(f" - {src}: {sc:.3f}")
    print("\nSource graph summary:", report.source_graph_summary)

def main():
    # 1) Dump the demo run
    asyncio.run(demo_run())

    # 2) Run a quick tuning simulation
    print("\nRunning quick simulation_tune (this is cheap)...")
    best_mult, score = simulation_tune(num_sims=200, seed=2025)
    print(f"simulation_tune suggests multiplier {best_mult} with score metric {score:.2f}")

if __name__ == "__main__":
    main()