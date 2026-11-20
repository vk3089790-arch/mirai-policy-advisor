"""
Automated Test Suite for Example-Question Shortcuts in app.py
Tests clicking Q1..Q5, verifies text_input population, visibility persistence, and form submission.
"""

from streamlit.testing.v1 import AppTest

EXPECTED_QUESTIONS = [
    (0, "Q1", "I have 72% attendance this semester. How many attendance marks will I receive, and am I eligible to appear for the final examination?"),
    (1, "Q2", "Within how many days after recovery must a student submit supporting documents for Medical Leave? What happens if the documents are submitted after this period?"),
    (2, "Q3", "What is the monthly subscription fee for using the campus swimming pool and indoor squash court?"),
    (3, "Q4", "What minimum percentage of batch-student support is required to propose a new student club, and which authority reviews the proposal first?"),
    (4, "Q5", "What is the default WPA2 password for the Mirai_Student_5G campus Wi-Fi network?")
]

def test_shortcuts():
    print("=" * 80)
    print("STARTING TEST: Example-Question Shortcuts Verification in app.py")
    print("=" * 80)

    # 1. Start AppTest instance
    at = AppTest.from_file("app.py", default_timeout=25)
    at.run()
    assert len(at.exception) == 0, f"Initial errors: {at.exception}"
    print("[PASS] Initial application run clean (Zero exceptions).")

    # 2. Test each shortcut button sequentially
    for btn_idx, q_code, expected_text in EXPECTED_QUESTIONS:
        # Find the button by key
        target_btn = [b for b in at.button if b.key == f"ex_btn_{btn_idx}"][0]
        print(f"\n--- Testing Click for {q_code} Shortcut ---")
        print(f"Action: Click button '{target_btn.label}'")
        target_btn.click()
        at.run()

        assert len(at.exception) == 0, f"Exception after clicking {q_code}: {at.exception}"

        # Inspect populated input
        actual_input_val = at.text_input[0].value
        print(f"Expected Input: \"{expected_text}\"")
        print(f"Actual Input:   \"{actual_input_val}\"")

        assert actual_input_val == expected_text, f"Mismatch for {q_code}!"
        print(f"Status: [{q_code} SHORTCUT POPULATION PASS]")

    # 3. Test that populated question remains visible before and after another run
    print("\n--- Testing Visibility Persistence ---")
    current_val = at.text_input[0].value
    at.run()
    assert at.text_input[0].value == current_val, "Input value did not persist across rerun!"
    print(f"Input value persisted across script rerun: \"{at.text_input[0].value[:60]}...\"")
    print("Status: [VISIBILITY PERSISTENCE PASS]")

    # 4. Test Form Submission with Populated Question (Testing Q3 as safe test without Gemini quota consumption)
    print("\n--- Testing Form Submission with Selected Shortcut (Q3) ---")
    q3_btn = [b for b in at.button if b.key == "ex_btn_2"][0]
    q3_btn.click()
    at.run()
    selected_q = at.text_input[0].value
    print(f"Selected for submission: \"{selected_q}\"")

    submit_btn = [b for b in at.button if b.label == "🔍 Ask Advisor"][0]
    submit_btn.click()
    at.run()

    assert len(at.exception) == 0, f"Exception on form submission: {at.exception}"
    
    # Verify input is still visible after submission
    print(f"Input value after submission: \"{at.text_input[0].value}\"")
    assert at.text_input[0].value == selected_q, "Input was cleared unexpectedly!"

    # Verify message in session history matches submitted question
    submitted_msg = at.session_state.messages[0]
    print(f"Session history recorded question: \"{submitted_msg['question']}\"")
    assert submitted_msg["question"] == selected_q, "Submitted question was not used by advisor!"
    print(f"Advisor generated response: \"{submitted_msg['answer']}\"")
    print("Status: [FORM SUBMISSION INTEGRATION PASS]")

    print("\n" + "=" * 80)
    print("ALL 10 REQUIREMENTS VERIFIED WITH ACTUAL OUTPUTS: 100% PASS")
    print("=" * 80)

if __name__ == "__main__":
    test_shortcuts()
