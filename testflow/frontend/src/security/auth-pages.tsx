import { useCallback, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  KeyRound,
  ListChecks,
  Mail,
  ShieldCheck,
} from "lucide-react";
import { api, csrf, errorMessage } from "./api";
import { useAuth, useToast } from "./state";
import {
  Brand,
  Button,
  Captcha,
  Field,
  PasswordInput,
  PasswordStrength,
  ThemeToggle,
  passwordRules,
} from "./ui";

const strong = z
  .string()
  .max(128, "Не більше 128 символів.")
  .superRefine((password, ctx) => {
    for (const rule of passwordRules)
      if (!rule.test(password))
        ctx.addIssue({ code: "custom", message: rule.label });
  });
const registration = z
  .object({
    first_name: z.string().min(1, "Вкажіть ім’я.").max(150),
    last_name: z.string().min(1, "Вкажіть прізвище.").max(150),
    email: z.email("Перевірте email."),
    password: strong,
    password_confirm: z.string(),
  })
  .refine((d) => d.password === d.password_confirm, {
    message: "Паролі не збігаються.",
    path: ["password_confirm"],
  });
type Registration = z.infer<typeof registration>;
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-layout">
      <aside className="auth-aside">
        <Brand />
        <div className="auth-story">
          <span className="eyebrow">КЕРУВАННЯ ЯКІСТЮ ПРОДУКТУ</span>
          <h1>
            Тестуйте.
            <br />
            <span>Контролюйте якість.</span>
          </h1>
          <p>
            Створюйте вимоги й тесткейси, фіксуйте виконання та аналізуйте
            результати в одному робочому просторі.
          </p>
          <div className="auth-features">
            <div>
              <ListChecks />
              <span>Вимоги та покриття тестами</span>
            </div>
            <div>
              <ClipboardCheck />
              <span>Ручні тесткейси та виконання</span>
            </div>
            <div>
              <BarChart3 />
              <span>Дефекти, звіти й аналітика</span>
            </div>
          </div>
        </div>
        <small className="auth-footer">
          WEBTESTCASE · УПРАВЛІННЯ ТЕСТ-КЕЙСАМИ
        </small>
      </aside>
      <section className="auth-main">
        <div className="auth-theme">
          <ThemeToggle />
        </div>
        <main className="auth-form">{children}</main>
      </section>
    </div>
  );
}
function GoogleButton() {
  const { config } = useAuth(),
    toast = useToast();
  const [busy, setBusy] = useState(false);
  return (
    <>
      <Button
        className="secondary full"
        busy={busy}
        disabled={!config?.google_enabled}
        onClick={async () => {
          setBusy(true);
          try {
            await csrf();
            const r = await api.post("/auth/oidc/start/");
            window.location.assign(r.data.url);
          } catch (e) {
            toast(errorMessage(e), true);
            setBusy(false);
          }
        }}
      >
        <span className="google-g">G</span>Увійти через Google
      </Button>
      {config && !config.google_enabled && (
        <small className="muted center">
          Вхід через Google ще не налаштовано.
        </small>
      )}
    </>
  );
}
export function RegisterPage() {
  const { config } = useAuth(),
    toast = useToast(),
    navigate = useNavigate();
  const [token, setToken] = useState(""),
    [resetKey, setResetKey] = useState(0);
  const onToken = useCallback((t: string) => setToken(t), []);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Registration>({
    resolver: zodResolver(registration),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      password_confirm: "",
    },
  });
  const activationMessage = config?.email_verification_required
    ? "Після реєстрації відкрийте одноразове посилання з листа Mailpit, щоб активувати акаунт."
    : "У цьому середовищі email активується одразу після реєстрації.";
  return (
    <>
      <span className="eyebrow">ПОЧНІМО ЗІ ЗНАЙОМСТВА</span>
      <h1>Створіть акаунт</h1>
      <p className="muted">{activationMessage}</p>
      <form
        onSubmit={handleSubmit(async (data) => {
          try {
            await csrf();
            const r = await api.post("/auth/register/", {
              ...data,
              captcha_token: token,
            });
            toast(r.data.message);
            navigate(
              r.data.email_verification_required ? "/check-email" : "/login",
            );
          } catch (e) {
            toast(errorMessage(e), true);
            setToken("");
            setResetKey((x) => x + 1);
          }
        })}
      >
        <div className="form-row">
          <Field label="Ім’я" error={errors.first_name?.message}>
            <input {...register("first_name")} autoComplete="given-name" />
          </Field>
          <Field label="Прізвище" error={errors.last_name?.message}>
            <input {...register("last_name")} autoComplete="family-name" />
          </Field>
        </div>
        <Field label="Email" error={errors.email?.message}>
          <input
            {...register("email")}
            type="email"
            autoComplete="email"
            placeholder="name@example.com"
          />
        </Field>
        <Field label="Пароль" error={errors.password?.message}>
          <PasswordInput
            registration={register("password")}
            autoComplete="new-password"
          />
        </Field>
        <PasswordStrength password={watch("password")} />
        <Field
          label="Повторіть пароль"
          error={errors.password_confirm?.message}
        >
          <PasswordInput
            registration={register("password_confirm")}
            autoComplete="new-password"
          />
        </Field>
        {config && (
          <Captcha
            siteKey={config.turnstile_site_key}
            onToken={onToken}
            resetKey={resetKey}
          />
        )}
        <Button
          type="submit"
          className="full"
          busy={isSubmitting}
          disabled={!token}
        >
          Створити акаунт <ArrowRight size={16} />
        </Button>
      </form>
      <p className="center muted">
        Уже маєте акаунт? <Link to="/login">Увійти</Link>
      </p>
    </>
  );
}
export function LoginPage() {
  const toast = useToast(),
    navigate = useNavigate(),
    { refresh } = useAuth(),
    [params] = useSearchParams();
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<{ email: string; password: string }>();
  return (
    <>
      <span className="eyebrow">РОБОЧИЙ ПРОСТІР ТЕСТУВАННЯ</span>
      <h1>Увійдіть до WebTestCase</h1>
      <p className="muted">
        Перейдіть до проєктів, вимог, тесткейcів і результатів перевірок.
      </p>
      {params.get("error") === "google" && (
        <div className="notice bad">
          Не вдалося завершити Google-вхід. Перевірте налаштування або увійдіть
          до наявного акаунта й прив’яжіть Google.
        </div>
      )}
      <GoogleButton />
      <div className="divider">
        <span>або за допомогою email</span>
      </div>
      <form
        onSubmit={handleSubmit(async (data) => {
          try {
            await csrf();
            const r = await api.post("/auth/login/", data);
            await csrf();
            if (r.data.requires_2fa) {
              await refresh();
              navigate("/two-factor");
              return;
            }
            const user = await refresh();
            navigate(
              user?.role === "ADMIN" && user.email_verified
                ? "/security/overview"
                : "/dashboard",
            );
          } catch (e) {
            toast(errorMessage(e), true);
          }
        })}
      >
        <Field label="Email">
          <input
            {...register("email", { required: true })}
            type="email"
            autoComplete="email"
          />
        </Field>
        <Field label="Пароль">
          <PasswordInput
            registration={register("password", { required: true })}
          />
        </Field>
        <Link className="forgot-link" to="/forgot-password">
          Забули пароль?
        </Link>
        <Button type="submit" busy={isSubmitting} className="full">
          Увійти <ArrowRight size={16} />
        </Button>
      </form>
      <p className="center muted">
        Немає акаунта? <Link to="/register">Зареєструватися</Link>
      </p>
    </>
  );
}
export function OTPPage() {
  const toast = useToast(),
    navigate = useNavigate(),
    { refresh } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<{ code: string }>();
  return (
    <>
      <span className="auth-symbol">
        <ShieldCheck />
      </span>
      <h1>Підтвердьте вхід</h1>
      <p className="muted">
        Введіть код із застосунку автентифікації або одноразовий резервний код.
      </p>
      <form
        onSubmit={handleSubmit(async (data) => {
          try {
            await csrf();
            await api.post("/auth/two-factor/", data);
            await csrf();
            const user = await refresh();
            navigate(
              user?.role === "ADMIN" ? "/security/overview" : "/dashboard",
            );
          } catch (e) {
            toast(errorMessage(e), true);
          }
        })}
      >
        <Field label="Код підтвердження">
          <input
            {...register("code", { required: true, maxLength: 128 })}
            autoComplete="one-time-code"
            className="otp-input"
          />
        </Field>
        <Button type="submit" busy={isSubmitting} className="full">
          Підтвердити вхід
        </Button>
      </form>
      <Link className="center block" to="/login">
        Повернутися до входу
      </Link>
    </>
  );
}
export function EmailPage({ verify = false }: { verify?: boolean }) {
  const toast = useToast(),
    [params] = useSearchParams(),
    [done, setDone] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<{ email: string }>();
  const [busy, setBusy] = useState(false);
  return (
    <>
      <span className="auth-symbol">
        <Mail />
      </span>
      <h1>{verify ? "Підтвердження email" : "Перевірте пошту"}</h1>
      <p className="muted">
        {done
          ? "Email підтверджено. Тепер можна увійти до акаунта."
          : "Відкрийте лист від WebTestCase й підтвердьте свою адресу. Посилання діє 24 години."}
      </p>
      {verify && !done ? (
        <Button
          className="full"
          busy={busy}
          disabled={!params.get("token")}
          onClick={async () => {
            setBusy(true);
            try {
              await csrf();
              await api.post("/auth/verify-email/", {
                token: params.get("token"),
              });
              setDone(true);
              toast("Email підтверджено.");
            } catch (e) {
              toast(errorMessage(e), true);
            } finally {
              setBusy(false);
            }
          }}
        >
          Підтвердити email
        </Button>
      ) : done ? (
        <Link className="btn full" to="/login">
          Перейти до входу
        </Link>
      ) : null}
      {!done && (
        <form
          onSubmit={handleSubmit(async (data) => {
            try {
              await csrf();
              const r = await api.post("/auth/resend/", data);
              toast(r.data.message);
            } catch (e) {
              toast(errorMessage(e), true);
            }
          })}
        >
          <Field label="Email для повторного листа">
            <input type="email" {...register("email", { required: true })} />
          </Field>
          <Button busy={isSubmitting} type="submit" className="secondary full">
            Надіслати лист повторно
          </Button>
        </form>
      )}
      <Link className="center block" to="/login">
        Повернутися до входу
      </Link>
    </>
  );
}
export function ForgotPage() {
  const toast = useToast();
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<{ email: string }>();
  return (
    <>
      <span className="auth-symbol">
        <KeyRound />
      </span>
      <h1>Відновлення доступу</h1>
      <p className="muted">
        Надішлемо посилання для встановлення нового пароля. Воно діятиме 30
        хвилин.
      </p>
      <form
        onSubmit={handleSubmit(async (data) => {
          try {
            await csrf();
            const r = await api.post("/auth/forgot-password/", data);
            toast(r.data.message);
          } catch (e) {
            toast(errorMessage(e), true);
          }
        })}
      >
        <Field label="Email">
          <input
            type="email"
            {...register("email", { required: true })}
            autoComplete="email"
          />
        </Field>
        <Button type="submit" className="full" busy={isSubmitting}>
          Надіслати посилання
        </Button>
      </form>
      <Link className="center block" to="/login">
        Повернутися до входу
      </Link>
    </>
  );
}
const resetSchema = z
  .object({ password: strong, password_confirm: z.string() })
  .refine((d) => d.password === d.password_confirm, {
    path: ["password_confirm"],
    message: "Паролі не збігаються.",
  });
export function ResetPage() {
  const toast = useToast(),
    navigate = useNavigate(),
    [params] = useSearchParams();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
    defaultValues: { password: "", password_confirm: "" },
  });
  return (
    <>
      <span className="auth-symbol">
        <KeyRound />
      </span>
      <h1>Новий пароль</h1>
      <p className="muted">
        Оберіть надійний пароль. Після зміни попередні сеанси буде завершено.
      </p>
      <form
        onSubmit={handleSubmit(async (data) => {
          try {
            await csrf();
            const r = await api.post("/auth/reset-password/", {
              ...data,
              token: params.get("token"),
            });
            toast(r.data.message);
            navigate("/login");
          } catch (e) {
            toast(errorMessage(e), true);
          }
        })}
      >
        <Field label="Новий пароль" error={errors.password?.message}>
          <PasswordInput
            registration={register("password")}
            autoComplete="new-password"
          />
        </Field>
        <PasswordStrength password={watch("password")} />
        <Field
          label="Повторіть пароль"
          error={errors.password_confirm?.message}
        >
          <PasswordInput
            registration={register("password_confirm")}
            autoComplete="new-password"
          />
        </Field>
        <Button
          type="submit"
          className="full"
          busy={isSubmitting}
          disabled={!params.get("token")}
        >
          Зберегти пароль
        </Button>
      </form>
    </>
  );
}
