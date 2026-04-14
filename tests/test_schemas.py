from app.schemas.idea import IdeaInput


def test_idea_schema_trims_keywords_and_claims() -> None:
    idea = IdeaInput(
        idea_id="IDEA-1",
        title="Transparent prior art overlap baseline",
        abstract="This abstract is long enough to pass validation and describe the idea in a clear way.",
        keywords=[" retrieval ", " ", "evidence"],
        claims=[" explainable verdict ", ""],
    )

    assert idea.keywords == ["retrieval", "evidence"]
    assert idea.claims == ["explainable verdict"]
