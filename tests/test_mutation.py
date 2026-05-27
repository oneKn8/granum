from granum.center.mutation import (
    Mutation,
    MutationKind,
    apply_mutation,
)


def test_citation_swap_changes_only_one_citation():
    parent = "Per Aetna CPB 0119 we appeal. ACC/AHA 2021 §6.2 supports."
    new = apply_mutation(
        parent,
        Mutation(kind=MutationKind.CITATION_SWAP, target="Aetna CPB 0119", replacement="Aetna CPB 0286"),
    )
    assert "Aetna CPB 0286" in new
    assert "ACC/AHA 2021 §6.2" in new  # other citation preserved
    assert "Aetna CPB 0119" not in new


def test_paragraph_reframe_preserves_citations():
    parent = "The procedure is medically necessary. Per Aetna CPB 0119, coverage applies."
    new = apply_mutation(
        parent,
        Mutation(
            kind=MutationKind.PARAGRAPH_REFRAME,
            target="The procedure is medically necessary.",
            replacement="The submitted documentation demonstrates medical necessity beyond Aetna's threshold for coverage.",
        ),
    )
    assert "Aetna CPB 0119" in new
    assert "submitted documentation demonstrates" in new
    assert "The procedure is medically necessary." not in new


def test_evidence_reorder_changes_order_only():
    parent = "First: clinical change documented. Second: prior stress imaging negative."
    new = apply_mutation(
        parent,
        Mutation(
            kind=MutationKind.EVIDENCE_REORDER,
            target="First: clinical change documented. Second: prior stress imaging negative.",
            replacement="First: prior stress imaging negative. Second: clinical change documented.",
        ),
    )
    assert "First: prior stress imaging" in new
    assert "Second: clinical change" in new


def test_invalid_mutation_kind_raises():
    import pytest
    with pytest.raises(ValueError, match="unknown mutation kind"):
        apply_mutation("text", Mutation(kind="prompt_rewrite", target="x", replacement="y"))  # type: ignore


def test_target_not_found_raises():
    import pytest
    with pytest.raises(ValueError, match="target .* not found"):
        apply_mutation(
            "Per Aetna CPB 0119 we appeal.",
            Mutation(kind=MutationKind.CITATION_SWAP, target="Aetna CPB 9999", replacement="X"),
        )


def test_only_first_occurrence_replaced():
    parent = "Aetna CPB 0119 first. Aetna CPB 0119 second."
    new = apply_mutation(
        parent,
        Mutation(kind=MutationKind.CITATION_SWAP, target="Aetna CPB 0119", replacement="Aetna CPB 0286"),
    )
    assert new == "Aetna CPB 0286 first. Aetna CPB 0119 second."
