# Проєктно-орієнтований QA workflow

## Мета

Проєкт є кореневим робочим простором WebTestCase. Дані тестування не існують як ізольована таблиця: кожна вимога, ручний тест, API-тест, прогін, виконання та дефект належать одному проєкту.

## Робочий сценарій

1. Менеджер створює Project і заповнює опис та AI context.
2. У межах Project створює Requirements з критеріями приймання.
3. Для Requirement створює manual Test Case або API Test. AI може запропонувати чернетку, але не зберігає її без підтвердження менеджера.
4. Менеджер групує ручні кейси в Test Suite та Test Run.
5. Тестувальник виконує призначений кейс. Backend створює новий TestExecution зі знімком тесткейсу й проєктом; попередні виконання не перезаписуються.
6. Якщо результат не відповідає очікуванню, тестувальник створює Defect. Defect успадковує Project і, коли є зв’язок, Requirement тесткейсу.
7. Project workspace рахує покриття Requirement тестами, прогрес, результати та відкриті дефекти.

## Інваріанти backend

- Requirement, Test Case і APITest повинні належати одному Project.
- Test Run може містити лише Test Case свого Project.
- TestExecution отримує Project з Test Case на сервері.
- Defect отримує Project з Test Case на сервері.
- TESTER бачить тільки проєкти, де є призначені йому тесткейси.
- AI draft зберігає проектний контекст; на старих посиланнях проєкт фіксується щойно менеджер приймає чернетку.

## Проєктні API-зведення

- `GET /api/projects/{id}/workspace/` - основні метрики, покриття та останні події.
- `GET /api/projects/{id}/analytics/` - метрики тільки цього проєкту.
- `GET /api/projects/{id}/reports/` - payload звіту для UI або експорту.
- `GET /api/projects/{id}/ai/coverage-summary/` - текстовий summary покриття без залежності від LLM.

## Демонстрація

Виконайте `python manage.py seed_demo` та `python manage.py seed_quality_demo`. Відкрийте `Demo Store API`, вимогу `REQ-CHECKOUT-01` і зв’язаний ручний/API-тест. API runner фіксує контрольований FAIL: Demo API повертає `201`, хоча вимога та API-тест очікують `400` для невалідного payment token.
