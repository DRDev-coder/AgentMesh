from __future__ import annotations

from evaluation.run_company_workflows import run_company_evaluation


def test_ten_company_upload_release_playground_and_api_key_workflows() -> None:
    result = run_company_evaluation(use_groq=False)

    assert result["metadata"]["company_count"] == 10
    assert result["summary"]["failed"] == 0, [
        {
            "company": company["company_name"],
            "failed_cases": [
                case["id"]
                for case in company["cases"]
                if not case["playground"]["passed"]
                or (case["api_key"] is not None and not case["api_key"]["passed"])
            ],
        }
        for company in result["companies"]
    ]

    for company in result["companies"]:
        assert company["release"]["version"] == 1
        for upload in company["uploads"]:
            assert upload["background_job"]["status"] == "COMPLETED"
            assert upload["version"]["status"] == "READY_FOR_REVIEW"
            assert upload["version"]["extraction_error"] is None
            assert upload["version"]["chunk_count"] > 0
