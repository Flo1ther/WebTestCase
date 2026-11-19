# Лабораторна робота 12 — рефакторинг і дизайн-патерни

## Мета

Вдосконалити наявну архітектуру WebTestCase без зміни предметної області: винести правила життєвого циклу тестового прогону з API-в'ю та розділити створення серверних звітів за типами.

## Початковий стан і проблема

`TestRun.status` зберігався в PostgreSQL, але створення, зміна та інтерпретація статусу не мали одного центру правил. Менеджер міг надіслати звичайний `PATCH` зі значенням статусу, а API не розрізняло доменні команди «запустити» і «завершити». Це ускладнювало додавання нових станів і не захищало завершений прогін від нових виконань.

Ендпоінт проєктного звіту також формував один фіксований payload прямо у view. Додавання матриці трасування або звіту прогресу збільшувало б один метод умовами та запитами до моделей.

## Патерн State: Test Run

Реалізовано `apps/executions/run_state.py`.

```text
DraftRunState --start--> ActiveRunState --complete--> CompletedRunState
      |                         |                         |
   complete: error           start: error              start/complete: error
```

`TestRunWorkflow` відновлює об'єкт стану за рядком `status`, що зберігається у PostgreSQL. Класи `DraftRunState`, `ActiveRunState` та `CompletedRunState` інкапсулюють дозволені переходи. `TestRunViewSet` отримав команди:

```text
POST /api/test-runs/{id}/start/
POST /api/test-runs/{id}/complete/
```

Пряме оновлення `status` через PATCH відхиляється serializer-ом. Виконання тесту, прив'язане до прогону, можна додавати тільки до стану `ACTIVE`. Після `COMPLETED` прогін лишається історичним записом; для наступного запуску створюється новий Test Run. Події переходів записуються в журнал аудиту.

## Патерн Factory Method: звіти проєкту

Реалізовано `apps/reports/factories.py`.

```text
ProjectReportCreator
  ├── QualitySummaryReportCreator  -> QualitySummaryReport
  ├── TraceabilityReportCreator    -> TraceabilityReport
  └── ExecutionProgressReportCreator -> ExecutionProgressReport
```

Базовий creator має метод `generate_report()`, який працює зі спільною абстракцією `ProjectReport`. Конкретні creator-и перевизначають лише `create_report()`. View не залежить від конкретних класів звітів: вона викликає `creator_for(type)`.

Доступні типи на одному серверному ендпоінті:

| Запит | Результат |
|---|---|
| `GET /api/projects/{id}/reports/?type=quality` | Якість: загальні показники, failed test cases, відкриті дефекти |
| `GET /api/projects/{id}/reports/?type=traceability` | Покриття вимог ручними та API-тестами, список непокритих вимог |
| `GET /api/projects/{id}/reports/?type=execution` | Прогони, прогрес і історія виконань |

Без параметра використовується `quality`, тому попередній сценарій не змінився.

## Тести

`tests/test_lab12_patterns.py` перевіряє:

1. неможливість завершити чернетку;
2. перехід `DRAFT → ACTIVE → COMPLETED` через API-команди;
3. заборону прямого PATCH статусу;
4. можливість виконання лише в активному прогоні;
5. неможливість повторно запустити або виконувати завершений прогін;
6. формування трьох типів звітів фабрикою та помилку для невідомого типу.

Запуск усіх перевірок:

```powershell
cd D:\WTC\testflow
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run build
```

## Результат

`State` прибрав правила переходів із контролера та зробив їх розширюваними: для нового стану достатньо додати клас, а не змінювати кілька view. `Factory Method` ізолював типи звітів; додатковий звіт потребує нового класу report і creator-а, без переписування API-в'ю. Обидва патерни інтегровані в робочі сценарії WebTestCase та покриті автоматизованими тестами.
