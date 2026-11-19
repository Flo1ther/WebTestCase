import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorText } from "../services/api";
import type { AIAnalysis, Defect, Execution, TestCase } from "../types";
import { Badge, Loader, Modal, Notice } from "../components/ui";
import { AIResult } from "../components/AIResult";
import { useAuth } from "../context/AuthContext";

export function TestCaseDetail() {
  const { id, projectId } = useParams();
  const { user } = useAuth();
  const [testCase, setTestCase] = useState<TestCase>();
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [runs, setRuns] = useState<
    { id: number; name: string; project: number; test_case_ids: number[] }[]
  >([]);
  const [modal, setModal] = useState<"execute" | "defect" | "ai" | null>(null);
  const [analysis, setAnalysis] = useState<AIAnalysis>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = () =>
    Promise.all([
      api.get(`/test-cases/${id}/`),
      api.get("/executions/", { params: { test_case: id } }),
      api.get("/defects/", { params: { test_case: id } }),
      api.get("/test-runs/"),
    ])
      .then(
        ([
          testCaseResponse,
          executionResponse,
          defectResponse,
          runResponse,
        ]) => {
          setTestCase(testCaseResponse.data);
          setExecutions(executionResponse.data.results);
          setDefects(defectResponse.data.results);
          setRuns(runResponse.data.results);
        },
      )
      .catch((requestError) => setError(errorText(requestError)));
  useEffect(() => {
    setAnalysis(undefined);
    void load();
  }, [id]);
  const submitExecution = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const payload: any = {
        ...Object.fromEntries(new FormData(event.currentTarget)),
        test_case: Number(id),
      };
      if (payload.test_run) payload.test_run = Number(payload.test_run);
      else delete payload.test_run;
      await api.post("/executions/", payload);
      setModal(null);
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  const submitDefect = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const payload: any = {
        ...Object.fromEntries(new FormData(event.currentTarget)),
        test_case: Number(id),
        status: "OPEN",
      };
      if (payload.test_run) payload.test_run = Number(payload.test_run);
      else delete payload.test_run;
      await api.post("/defects/", payload);
      setModal(null);
      await load();
    } catch (requestError) {
      setError(errorText(requestError));
    }
  };
  const analyze = async () => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/ai/analyze-test-case/", {
        test_case_id: Number(id),
      });
      setAnalysis(data);
      setModal("ai");
    } catch (requestError) {
      setError(errorText(requestError));
    } finally {
      setBusy(false);
    }
  };
  if (error && !testCase) return <Notice text={error} />;
  if (!testCase) return <Loader />;
  const assigned = user?.role === "TESTER" && testCase.assigned_to === user.id;
  const projectPath = projectId
    ? `/projects/${projectId}`
    : `/projects/${testCase.project}`;
  const caseEditPath = projectId
    ? `/projects/${projectId}/test-cases/${id}/edit`
    : `/test-cases/${id}/edit`;
  const canExecute = user?.role !== "TESTER" || assigned;
  return (
    <>
      <div className="page-heading">
        <div>
          <Link className="back" to={`${projectPath}/test-cases`}>
            Тесткейси проєкту
          </Link>
          <h1>{testCase.title}</h1>
          <p>{testCase.project_name}</p>
        </div>
        <div className="actions">
          {canExecute && (
            <button type="button" className="primary" onClick={() => setModal("execute")}>
              Виконати тест
            </button>
          )}
          {(assigned || user?.role !== "TESTER") && (
            <button type="button" onClick={() => setModal("defect")}>
              Повідомити про дефект
            </button>
          )}
          <button type="button" onClick={analyze} disabled={busy}>
            {busy ? "Аналізування…" : "Проаналізувати за допомогою ШІ"}
          </button>
          {user?.role !== "TESTER" && <Link to={caseEditPath}>Редагувати</Link>}
        </div>
      </div>
      {error && <Notice text={error} />}
      <section className="detail-grid">
        <div className="panel">
          <h2>Сценарій</h2>
          <p>{testCase.description}</p>
          <h3>Передумови</h3>
          <p>{testCase.preconditions || "Не вказано"}</p>
          <h3>Очікуваний результат</h3>
          <p>{testCase.expected_result}</p>
        </div>
        <aside className="panel meta">
          <div>
            <span>Стан</span>
            <Badge value={testCase.status} />
          </div>
          <div>
            <span>Пріоритет</span>
            <Badge value={testCase.priority} />
          </div>
          <div>
            <span>Призначений тестувальник</span>
            <strong>{testCase.assigned_to_name || "Не призначено"}</strong>
          </div>
          <div>
            <span>Автор</span>
            <strong>{testCase.created_by_name}</strong>
          </div>
        </aside>
      </section>
      <section className="panel">
        <h2>Кроки перевірки</h2>
        <ol className="steps">
          {testCase.steps.map((step) => (
            <li key={step.id}>
              <strong>{step.action}</strong>
              <span>Очікується: {step.expected_result}</span>
            </li>
          ))}
        </ol>
      </section>
      <section className="dashboard-grid">
        <div className="panel">
          <h2>Історія виконання</h2>
          {executions.map((execution) => (
            <div className="history" key={execution.id}>
              <Badge value={execution.status} />
              <div>
                <strong>{execution.tester_name}</strong>
                <p>{execution.actual_result}</p>
                <small>
                  {new Date(execution.executed_at).toLocaleString("uk-UA")}
                </small>
              </div>
            </div>
          ))}
          {!executions.length && (
            <p className="muted">Історії виконання ще немає.</p>
          )}
        </div>
        <div className="panel">
          <h2>Пов’язані дефекти</h2>
          {defects.map((defect) => (
            <div className="history" key={defect.id}>
              <Badge value={defect.status} />
              <div>
                <strong>{defect.title}</strong>
                <p>{defect.description}</p>
              </div>
            </div>
          ))}
          {!defects.length && <p className="muted">Дефектів ще немає.</p>}
        </div>
      </section>
      {modal === "execute" && (
        <Modal title="Виконати тест" onClose={() => setModal(null)}>
          <form onSubmit={submitExecution}>
            <label>
              Test Run
              <select name="test_run" defaultValue="">
                <option value="">Позапланове виконання</option>
                {runs
                  .filter(
                    (run) =>
                      run.project === testCase.project &&
                      run.test_case_ids.includes(testCase.id),
                  )
                  .map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name}
                    </option>
                  ))}
              </select>
              <small>Вибір прогону оновить його реальний прогрес.</small>
            </label>
            <label>
              Стан результату
              <select name="status" required>
                <option value="PASSED">Пройдено</option>
                <option value="FAILED">Не пройдено</option>
                <option value="BLOCKED">Заблоковано</option>
                <option value="NOT_RUN">Не виконано</option>
              </select>
            </label>
            <label>
              Фактичний результат
              <textarea name="actual_result" required minLength={5} rows={4} />
            </label>
            <label>
              Коментар
              <textarea name="comment" rows={3} />
            </label>
            <div className="form-actions">
              <button type="button" onClick={() => setModal(null)}>
                Скасувати
              </button>
              <button type="submit" className="primary">Зберегти виконання</button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "defect" && (
        <Modal title="Повідомити про дефект" onClose={() => setModal(null)}>
          <form onSubmit={submitDefect}>
            <label>
              Назва
              <input name="title" required minLength={5} />
            </label>
            <label>
              Опис
              <textarea
                name="description"
                required
                minLength={10}
                rows={4}
                placeholder="Що саме сталося?"
              />
            </label>
            <label>
              Кроки відтворення
              <textarea
                name="reproduction_steps"
                rows={3}
                defaultValue={testCase.steps
                  .map((step) => `${step.step_number}. ${step.action}`)
                  .join("\n")}
              />
            </label>
            <label>
              Очікуваний результат
              <textarea
                name="expected_result"
                rows={2}
                defaultValue={testCase.expected_result}
              />
            </label>
            <label>
              Фактичний результат
              <textarea
                name="actual_result"
                rows={2}
                defaultValue={executions[0]?.actual_result || ""}
              />
            </label>
            <div className="form-grid">
              <label>
                Severity
                <select name="severity" defaultValue="MEDIUM">
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
              <label>
                Priority
                <select name="priority" defaultValue={testCase.priority}>
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Test Run
              <select name="test_run" defaultValue="">
                <option value="">Без прив’язки до прогону</option>
                {runs
                  .filter((run) => run.project === testCase.project)
                  .map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Версія продукту
              <input name="product_version" placeholder="1.0.0" />
            </label>
            <label>
              Середовище
              <input name="environment" placeholder="staging / Chrome 128" />
            </label>
            <div className="form-actions">
              <button type="button" onClick={() => setModal(null)}>
                Скасувати
              </button>
              <button type="submit" className="primary">Створити дефект</button>
            </div>
          </form>
        </Modal>
      )}
      {modal === "ai" && analysis && (
        <Modal title="Аналіз ШІ" onClose={() => setModal(null)}>
          <AIResult
            analysis={analysis}
            currentUpdatedAt={testCase.updated_at}
          />
          <div className="form-actions">
            <button type="button" onClick={() => setModal(null)}>Закрити</button>
          </div>
        </Modal>
      )}
    </>
  );
}
