"""Deterministic, evidence-based services used by AI QA Copilot.

The rules are deliberately general rather than tailored to one demo scenario.  They
produce evidence and a repair candidate; an LLM may add semantic review on top.
"""
from __future__ import annotations

import re
from collections import Counter


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def finding(fid, category, severity, title, field, evidence, reason, recommendation, proof="formal_check", before="", after=""):
    return {"id": fid, "category": category, "severity": severity, "title": title,
            "field": field, "evidence": evidence, "reason": reason,
            "recommendation": recommendation, "evidence_type": proof,
            "confidence": "deterministic" if proof == "formal_check" else "contextual",
            "fix": {"before": before or evidence, "after": after, "related_fields": []} if after else None}


class ContextBuilder:
    """Build a bounded project-context envelope from objects already authorised by views."""
    def build(self, case):
        requirements = list(case.requirements.select_related("project").all()[:10])
        siblings = list(case.project.test_cases.exclude(pk=case.pk).order_by("-updated_at")[:12])
        suites = list(case.suites.all()[:8])
        executions = list(case.executions.select_related("tester").order_by("-executed_at")[:8])
        defects = list(case.defects.order_by("-created_at")[:8])
        return {
            "project": {"id": case.project_id, "name": case.project.name, "description": case.project.description[:1200], "ai_context": case.project.ai_context[:2400]},
            "requirements": [{"key": r.key, "title": r.title, "description": r.description[:1800], "priority": r.priority} for r in requirements],
            "related_cases": [{"id": item.id, "title": item.title, "expected_result": item.expected_result[:500]} for item in siblings],
            "suites": [{"id": item.id, "name": item.name} for item in suites],
            "execution_history": [{"status": item.status, "actual_result": item.actual_result[:500]} for item in executions],
            "defects": [{"title": item.title, "status": item.status, "actual_result": item.actual_result[:500]} for item in defects],
            "limitations": [] if requirements else ["Немає пов’язаної Requirement: перевірка відповідності бізнес-вимогам обмежена."],
        }


class DeterministicReviewer:
    """Checks structure and generic formal contradictions with auditable evidence."""
    def review(self, payload, context):
        issues = []
        for field, label in (("title", "назву"), ("description", "опис"), ("preconditions", "передумови"), ("expected_result", "очікуваний результат")):
            if not (payload.get(field) or "").strip():
                issues.append(finding(f"STR-{field}", "structure", "HIGH", f"Відсутня {label}", field, "", f"Не заповнено {label} тесткейсу.", f"Додайте конкретну {label}."))
        steps = payload.get("steps", [])
        if not steps:
            issues.append(finding("STR-STEPS", "structure", "CRITICAL", "Відсутні кроки", "steps", "", "Сценарій неможливо відтворити без дій.", "Додайте нумеровані кроки та перевірки."))
        for index, step in enumerate(steps):
            for key, label in (("action", "дію"), ("expected_result", "очікуваний результат")):
                if not (step.get(key) or "").strip():
                    issues.append(finding(f"STR-{index}-{key}", "structure", "HIGH", f"Крок {index+1}: відсутня {label}", f"steps.{index}.{key}", "", f"У кроці {index+1} не вказано {label}.", f"Заповніть {label}, який можна спостерігати."))
        all_expected = " ".join([payload.get("expected_result", "")] + [s.get("expected_result", "") for s in steps])
        all_actions = " ".join([payload.get("preconditions", "")] + [s.get("action", "") for s in steps])
        self._contradictions(issues, payload, all_actions, all_expected, context)
        self._requirement_checks(issues, payload, all_actions, all_expected, context)
        self._duplicates(issues, payload, context)
        return self._dedupe(issues)

    def _contradictions(self, issues, payload, actions, expected, context):
        a, e = _norm(actions), _norm(expected)
        invalid = re.search(r"(?:некорект|невалід|порожн|неправильн|invalid|wrong)", a)
        # Do not confuse a correct negative expectation such as “HTTP 400; order not created”
        # with a successful operation merely because it contains the word “created”.
        success = re.search(r"(?:успіш\w*|оплачено|дозволяє|\bsuccess\b|\bpaid\b|(?<!не )створено)", e)
        rejection = re.search(r"(?:помилк|валідац|\bhttp\s*[45]\d\d\b|не\s+створен|не\s+викон|відхилен|rejected|error|fail)", e)
        if invalid and success and not rejection:
            issues.append(finding("LOG-INVALID-SUCCESS", "logic", "CRITICAL", "Неочікуваний успіх для некоректних даних", "expected_result", payload.get("expected_result", ""), "Кроки містять некоректні або порожні дані, але очікується успішна операція.", "Уточніть правило. Якщо дані мають бути невалідними, очікуйте помилку валідації та відсутність побічного ефекту.", "formal_check", payload.get("expected_result", ""), "Система показує повідомлення про помилку; операція не виконується."))
        correct_credentials = re.search(r"(?:правильн(?:ий|і)?|валідн(?:ий|і)?).{0,50}(?:парол|email|обліков)", a)
        wrong_password = re.search(r"(?:неправильн|некоректн).{0,50}парол", e)
        if correct_credentials and wrong_password:
            issues.append(finding("LOG-CREDENTIALS", "logic", "HIGH", "Суперечність для правильних облікових даних", "expected_result", payload.get("expected_result", ""), "Передумови або кроки називають дані правильними, але результат очікує помилку пароля.", "Або використайте невалідний пароль, або очікуйте успішний вхід.", "formal_check"))
        for match in re.finditer(r"(\d+(?:[.,]\d+)?)\s*%", a):
            percent = float(match.group(1))
            money = re.findall(r"(\d[\d\s]{1,12})\s*(?:грн|uah)", a)
            expected_money = re.findall(r"(\d[\d\s]{1,12})\s*(?:грн|uah)", e)
            if money and expected_money and 0 < percent < 100:
                base = float(money[0].replace(" ", "")); actual = float(expected_money[-1].replace(" ", "")); calculated = round(base * (1 - percent / 100), 2)
                if abs(actual - calculated) > .01:
                    issues.append(finding("LOG-PERCENT", "logic", "HIGH", "Некоректний розрахунок відсотка", "expected_result", str(actual), f"Від {base:g} зі знижкою {percent:g}% очікувана сума {calculated:g}, але вказано {actual:g}.", f"Замініть очікувану суму на {calculated:g}.", "formal_check", str(actual), str(calculated)))

    def _requirement_checks(self, issues, payload, actions, expected, context):
        joined = " ".join(r["description"] for r in context["requirements"])
        match = re.search(r"(?:щонайменше|не менше|at least|min(?:imum)?)\s+(\d+)\s*(?:символ|character)", joined, re.I)
        if not match:
            return
        limit = int(match.group(1))
        given = re.search(r"(?:парол|password).{0,60}?(\d+)\s*(?:символ|character)", actions, re.I)
        if given and int(given.group(1)) < limit and re.search(r"(?:успіш|зареєстр|створен|success)", _norm(expected)):
            issues.append(finding("REQ-MIN-LENGTH", "requirement", "CRITICAL", "Expected result суперечить обмеженню Requirement", "expected_result", payload.get("expected_result", ""), f"Requirement задає мінімум {limit} символів, а сценарій використовує {given.group(1)} та очікує успіх.", "Очікуйте помилку валідації та відсутність створеного облікового запису.", "requirement_match", payload.get("expected_result", ""), "Система показує помилку мінімальної довжини; реєстрацію не виконано."))

    def _duplicates(self, issues, payload, context):
        title = _norm(payload.get("title"))
        for other in context["related_cases"]:
            candidate = _norm(other["title"])
            if title and candidate and (title == candidate or title in candidate or candidate in title):
                issues.append(finding(f"DUP-{other['id']}", "coverage", "MEDIUM", "Можливий дублікат тесткейсу", "title", payload.get("title", ""), f"Назва подібна до Test Case #{other['id']}: «{other['title']}».", "Порівняйте дані та очікувані результати; за потреби об’єднайте або уточніть межі сценаріїв.", "context_match"))

    @staticmethod
    def _dedupe(items):
        result, seen = [], set()
        for item in items:
            key = (item["category"], item["field"], _norm(item["reason"]))
            if key not in seen:
                result.append(item); seen.add(key)
        return result


class TextScenarioReviewer:
    """Auditable checks for a pasted requirement before it becomes a test case.

    These are domain-independent consistency checks, not a catalog of demo phrases:
    numbers must add up, invalid input must not be marked successful, and a browser
    refresh must not silently repeat a state-changing operation.
    """
    @staticmethod
    def _excerpt(text, start, end):
        left = max(text.rfind('\n', 0, start), text.rfind('.', 0, start), text.rfind('!', 0, start), text.rfind('?', 0, start)) + 1
        right_options = [pos for pos in (text.find('\n', end), text.find('.', end), text.find('!', end), text.find('?', end)) if pos >= 0]
        right = min(right_options) if right_options else len(text)
        return text[left:right].strip()[:600]

    def review(self, text):
        issues, normalized = [], _norm(text)

        # A percentage-based calculation can be validated only when the source
        # prices and the stated total are both explicitly present in the text.
        percent = re.search(r"([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%", text)
        if percent:
            before, after = text[:percent.start()], text[percent.end():]
            money = r"([0-9]{1,9}(?: [0-9]{3})*(?:[.,][0-9]{1,2})?)"
            prices = [float(value.replace(' ', '').replace(',', '.')) for value in re.findall(rf"(?:вартіст[^\s]*|цін[^\s]*|price)\s*(?:товару\s*)?{money}\s*(?:грн|uah|₴)", before, re.I)]
            stated = re.search(rf"(?:сума|вартіст[^\s]*)[^\n]{{0,80}}(?:становить|дорівнює|=)\s*{money}\s*(?:грн|uah|₴)", after, re.I)
            if prices and stated:
                base, discount = sum(prices), float(percent.group(1).replace(',', '.'))
                actual = float(stated.group(1).replace(' ', '').replace(',', '.'))
                calculated = round(base * (1 - discount / 100), 2)
                if 0 < discount < 100 and abs(actual - calculated) > .01:
                    evidence = self._excerpt(text, percent.start(), percent.end()) + '. ' + self._excerpt(text, percent.end() + stated.start(), percent.end() + stated.end())
                    issues.append(finding('TEXT-PERCENT', 'logic', 'HIGH', 'Некоректний розрахунок відсотка', 'text', evidence,
                        f'Сума позицій {base:g} зі знижкою {discount:g}% дорівнює {calculated:g}, але вказано {actual:g}.',
                        f'Уточніть правило або змініть очікувану суму на {calculated:g}.', 'formal_check', str(actual), str(calculated)))

        invalid = re.search(r"(?:некорект\w*|невалід\w*|порожн\w*|неправильн\w*|invalid|wrong)", normalized)
        success = re.search(r"(?:успіш\w*|оплат[ау]\s+виконан\w*|\bуспішн\w*\s+створен\w*|(?<!не )\bоплачено\b|(?<!не )\bстворен\w*)", normalized)
        rejected = re.search(r"(?:помилк\w*|валідац\w*|\bhttp\s*[45]\d\d\b|не\s+створен\w*|не\s+викон\w*|відхилен\w*|rejected|error|fail)", normalized)
        if invalid and success and not rejected:
            issues.append(finding('TEXT-INVALID-SUCCESS', 'logic', 'CRITICAL', 'Неочікуваний успіх для невалідних даних', 'text', self._excerpt(text, success.start(), success.end()),
                'Опис містить невалідні або некоректні дані, але очікує успішне завершення операції.',
                'Для невалідних даних очікуйте зрозумілу помилку та відсутність створеного або оплаченого запису.', 'formal_check'))

        refresh = re.search(r"(?:оновити\s+сторінк\w*|оновленн\w*\s+сторінк\w*|refresh(?:\s+the)?\s+page)", normalized)
        repeated = re.search(r"(?:автоматичн\w*.{0,50}(?:повторн\w*|ще\s+одн\w*)|(?:повторн\w*|ще\s+одн\w*).{0,50}(?:створен\w*|замовлен\w*|запис\w*))", normalized)
        if refresh and repeated:
            issues.append(finding('TEXT-REPEAT-SIDE-EFFECT', 'logic', 'HIGH', 'Повторна операція після оновлення сторінки', 'text', self._excerpt(text, repeated.start(), repeated.end()),
                'Оновлення сторінки не повинно без явної дії користувача повторювати операцію зі зміною стану.',
                'Очікуйте збереження одного запису; для повторного запиту перевірте ідемпотентність операції.', 'formal_check'))
        return DeterministicReviewer._dedupe(issues)


class CoverageAnalyzer:
    scenario_catalog = [
        ("positive", "Успішне виконання основного сценарію"),
        ("negative", "Відхилення невалідних даних"),
        ("boundary", "Граничні значення параметрів"),
        ("duplicate", "Повторна операція або дубльований запит"),
    ]
    def analyze(self, requirement):
        cases = list(requirement.test_cases.prefetch_related("steps").all())
        corpus = " ".join(_norm(" ".join([case.title, case.description, case.expected_result])) for case in cases)
        covered, missing = [], []
        for key, label in self.scenario_catalog:
            tokens = {"positive": ["успіш", "valid"], "negative": ["некорект", "невалід", "помил"], "boundary": ["гранич", "мінім", "максим", "довжин"], "duplicate": ["повтор", "дубл", "ідемпот"]}[key]
            (covered if any(token in corpus for token in tokens) else missing).append({"type": key, "title": label})
        suggestions = [{"title": f"{entry['title']}: {requirement.title}", "description": requirement.description, "preconditions": "Система доступна; Requirement затверджена.", "steps": [{"action": f"Виконати сценарій: {entry['title'].lower()}.", "expected_result": "Система поводиться відповідно до Requirement."}], "expected_result": "Результат відповідає Requirement.", "priority": requirement.priority, "scenario_type": entry["type"]} for entry in missing]
        return {"requirement": {"id": requirement.id, "key": requirement.key, "title": requirement.title}, "linked_cases": [{"id": case.id, "title": case.title} for case in cases], "confirmed_scenarios": covered, "potential_gaps": missing, "suggestions": suggestions, "scope": "Це евристика за текстом пов’язаних тестів. Кількість тесткейсів не є доказом повноти покриття."}
