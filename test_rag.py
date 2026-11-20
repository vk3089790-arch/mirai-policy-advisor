"""
Mirai School of Technology Academic & Hostel Policy Advisor
Module: Comprehensive Assessment Test Suite
Executes the five mandatory evaluation questions and records outputs to assessment_results.json.
"""

import json
import logging
import os
import sys

# Suppress harmless warnings
import warnings
warnings.filterwarnings("ignore")

from rag import answer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EVALUATION_QUESTIONS = [
    {
        "id": "Q1",
        "question": "I have 72% attendance this semester. How many attendance marks will I receive, and am I eligible to appear for the final examination?",
        "expected_pages": [7],
        "expected_status": "supported",
        "expected_summary": "4 marks; strictly debarred from appearing in final exam unless condoned up to 15% via medical exemption."
    },
    {
        "id": "Q2",
        "question": "Within how many days after recovery must a student submit supporting documents for Medical Leave? What happens if the documents are submitted after this period?",
        "expected_pages": [24],
        "expected_status": "supported",
        "expected_summary": "Within 7 days of recovery to Campus Manager. If submitted late, strictly rejected with zero relaxation and treated as unauthorized absence."
    },
    {
        "id": "Q3",
        "question": "What is the monthly subscription fee for using the campus swimming pool and indoor squash court?",
        "expected_pages": [],
        "expected_status": "not_found",
        "expected_summary": "[not found] - Swimming pool and squash court facilities are not documented in the handbook."
    },
    {
        "id": "Q4",
        "question": "What minimum percentage of batch-student support is required to propose a new student club, and which authority reviews the proposal first?",
        "expected_pages": [38],
        "expected_status": "supported",
        "expected_summary": "At least 40% batch-student support. First reviewed by designated Faculty Coordinator before forwarding to Management."
    },
    {
        "id": "Q5",
        "question": "What is the default WPA2 password for the Mirai_Student_5G campus Wi-Fi network?",
        "expected_pages": [],
        "expected_status": "not_found",
        "expected_summary": "[not found] - Campus Wi-Fi passwords and credentials are not documented in the handbook."
    }
]


def run_assessment(output_file: str = "assessment_results.json"):
    """
    Executes all 5 evaluation questions, validates behavior, and saves results to JSON.
    """
    results = []
    print("=" * 80)
    print("STARTING ASSESSMENT: University Academic & Hostel Policy Advisor")
    print("=" * 80)

    for item in EVALUATION_QUESTIONS:
        qid = item["id"]
        q_text = item["question"]
        print(f"\n--- Testing {qid} ---")
        print(f"Question: {q_text}")

        res = answer(q_text)
        ans = res.get("answer", "")
        sources = res.get("sources", [])

        print(f"Generated Answer:\n{ans}")
        print(f"Sources: {sources}")

        # Verification check
        if item["expected_status"] == "not_found":
            passed = (ans.strip() == "[not found]") and (len(sources) == 0)
        else:
            has_expected_page = any(p in sources for p in item["expected_pages"]) if item["expected_pages"] else True
            passed = (ans.strip() != "[not found]") and has_expected_page

        status_label = "PASS" if passed else "FLAGGED"
        print(f"Test Status: [{status_label}]")

        results.append({
            "id": qid,
            "question": q_text,
            "actual_answer": ans,
            "actual_sources": sources,
            "expected_status": item["expected_status"],
            "expected_pages": item["expected_pages"],
            "expected_summary": item["expected_summary"],
            "status": status_label
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"All {len(results)} questions tested. Results saved to {output_file}.")
    print("=" * 80)
    return results


if __name__ == "__main__":
    run_assessment()
