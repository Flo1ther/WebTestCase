import { FormEvent, useEffect, useState } from "react";
import api, { errorText } from "../services/api";
import { Empty, Loader, Notice } from "../components/ui";

type Project = { id: number; name: string };
type TestCase = { id: number; title: string; project: number };
type Suite = {
  id: number;
  name: string;
  description: string;
  project: number;
  test_case_ids: number[];
  created_at: string;
};

export function TestSuites() {
  const [suites, setSuites] = useState<Suite[]>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [cases, setCases] = useState<TestCase[]>([]);
  const [project, setProject] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const load = () =>
    api
      .get("/test-suites/")
      .then((r) => setSuites(r.data.results))
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    load();
    api
      .get("/projects/")
      .then((r) => setProjects(r.data.results))
      .catch((e) => setError(errorText(e)));
    api
      .get("/test-cases/?page_size=100")
      .then((r) => setCases(r.data.results))
      .catch((e) => setError(errorText(e)));
  }, []);
  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSaving(true);
    setError("");
    try {
      await api.post("/test-suites/", {
        project: Number(project),
        name: form.get("name"),
        description: form.get("description"),
        test_case_ids: selected,
      });
      event.currentTarget.reset();
      setSelected([]);
      await load();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  };
  if (!suites) return <Loader />;
  const available = cases.filter((item) => String(item.project) === project);
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Набори тестів</h1>
          <p>Повторно використовувані Smoke, Regression та Release-набори.</p>
        </div>
      </div>
      {error && <Notice text={error} />}
      <form className="form-panel" onSubmit={create}>
        <h2>Створити Test Suite</h2>
        <label>
          Проєкт
          <select
            required
            value={project}
            onChange={(e) => {
              setProject(e.target.value);
              setSelected([]);
            }}
          >
            <option value="">Оберіть проєкт</option>
            {projects.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Назва набору
          <input
            name="name"
            required
            minLength={3}
            placeholder="Smoke checkout"
          />
        </label>
        <label>
          Призначення набору
          <textarea
            name="description"
            rows={3}
            placeholder="Критичні перевірки перед релізом"
          />
        </label>
        <label>
          Тесткейси
          <select
            multiple
            required
            value={selected.map(String)}
            onChange={(e) =>
              setSelected(
                Array.from(e.currentTarget.selectedOptions).map((option) =>
                  Number(option.value),
                ),
              )
            }
          >
            {available.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
          <small>Оберіть один або кілька тесткейсів поточного проєкту.</small>
        </label>
        <button
          type="submit"
          className="primary"
          disabled={saving || !project || !selected.length}
        >
          {saving ? "Збереження…" : "Створити набір"}
        </button>
      </form>
      <section className="panel">
        <h2>Створені набори</h2>
        {suites.length ? (
          <div className="compact-list">
            {suites.map((item) => (
              <div key={item.id}>
                <span>
                  <strong>{item.name}</strong>
                  <small>{item.description || "Без опису"}</small>
                  <small>
                    {item.test_case_ids?.length || 0} тесткейсів · проєкт #
                    {item.project}
                  </small>
                </span>
              </div>
            ))}
          </div>
        ) : (
          <Empty>Наборів ще немає. Створіть Smoke або Regression-набір.</Empty>
        )}
      </section>
    </>
  );
}
