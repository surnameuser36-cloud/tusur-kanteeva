import hashlib
import os
import re
import uuid
from datetime import date

from flask import Flask, request
from flask_restx import Api, Namespace, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix

from models.cases import api as cases_api
from models.statistic import api as stats_api

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config["RESTX_MASK_SWAGGER"] = False

VERIFY_TOKEN = "TUSUR-KANTEEVA-20261110-AEADDC34"
VERIFY_DATE = "2026-11-08"

api = Api(
    app=app,
    version="1.0",
    title="Disease Cases by Country API",
    description="REST API для каталога заболевших опасным заболеванием по странам с CRUD операциями и статистикой",
    doc="/",
)

api.add_namespace(cases_api)
api.add_namespace(stats_api)

disease_api = Namespace(
    "disease",
    path="/api/disease",
    description="Проверочный ресурс заболеваний",
)

DISEASE_MODEL = disease_api.model(
    "VerificationDisease",
    {
        "country": fields.String(required=True, description="Страна"),
        "disease": fields.String(required=True, description="Проверочный токен"),
        "date": fields.String(required=True, description="Дата в формате YYYY-MM-DD"),
        "sick": fields.Integer(required=True, description="Количество заболевших"),
        "recovered": fields.Integer(required=True, description="Количество выздоровевших"),
        "deaths": fields.Integer(required=True, description="Количество умерших"),
    },
)

DISEASE_DATA = []


def normalize_text(text):
    """Нормализует фактическое тело ответа перед расчётом SHA-256."""
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    lines = [re.sub(r"\s+", " ", line) for line in lines]
    return "\n".join(lines)


@disease_api.route("/")
class DiseaseCollection(Resource):
    @disease_api.expect(DISEASE_MODEL, validate=True)
    def post(self):
        """Создать проверочную запись с персональным токеном."""
        payload = dict(disease_api.payload)
        if payload.get("disease") != VERIFY_TOKEN:
            disease_api.abort(400, "Поле disease должно содержать проверочный токен")
        if payload.get("date") != VERIFY_DATE:
            disease_api.abort(400, f"Дата должна быть равна {VERIFY_DATE}")

        record = {
            "id": uuid.uuid4().hex[:8],
            "country": payload["country"],
            "disease": payload["disease"],
            "date": payload["date"],
            "sick": payload["sick"],
            "recovered": payload["recovered"],
            "deaths": payload["deaths"],
        }
        DISEASE_DATA.append(record)
        return record, 201

    def get(self):
        """Получить последнюю созданную проверочную запись."""
        if not DISEASE_DATA:
            disease_api.abort(404, "Проверочная запись ещё не создана")
        return DISEASE_DATA[-1]


@disease_api.route("/<string:record_id>")
class DiseaseById(Resource):
    def get(self, record_id):
        """Получить проверочную запись по идентификатору."""
        record = next((item for item in DISEASE_DATA if item["id"] == record_id), None)
        if not record:
            disease_api.abort(404, "Проверочная запись не найдена")
        return record


api.add_namespace(disease_api)


@app.after_request
def add_verify_hash(response):
    """Добавляет SHA-256 для успешного GET проверочного ресурса."""
    is_disease_get = request.method == "GET" and re.match(
        r"^/api/disease/(?:[^/]+)?$", request.path
    )
    if is_disease_get and response.status_code == 200:
        body = response.get_data(as_text=True)
        normalized = normalize_text(body)
        response.headers["X-Verify-Hash"] = hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()
    return response


@app.get("/health")
def health():
    """Возвращает состояние сервиса для проверки Render."""
    return {"status": "ok", "date": date.today().isoformat()}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
