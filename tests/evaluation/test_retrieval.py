from pathlib import Path

from fabcopilot.evaluation.retrieval import load_dataset


def test_retrieval_dataset_has_bilingual_labeled_cases() -> None:
    project_root = Path(__file__).resolve().parents[2]

    documents, cases = load_dataset(project_root / "evals" / "retrieval_cases.json")

    assert len(documents) == 15
    assert len(cases) == 60
    assert any(
        any("\u4e00" <= char <= "\u9fff" for char in case.query) for case in cases
    )
    assert any(case.query.isascii() for case in cases)
    document_ids = {document.document_id for document in documents}
    assert all(case.relevant_document_ids <= document_ids for case in cases)
