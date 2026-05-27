from granum.center.mutation_strategies import propose_mutations
from granum.center.mutation import Mutation


def test_propose_mutations_returns_n_proposals():
    parent = "Per Aetna CPB 0119 we appeal. ACC/AHA 2021 Chronic Coronary Disease supports."
    mutations = propose_mutations(parent=parent, n=3, seed=0)
    assert len(mutations) == 3
    for m in mutations:
        assert isinstance(m, Mutation)


def test_propose_mutations_deterministic_with_seed():
    parent = "Per Aetna CPB 0119 we appeal. The procedure is medically necessary."
    a = propose_mutations(parent=parent, n=3, seed=42)
    b = propose_mutations(parent=parent, n=3, seed=42)
    assert a == b


def test_propose_mutations_varies_with_different_seeds():
    parent = "Per Aetna CPB 0119 we appeal. Per Aetna CPB 0286 we also cite. The procedure is medically necessary."
    seen_first = {propose_mutations(parent=parent, n=1, seed=s)[0] for s in range(20)}
    # At least 2 distinct mutations across 20 seeds
    assert len(seen_first) >= 2


def test_propose_mutations_targets_exist_in_parent():
    parent = "Per Aetna CPB 0119 we appeal. ACC/AHA 2021 Chronic Coronary Disease supports."
    mutations = propose_mutations(parent=parent, n=5, seed=7)
    for m in mutations:
        # Each mutation's target must be a real substring of the parent
        # (else apply_mutation would raise)
        if m.target == m.replacement:
            # No-op mutation acceptable as fallback
            continue
        assert m.target in parent, f"target {m.target!r} not in parent"


def test_propose_mutations_zero_n_returns_empty():
    mutations = propose_mutations(parent="anything", n=0)
    assert mutations == []
