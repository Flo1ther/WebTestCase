-- TestFlow. Набір SQL-тестів бази даних.
-- Запускайте окремий тест кнопкою F5 у Query Tool бази testflow.

-- Тест 1. Перевірка підключення до бази даних.
SELECT current_database() AS database_name, current_schema() AS schema_name, current_user AS connected_user;

-- Тест 2. Перевірка структури бази даних.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Тест 3. Перевірка демонстраційних даних.
SELECT 'Users' AS entity, COUNT(*) AS record_count FROM accounts_user
UNION ALL SELECT 'Projects', COUNT(*) FROM projects_project
UNION ALL SELECT 'Test cases', COUNT(*) FROM test_cases_testcase
UNION ALL SELECT 'Test steps', COUNT(*) FROM test_cases_teststep
UNION ALL SELECT 'Executions', COUNT(*) FROM executions_testexecution
UNION ALL SELECT 'Defects', COUNT(*) FROM defects_defect
UNION ALL SELECT 'AI analyses', COUNT(*) FROM ai_assistant_aianalysis
UNION ALL SELECT 'Audit logs', COUNT(*) FROM audit_auditlog
ORDER BY entity;

-- Тест 4. Перевірка зв'язку «Проєкт - Тест-кейс».
SELECT
    p.name AS project,
    tc.id AS test_case_id,
    tc.title AS test_case,
    tc.priority,
    tc.status,
    assigned.username AS assigned_tester
FROM projects_project AS p
LEFT JOIN test_cases_testcase AS tc ON tc.project_id = p.id
LEFT JOIN accounts_user AS assigned ON assigned.id = tc.assigned_to_id
ORDER BY p.name, tc.id;

-- Тест 5. Перевірка кроків тест-кейсу.
SELECT
    tc.title AS test_case,
    step.step_number,
    step.action,
    step.expected_result
FROM test_cases_teststep AS step
JOIN test_cases_testcase AS tc ON tc.id = step.test_case_id
ORDER BY tc.title, step.step_number;

-- Тест 6. Перевірка історії виконання тест-кейсів.
SELECT
    execution.id,
    tc.title AS test_case,
    tester.username AS tester,
    execution.status,
    execution.actual_result,
    execution.comment,
    execution.executed_at
FROM executions_testexecution AS execution
JOIN test_cases_testcase AS tc ON tc.id = execution.test_case_id
JOIN accounts_user AS tester ON tester.id = execution.tester_id
ORDER BY execution.executed_at DESC;

-- Тест 7. Перевірка статистики результатів виконання.
SELECT
    status,
    COUNT(*) AS execution_count
FROM executions_testexecution
GROUP BY status
ORDER BY status;

-- Тест 8. Перевірка дефектів тест-кейсів.
SELECT
    defect.id,
    defect.title AS defect,
    defect.status,
    tc.title AS related_test_case,
    reporter.username AS reported_by,
    defect.created_at
FROM defects_defect AS defect
JOIN test_cases_testcase AS tc ON tc.id = defect.test_case_id
JOIN accounts_user AS reporter ON reporter.id = defect.reported_by_id
ORDER BY defect.created_at DESC;

-- Тест 9. Перевірка результатів AI Assistant.
SELECT
    analysis.id,
    analysis.analysis_type,
    analysis.provider,
    analysis.model_name,
    requester.username AS requested_by,
    tc.title AS test_case,
    analysis.result ->> 'mode' AS mode,
    analysis.result ->> 'summary' AS summary,
    analysis.created_at
FROM ai_assistant_aianalysis AS analysis
JOIN accounts_user AS requester ON requester.id = analysis.requested_by_id
LEFT JOIN test_cases_testcase AS tc ON tc.id = analysis.test_case_id
ORDER BY analysis.created_at DESC;

-- Тест 10. Перевірка журналу аудиту.
SELECT
    log.created_at,
    user_account.username AS performed_by,
    log.action,
    log.entity_type,
    log.entity_id,
    log.metadata
FROM audit_auditlog AS log
LEFT JOIN accounts_user AS user_account ON user_account.id = log.user_id
ORDER BY log.created_at DESC;

-- Тест 11. Перевірка посилальної цілісності даних.
SELECT tc.id, tc.title, tc.project_id
FROM test_cases_testcase AS tc
LEFT JOIN projects_project AS p ON p.id = tc.project_id
WHERE p.id IS NULL;

-- Тест 12. Пошук тест-кейсів без виконання.
SELECT tc.id, tc.title, p.name AS project, tc.status
FROM test_cases_testcase AS tc
JOIN projects_project AS p ON p.id = tc.project_id
LEFT JOIN executions_testexecution AS execution ON execution.test_case_id = tc.id
WHERE execution.id IS NULL
ORDER BY tc.id;
