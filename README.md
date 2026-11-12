# Orders API Testing Lab

Self-contained FastAPI + SQLite service for practicing **manual API testing, HTTP status codes, test data isolation, SQL validation, Postman and pytest**. Designed for junior QA roles; no external database or paid cloud services needed.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for Swagger UI and submit requests manually. Run `pytest -v` from a second terminal. Use the Postman collection in `postman/` with `baseUrl=http://127.0.0.1:8000`. Tests create temporary, isolated SQLite databases.

## Endpoints and expected behavior

| Method | Endpoint | Success | Negative tests |
|---|---|---|---|
| GET | `/health` | 200 | — |
| POST | `/orders` | 201 | 400 unknown SKU; 422 invalid input |
| GET | `/orders` | 200 | 400 unknown status |
| GET | `/orders/{id}` | 200 | 404 unknown ID |
| PATCH | `/orders/{id}/status` | 200 | 404 ID; 400 status; 409 transition |

Allowed status flow: `pending → packed → shipped`; `pending → cancelled`; `packed → cancelled`. The amounts are fictional and fixed server-side to keep tests deterministic.

## Why it is useful for QA interviews

- Illustrates positive, negative, boundary and state-transition tests.
- Uses 200, 201, 400, 404, 409 and 422 responses meaningfully.
- Verifies API data against a real SQLite table, not just mocked JSON.
- Contains Postman requests with test assertions and a CI workflow.

## Public demo limitations

GitHub Pages publishes only the `docs/` information page. **It does not host Python/FastAPI**. Hosting a real API requires a separate backend service; don't imply this project has a live API until one is deployed and verified.

## Practice tasks to complete personally

1. Write a test for an unsupported SKU and explain why it returns 400 rather than 422.
2. Add a SQL query to count orders grouped by status.
3. Design a test case that attempts to cancel a shipped order.
4. Capture an actual pytest report and document a bug only if you discover one.
