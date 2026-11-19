import { label } from "../labels";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
import api, { errorText } from "../services/api";
import type { ListResponse, Project, TestCase, User } from "../types";
import {
  Badge,
  Empty,
  Loader,
  Modal,
  Notice,
  Pagination,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
const statuses = ["", "PASSED", "FAILED", "BLOCKED", "NOT_RUN"];
const priorities = ["", "LOW", "MEDIUM", "HIGH", "CRITICAL"];
export function TestCases() {
  const { projectId } = useParams();
  const [data, setData] = useState<ListResponse<TestCase>>({
      count: 0,
      results: [],
      next: null,
      previous: null,
    }),
    [filters, setFilters] = useState<any>({
      page: 1,
      search: "",
      status: "",
      priority: "",
      project: projectId || "",
    }),
    [err, setErr] = useState("");
  const { user } = useAuth();
  const load = () =>
    api
      .get("/test-cases/", {
        params: { ...filters, project: projectId || filters.project },
      })
      .then((r) => setData(r.data))
      .catch((e) => setErr(errorText(e)));
  useEffect(() => {
    setFilters((value: any) => ({ ...value, project: projectId || "" }));
  }, [projectId]);
  useEffect(() => {
    load();
  }, [filters, projectId]);
  const del = async (id: number) => {
    if (confirm("Видалити цей тесткейс?"))
      try {
        await api.delete(`/test-cases/${id}/`);
        load();
      } catch (e) {
        setErr(errorText(e));
      }
  };
  const createPath = projectId
    ? `/projects/${projectId}/test-cases/create`
    : "/test-cases/create";
  const casePath = (id: number) =>
    projectId ? `/projects/${projectId}/test-cases/${id}` : `/test-cases/${id}`;
  const editPath = (id: number) =>
    projectId
      ? `/projects/${projectId}/test-cases/${id}/edit`
      : `/test-cases/${id}/edit`;
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>{projectId ? "Тесткейси проєкту" : "Тесткейси"}</h1>
          <p>Створюйте, призначайте й відстежуйте сценарії перевірок.</p>
        </div>
        {user?.role !== "TESTER" && (
          <Link className="primary" to={createPath}>
            <Plus size={17} />
            Новий тесткейс
          </Link>
        )}
      </div>
      <div className="toolbar">
        <input
          placeholder="Пошук за назвою або описом"
          value={filters.search}
          onChange={(e) =>
            setFilters({ ...filters, search: e.target.value, page: 1 })
          }
        />
        <select
          value={filters.status}
          onChange={(e) =>
            setFilters({ ...filters, status: e.target.value, page: 1 })
          }
        >
          {statuses.map((x) => (
            <option value={x} key={x}>
              {label(x) || "Усі стани"}
            </option>
          ))}
        </select>
        <select
          value={filters.priority}
          onChange={(e) =>
            setFilters({ ...filters, priority: e.target.value, page: 1 })
          }
        >
          {priorities.map((x) => (
            <option value={x} key={x}>
              {label(x) || "Усі пріоритети"}
            </option>
          ))}
        </select>
      </div>
      {err && <Notice text={err} />}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Тесткейс</th>
              <th>Вимога</th>
              <th>Пріоритет</th>
              <th>Стан</th>
              <th>Тестувальник</th>
              <th>Створено</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.results.map((c) => (
              <tr key={c.id}>
                <td data-label="Тесткейс">
                  <Link to={casePath(c.id)}>{c.title}</Link>
                </td>
                <td data-label="Вимога">{c.requirement_key || "Не вибрано"}</td>
                <td data-label="Пріоритет">
                  <Badge value={c.priority} />
                </td>
                <td data-label="Стан">
                  <Badge value={c.status} />
                </td>
                <td data-label="Тестувальник">
                  {c.assigned_to_name || "Не призначено"}
                </td>
                <td data-label="Створено">
                  {new Date(c.created_at).toLocaleDateString()}
                </td>
                <td className="row-actions">
                  <Link to={casePath(c.id)}>Переглянути</Link>
                  {user?.role !== "TESTER" && (
                    <>
                      <Link to={editPath(c.id)}>Редагувати</Link>
                      <button
                        type="button"
                        className="danger icon-button"
                        title="Видалити"
                        onClick={() => del(c.id)}
                      >
                        <Trash2 size={15} />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.results.length && <Empty>Тесткейси не знайдено.</Empty>}
      </div>
      <Pagination
        count={data.count}
        page={filters.page}
        setPage={(page) => setFilters({ ...filters, page })}
      />
    </>
  );
}
export function TestCaseForm() {
  const { id, projectId } = useParams();
  const nav = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]),
    [requirements, setRequirements] = useState<any[]>([]),
    [testers, setTesters] = useState<User[]>([]),
    [caseData, setCaseData] = useState<Partial<TestCase>>({
      project: projectId ? Number(projectId) : undefined,
      priority: "MEDIUM",
      status: "NOT_RUN",
      steps: [{ step_number: 1, action: "", expected_result: "" }],
    }),
    [err, setErr] = useState("");
  const editing = Boolean(id);
  useEffect(() => {
    Promise.all([
      api.get("/projects/"),
      api.get("/assignable-testers/"),
      id ? api.get(`/test-cases/${id}/`) : Promise.resolve(null),
    ])
      .then(([p, u, c]) => {
        setProjects(p.data.results);
        setTesters(u.data.results);
        if (c) setCaseData(c.data);
      })
      .catch((e) => setErr(errorText(e)));
  }, [id]);
  useEffect(() => {
    if (caseData.project)
      api
        .get("/requirements/", {
          params: { project: caseData.project, page_size: 100 },
        })
        .then((r) => setRequirements(r.data.results))
        .catch((e) => setErr(errorText(e)));
    else setRequirements([]);
  }, [caseData.project]);
  const set = (k: string, v: any) => setCaseData((x) => ({ ...x, [k]: v }));
  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (
      !caseData.steps?.every((s) => s.action.trim() && s.expected_result.trim())
    )
      return setErr("Кожен крок має містити дію та очікуваний результат.");
    try {
      const payload = {
        ...caseData,
        automation_key: (caseData.automation_key || "").trim().toUpperCase(),
        project: Number(caseData.project),
        requirement: caseData.requirement ? Number(caseData.requirement) : null,
        assigned_to: caseData.assigned_to ? Number(caseData.assigned_to) : null,
      };
      editing
        ? await api.put(`/test-cases/${id}/`, payload)
        : await api.post("/test-cases/", payload);
      nav(projectId ? `/projects/${projectId}/test-cases` : "/test-cases");
    } catch (e) {
      setErr(errorText(e));
    }
  };
  const back = projectId ? `/projects/${projectId}/test-cases` : "/test-cases";
  return (
    <>
      <div className="page-heading">
        <div>
          <Link className="back" to={back}>
            Тесткейси
          </Link>
          <h1>{editing ? "Редагувати тесткейс" : "Створити тесткейс"}</h1>
        </div>
      </div>
      {err && <Notice text={err} />}
      <form className="form-panel" onSubmit={save}>
        <div className="form-grid">
          <label>
            Назва
            <input
              value={caseData.title || ""}
              onChange={(e) => set("title", e.target.value)}
              required
              minLength={4}
            />
          </label>
          <label>
            Проєкт
            <select
              value={caseData.project || ""}
              onChange={(e) => {
                set("project", e.target.value);
                set("requirement", null);
              }}
              required
              disabled={Boolean(projectId)}
            >
              <option value="">Оберіть проєкт</option>
              {projects.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Вимога
            <select
              value={caseData.requirement || ""}
              onChange={(e) => set("requirement", e.target.value)}
              disabled={!caseData.project}
            >
              <option value="">Без прямого зв’язку</option>
              {requirements.map((r) => (
                <option value={r.id} key={r.id}>
                  {r.key} · {r.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ключ автоматизації
            <input
              value={caseData.automation_key || ""}
              onChange={(e) => set("automation_key", e.target.value)}
              placeholder="TC-AUTH-LOGIN"
            />
            <small>
              Необов’язково. Використовується GitHub CI для зв’язування
              результату з тесткейcом.
            </small>
          </label>
          <label>
            Пріоритет
            <select
              value={caseData.priority}
              onChange={(e) => set("priority", e.target.value)}
            >
              {priorities.slice(1).map((x) => (
                <option key={x} value={x}>
                  {label(x)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Призначений тестувальник
            <select
              value={caseData.assigned_to || ""}
              onChange={(e) => set("assigned_to", e.target.value)}
            >
              <option value="">Не призначено</option>
              {testers.map((t) => (
                <option value={t.id} key={t.id}>
                  {t.full_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Опис
          <textarea
            value={caseData.description || ""}
            onChange={(e) => set("description", e.target.value)}
            required
            minLength={10}
            rows={4}
          />
        </label>
        <label>
          Передумови
          <textarea
            value={caseData.preconditions || ""}
            onChange={(e) => set("preconditions", e.target.value)}
            rows={3}
          />
        </label>
        <fieldset>
          <legend>Кроки перевірки</legend>
          {caseData.steps?.map((s, i) => (
            <div className="step" key={i}>
              <strong>{i + 1}</strong>
              <input
                placeholder="Дія"
                value={s.action}
                onChange={(e) => {
                  const a = [...caseData.steps!];
                  a[i] = { ...s, action: e.target.value };
                  set("steps", a);
                }}
              />
              <input
                placeholder="Очікуваний результат"
                value={s.expected_result}
                onChange={(e) => {
                  const a = [...caseData.steps!];
                  a[i] = { ...s, expected_result: e.target.value };
                  set("steps", a);
                }}
              />
              {caseData.steps!.length > 1 && (
                <button
                  type="button"
                  onClick={() =>
                    set(
                      "steps",
                      caseData.steps!.filter((_, j) => j !== i),
                    )
                  }
                >
                  Прибрати
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              set("steps", [
                ...caseData.steps!,
                {
                  step_number: caseData.steps!.length + 1,
                  action: "",
                  expected_result: "",
                },
              ])
            }
          >
            Додати крок
          </button>
        </fieldset>
        <label>
          Очікуваний результат
          <textarea
            value={caseData.expected_result || ""}
            onChange={(e) => set("expected_result", e.target.value)}
            required
            rows={3}
          />
        </label>
        <div className="form-actions">
          <Link to={back}>Скасувати</Link>
          <button type="submit" className="primary">
            {editing ? "Зберегти зміни" : "Створити тесткейс"}
          </button>
        </div>
      </form>
    </>
  );
}
