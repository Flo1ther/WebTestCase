import { label } from "../labels";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api, { errorText } from "../services/api";
import { Empty, Loader, Notice } from "../components/ui";

type Overview = {
  total_test_cases: number;
  total_executions: number;
  passed: number;
  failed: number;
  blocked: number;
  not_run: number;
  pass_rate: number;
  failure_rate: number;
  execution_coverage: number;
  open_defects: number;
};
const date = (value: string) =>
  value ? new Date(value).toLocaleDateString("uk-UA") : "";
export function Analytics() {
  const [overview, setOverview] = useState<Overview>(),
    [trends, setTrends] = useState<any[]>([]),
    [projects, setProjects] = useState<any[]>([]),
    [stability, setStability] = useState<any[]>([]),
    [error, setError] = useState("");
  const load = () =>
    Promise.all([
      api.get("/analytics/overview/"),
      api.get("/analytics/execution-trends/"),
      api.get("/analytics/project-comparison/"),
      api.get("/analytics/test-stability/"),
    ])
      .then(([a, b, c, d]) => {
        setOverview(a.data);
        setTrends(b.data.map((x: any) => ({ ...x, day: date(x.day) })));
        setProjects(c.data);
        setStability(d.data);
      })
      .catch((e) => setError(errorText(e)));
  useEffect(() => {
    void load();
  }, []);
  if (error) return <Notice text={error} />;
  if (!overview) return <Loader />;
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Аналітика</h1>
          <p>
            Якість виконання, покриття та стабільність сценаріїв за даними
            системи.
          </p>
        </div>
      </div>
      <section className="stats analytics-stats">
        {[
          ["Тесткейси", overview.total_test_cases],
          ["Виконання", overview.total_executions],
          ["Частка успішних перевірок", `${overview.pass_rate}%`],
          ["Частка невдач", `${overview.failure_rate}%`],
          ["Покриття", `${overview.execution_coverage}%`],
          ["Відкриті дефекти", overview.open_defects],
        ].map(([label, value]) => (
          <div className="stat" key={String(label)}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>
      <section className="dashboard-grid">
        <div className="panel chart-panel">
          <h2>Динаміка виконання</h2>
          {trends.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  name="Пройдено"
                  dataKey="passed"
                  stroke="#168a63"
                />
                <Line
                  type="monotone"
                  name="Не пройдено"
                  dataKey="failed"
                  stroke="#ca3f45"
                />
                <Line
                  type="monotone"
                  name="Заблоковано"
                  dataKey="blocked"
                  stroke="#b77a00"
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Empty>За цей період немає даних про виконання.</Empty>
          )}
        </div>
        <div className="panel chart-panel">
          <h2>Порівняння проєктів</h2>
          {projects.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={projects}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar
                  name="Усього тесткейсів"
                  dataKey="total_cases"
                  fill="#3478b8"
                />
                <Bar name="Виконано" dataKey="completed_cases" fill="#1aa085" />
                <Bar name="Не пройдено" dataKey="failed_cases" fill="#cc5551" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty>Немає доступних проєктів.</Empty>
          )}
        </div>
      </section>
      <section className="panel">
        <h2>Стабільність тестів</h2>
        <div className="compact-list">
          {stability.map((item) => (
            <div key={item.test_case_id}>
              <span>
                <strong>{item.title}</strong>
                <small>
                  {item.project} · {item.reason}
                </small>
              </span>
              <b
                className={`stability ${item.stability.toLowerCase().replace(" ", "-")}`}
              >
                {label(item.stability)}
              </b>
            </div>
          ))}
          {!stability.length && <Empty>Немає доступних тесткейсів.</Empty>}
        </div>
      </section>
    </>
  );
}
