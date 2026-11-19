# Інтеграція безпеки Secura у WebTestCase

Усі механізми додано **до наявного проєкту** `D:\WTC\testflow`. Використовуються чинні `accounts.User`, PostgreSQL, проєкти, тесткейси, виконання й дефекти. Окрема база чи другий паралельний набір акаунтів не створюються. Початкові зміни користувача збережено; резервна копія коду до інтеграції — `C:\Users\shevc\Documents\ChatGPT\Sec\output\WebTestCase-before-integration-20261026.zip`. Архів містить локальну конфігурацію, тому не публікуйте його.

## Що додано

- Нові реєстрації отримують роль TESTER, проходять CAPTCHA й підтверджують email. Ім’я, прізвище, email, пароль та підтвердження перевіряються на сервері й у формі. Пароль: 8–128 символів, велика/мала літера, цифра, спеціальний символ.
- Нові паролі — Argon2id. Старі PBKDF2 hashes підтримуються для сумісності та оновлюються при успішній перевірці пароля. Справжні паролі користувачів не змінювалися.
- JWT у localStorage замінено серверними сесіями та HttpOnly/SameSite cookies, POST/PATCH/DELETE захищено CSRF. Старі access/refresh вилучаються з браузерного сховища; `/api/auth/refresh/` вимкнено. При першому відкритті після оновлення потрібно увійти заново.
- Токени активації email одноразові й діють 24 години; reset tokens — 30 хвилин. У БД лише digests. Resend і forgot-password мають ліміти й не повідомляють про наявність адреси. Скидання пароля анулює попередні сеанси.
- П’ять невдалих паролів блокують пару email+IP на 15 хвилин; джерело має додатковий ліміт 40 спроб за 15 хвилин. Ручне блокування окреме й завершує активні сесії. Розблокування скидає автоматичні блокування користувача, але не глобальні source limits.
- TOTP: QR, підтвердження налаштування кодом, шифрування Fernet, захист від повтору використаного інтервалу, 10 одноразових резервних кодів із HMAC digests. До другого фактора немає повного доступу. Вимкнення вимагає повторного підтвердження особи.
- Google OIDC: Authlib, PKCE, state/nonce, JWT signature/issuer/audience/expiry. Прив’язування Google явне й потребує підтвердження особи; збіг email автоматично не зливає акаунти. Локальні блокування й 2FA діють після Google-входу.
- Окремий журнал безпеки з часом, IP, результатом і причиною, фільтрами та пагінацією. Старий аудит операцій із тесткейсами збережено. Дашборд безпеки показує справжні ORM-агрегати за 30 днів.
- Збережено ADMIN/MANAGER/TESTER і доступ тестувальників до призначених перевірок. Нові security/admin API доступні тільки ADMIN. MANAGER отримує окремий мінімальний список призначуваних тестувальників замість доступу до адміністративних даних усіх акаунтів.

## Сумісність із чинними користувачами

Три акаунти, що існували до міграції, збережено. Наявним користувачам надано статус підтвердження для продовження роботи — це міграційна сумісність, а не результат фактичного надсилання їм verification-листів. Усі нові публічні реєстрації створюються непідтвердженими. Проєкти, кейси, історію та ролі не видалено й не перейменовано.

Класичний Django admin URL прибрано з публічних маршрутів, щоб окремий password-only login не обходив TOTP. Використовуйте штатну адміністративну панель WebTestCase. Старі ідентифікатори API та enum values збережені для сумісності; їхні видимі назви перекладені українською.

## Маршрути

- UI: `/profile`, `/security`, `/security/overview`, `/security/users`, `/security/events`; керування ролями — `/admin/users`.
- API: `/api/auth/register/`, `login/`, `two-factor/`, `logout/`, `verify-email/`, `resend/`, `forgot-password/`, `reset-password/`, `oidc/start/`, `oidc/callback/`.
- Профіль: `/api/me/` і сумісний `/api/auth/me/`; `/api/profiles/<id>/` дозволяє читати/редагувати тільки власний профіль.
- Безпека: `/api/security/password/`, `/api/security/2fa/setup/`, `enable/`, `disable/`.
- Адміністратор: `/api/security/admin/users/`, `users/<id>/`, `events/`, `dashboard/`.

## Зовнішні налаштування

У `.env.example` — офіційні локальні dummy keys Cloudflare Turnstile. Використано visible test sitekey, який примусово показує інтерактивне завдання; серверний test secret приймає його dummy token через Siteverify. Це наочна локальна демонстрація, а не реальний антибот-захист. Backend справді звертається до Siteverify; потрібен Інтернет. У production тестові ключі заборонені, потрібні справжні hostname/action-обмеження. Mailpit приймає SMTP на 11025, вебінтерфейс — 18025. Для production потрібен ваш SMTP із TLS.

Для Google створіть Web application OAuth client, заповніть branding/consent screen та додайте тестового користувача, якщо Google Cloud працює у testing mode. У Cloud Console внесіть обидва callback: **`http://localhost:5173/api/auth/oidc/callback/`** і **`http://127.0.0.1:5173/api/auth/oidc/callback/`**. Вони мають точно збігатися, включно з final slash. Виконайте `scripts/configure-google-oidc.ps1`, який локально збереже `GOOGLE_CLIENT_ID` і `GOOGLE_CLIENT_SECRET` у `.env`, після чого перезапустіть backend. Без ключів кнопка чесно показує недоступність.

Production: DEBUG=false, випадковий SECRET_KEY, захищений ключ Fernet, HTTPS PUBLIC_BASE_URL, TLS reverse proxy, реальні CAPTCHA/SMTP. Cookies стають Secure. Якщо TLS завершується на зовнішньому proxy, який гарантує HTTPS і передає запити до локального nginx, установіть SECURE_SSL_REDIRECT=false в Django, щоб уникнути циклу redirect; HTTP→HTTPS тоді забезпечує зовнішній proxy. XFF довіряється лише адресам TRUSTED_PROXY_IPS; у Compose це конкретна frontend-IP. Не довіряйте всьому Інтернету.

## Підтверджені перевірки

Автоматизовані тести модуля безпеки проходять. Вони використовують окрему SQLite test database з наявного `config/test_settings.py`; runtime і живий сценарій використовують PostgreSQL. Тести перевіряють Cloudflare dummy Siteverify, SMTP/Mailpit, активацію, TOTP і резервний код, reset та анулювання сеансів, блокування/розблокування, аудит і RBAC. Для фактичної демонстрації зовнішніх інтеграцій потрібні запущений Mailpit і, для Google-входу, реальні OAuth-ключі.

Перевірено production frontend build і npm audit: 0 відомих уразливостей на дату перевірки. Docker Compose перевіряється командою `docker compose config --quiet`; запуск контейнерів і реальний Google-вхід залишаються окремою зовнішньою перевіркою. Це не сертифікація безпеки й не звіт penetration testing.

Мову widget CAPTCHA зафіксовано як uk згідно з [документацією Cloudflare](https://developers.cloudflare.com/turnstile/reference/supported-languages/), щоб вона не залежала від мови браузера.
