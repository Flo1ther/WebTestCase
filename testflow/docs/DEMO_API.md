# Local demo API

`/api/demo-store/` is a local, deliberately small shop API used only to demonstrate the API-test runner.

* `GET /api/demo-store/health/` returns a health JSON document.
* `POST /api/demo-store/checkout/` requires a non-empty `items` array.
* **DEMO-API-01** is intentional: any non-empty `payment_token`, including an invalid value, produces `201` with `status: paid`.

Create an API test that expects `400` for an invalid token. The runner receives a real `201`, marks the assertion failed and stores the response. This is a reproducible example of an automated test detecting a defect; the language model does not determine the result.
