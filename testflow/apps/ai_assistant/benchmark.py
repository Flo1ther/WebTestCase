"""Small, versioned regression benchmark for deterministic QA review rules."""
from .copilot import DeterministicReviewer


CASES = [
 {"id":"invalid_success","payload":{"title":"Invalid payment","description":"d","preconditions":"Checkout open","expected_result":"Оплату успішно виконано.","steps":[{"action":"Ввести невалідний номер картки","expected_result":"Оплата успішна"}]},"requirements":[],"expected":{"LOG-INVALID-SUCCESS"}},
 {"id":"password_requirement","payload":{"title":"Short password","description":"d","preconditions":"Form open","expected_result":"Користувача успішно зареєстровано.","steps":[{"action":"Ввести пароль з 5 символів","expected_result":"Form submitted"}]},"requirements":[{"key":"REQ-8","title":"Password","description":"Пароль повинен містити щонайменше 8 символів.","priority":"HIGH"}],"expected":{"REQ-MIN-LENGTH"}},
 {"id":"missing_precondition","payload":{"title":"Save","description":"d","preconditions":"","expected_result":"Saved","steps":[{"action":"Click save","expected_result":"Saved"}]},"requirements":[],"expected":{"STR-preconditions"}},
 {"id":"missing_step_result","payload":{"title":"Save","description":"d","preconditions":"Signed in","expected_result":"Saved","steps":[{"action":"Click save","expected_result":""}]},"requirements":[],"expected":{"STR-0-expected_result"}},
 {"id":"correct_case","payload":{"title":"Successful sign in","description":"d","preconditions":"Active user exists","expected_result":"Dashboard opens","steps":[{"action":"Enter valid email and password","expected_result":"Credentials accepted"}]},"requirements":[],"expected":set()},
 {"id":"ambiguous_without_requirement","payload":{"title":"Business rule","description":"d","preconditions":"System available","expected_result":"Correct discount applied","steps":[{"action":"Apply promotion","expected_result":"Price updated"}]},"requirements":[],"expected":set()},
]


def run_benchmark():
    reviewer=DeterministicReviewer(); tp=fp=fn=0; details=[]
    for item in CASES:
        context={"requirements":item["requirements"],"related_cases":[],"suites":[],"execution_history":[],"defects":[],"limitations":[]}
        found={finding["id"] for finding in reviewer.review(item["payload"],context)}
        expected=item["expected"]
        hit=found & expected; extra=found-expected; missed=expected-found
        tp+=len(hit);fp+=len(extra);fn+=len(missed)
        details.append({"id":item["id"],"expected":sorted(expected),"found":sorted(found),"false_positives":sorted(extra),"false_negatives":sorted(missed)})
    precision=tp/(tp+fp) if tp+fp else 1.0; recall=tp/(tp+fn) if tp+fn else 1.0
    return {"precision":round(precision,3),"recall":round(recall,3),"f1":round(2*precision*recall/(precision+recall),3) if precision+recall else 0,"true_positives":tp,"false_positives":fp,"false_negatives":fn,"dataset_cases":len(CASES)}, details
