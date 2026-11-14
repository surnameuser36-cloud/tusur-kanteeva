from flask_restx import Namespace, Resource, fields
from data.data import disease_cases_data

api = Namespace("disease_cases_catalog", description="Каталог заболевших опасным заболеванием по странам")

CASE_MODEL = api.model(
    "DiseaseCase",
    {
        "id": fields.Integer(required=True, description="ID записи"),
        "country": fields.String(required=True, description="Страна"),
        "continent": fields.String(required=True, description="Континент"),
        "disease_name": fields.String(required=True, description="Название заболевания"),
        "record_date": fields.String(required=True, description="Дата записи"),
        "infected_count": fields.Integer(required=True, description="Количество заболевших"),
        "recovered_count": fields.Integer(required=True, description="Количество выздоровевших"),
        "deaths_count": fields.Integer(required=True, description="Количество погибших"),
        "active_cases": fields.Integer(required=True, description="Количество активных случаев"),
        "critical_cases": fields.Integer(required=True, description="Количество тяжёлых случаев"),
        "tests_count": fields.Integer(required=True, description="Количество тестов"),
        "population": fields.Integer(required=True, description="Численность населения"),
        "quarantine_level": fields.String(required=True, description="Уровень карантина"),
        "is_emergency": fields.Boolean(required=True, description="Режим ЧС"),
        "description": fields.String(required=True, description="Описание"),
    },
)

COUNTS_EDIT_MODEL = api.model(
    "DiseaseCountsEdit",
    {
        "id": fields.Integer(required=True, description="ID записи"),
        "infected_count": fields.Integer(required=True, description="Количество заболевших"),
        "active_cases": fields.Integer(required=True, description="Количество активных случаев"),
        "critical_cases": fields.Integer(required=True, description="Количество тяжёлых случаев"),
    },
)

RECOVERED_EDIT_MODEL = api.model(
    "DiseaseRecoveredEdit",
    {
        "id": fields.Integer(required=True, description="ID записи"),
        "recovered_count": fields.Integer(required=True, description="Количество выздоровевших"),
    },
)

DEATHS_EDIT_MODEL = api.model(
    "DiseaseDeathsEdit",
    {
        "id": fields.Integer(required=True, description="ID записи"),
        "deaths_count": fields.Integer(required=True, description="Количество погибших"),
    },
)

QUARANTINE_EDIT_MODEL = api.model(
    "DiseaseQuarantineEdit",
    {
        "id": fields.Integer(required=True, description="ID записи"),
        "quarantine_level": fields.String(required=True, description="Уровень карантина"),
        "is_emergency": fields.Boolean(required=True, description="Режим ЧС"),
    },
)

CASE_PATCH_MODEL = api.model(
    "DiseaseCasePatch",
    {
        "country": fields.String(description="Страна"),
        "continent": fields.String(description="Континент"),
        "disease_name": fields.String(description="Название заболевания"),
        "record_date": fields.String(description="Дата записи"),
        "infected_count": fields.Integer(description="Количество заболевших"),
        "recovered_count": fields.Integer(description="Количество выздоровевших"),
        "deaths_count": fields.Integer(description="Количество погибших"),
        "active_cases": fields.Integer(description="Количество активных случаев"),
        "critical_cases": fields.Integer(description="Количество тяжёлых случаев"),
        "tests_count": fields.Integer(description="Количество тестов"),
        "population": fields.Integer(description="Численность населения"),
        "quarantine_level": fields.String(description="Уровень карантина"),
        "is_emergency": fields.Boolean(description="Режим ЧС"),
        "description": fields.String(description="Описание"),
    },
)

SORTABLE_FIELDS = [
    "infected_count",
    "recovered_count",
    "deaths_count",
    "active_cases",
    "critical_cases",
    "tests_count",
    "population",
]


def get_next_id():
    return max([case["id"] for case in disease_cases_data], default=0) + 1


def find_case_by_id(case_id):
    return next((case for case in disease_cases_data if case["id"] == case_id), None)


@api.route("/list/all")
class CasesList(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self):
        return disease_cases_data


@api.route("/list/all/sortBy/<string:field_name>")
class CasesListSorted(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, field_name):
        if field_name not in SORTABLE_FIELDS:
            api.abort(400, f"Поле {field_name} недоступно для сортировки")
        return sorted(disease_cases_data, key=lambda item: item.get(field_name, 0))


@api.route("/case/getBy/id/<int:case_id>")
class CaseGetById(Resource):
    @api.marshal_with(CASE_MODEL, envelope="case")
    def get(self, case_id):
        case = find_case_by_id(case_id)
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        return case


@api.route("/case/deleteBy/id/<int:case_id>")
class CaseDeleteById(Resource):
    def delete(self, case_id):
        case = find_case_by_id(case_id)
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        disease_cases_data.remove(case)
        return {"message": f"Запись ID={case_id} удалена"}


@api.route("/case/deleteBy/country/<string:country>")
class CaseDeleteByCountry(Resource):
    def delete(self, country):
        found = [case for case in disease_cases_data if country.lower() == case.get("country", "").lower()]
        if not found:
            api.abort(404, "Записи по указанной стране не найдены")
        for case in found:
            disease_cases_data.remove(case)
        return {"message": f"Удалено записей: {len(found)}"}


@api.route("/case/deleteBy/continent/<string:continent>")
class CaseDeleteByContinent(Resource):
    def delete(self, continent):
        found = [case for case in disease_cases_data if continent.lower() == case.get("continent", "").lower()]
        if not found:
            api.abort(404, "Записи по указанному континенту не найдены")
        for case in found:
            disease_cases_data.remove(case)
        return {"message": f"Удалено записей по континенту {continent}: {len(found)}"}


@api.route("/case/add")
class CaseAdd(Resource):
    @api.expect(CASE_MODEL)
    @api.marshal_with(CASE_MODEL, code=201, envelope="case")
    def post(self):
        data = dict(api.payload)
        data["id"] = get_next_id()
        disease_cases_data.append(data)
        return data, 201


@api.route("/case/update")
class CaseUpdate(Resource):
    @api.expect(CASE_MODEL)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def put(self):
        case_id = api.payload.get("id")
        case = find_case_by_id(case_id)
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        case.clear()
        case.update(api.payload)
        return case


@api.route("/case/patch/<int:case_id>")
class CasePatch(Resource):
    @api.expect(CASE_PATCH_MODEL, validate=True)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def patch(self, case_id):
        """Частично обновить только переданные поля записи."""
        case = find_case_by_id(case_id)
        if not case:
            api.abort(404, "Запись с таким ID не найдена")

        changes = dict(api.payload or {})
        if not changes:
            api.abort(400, "Передайте хотя бы одно поле для обновления")

        for field_name, value in changes.items():
            case[field_name] = value
        return case


@api.route("/case/editBy/id/counts")
class CaseEditCounts(Resource):
    @api.expect(COUNTS_EDIT_MODEL)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def patch(self):
        case = find_case_by_id(api.payload["id"])
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        case["infected_count"] = api.payload["infected_count"]
        case["active_cases"] = api.payload["active_cases"]
        case["critical_cases"] = api.payload["critical_cases"]
        return case


@api.route("/case/editBy/id/recovered")
class CaseEditRecovered(Resource):
    @api.expect(RECOVERED_EDIT_MODEL)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def patch(self):
        case = find_case_by_id(api.payload["id"])
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        case["recovered_count"] = api.payload["recovered_count"]
        return case


@api.route("/case/editBy/id/deaths")
class CaseEditDeaths(Resource):
    @api.expect(DEATHS_EDIT_MODEL)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def patch(self):
        case = find_case_by_id(api.payload["id"])
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        case["deaths_count"] = api.payload["deaths_count"]
        return case


@api.route("/case/editBy/id/quarantine")
class CaseEditQuarantine(Resource):
    @api.expect(QUARANTINE_EDIT_MODEL)
    @api.marshal_with(CASE_MODEL, envelope="case")
    def patch(self):
        case = find_case_by_id(api.payload["id"])
        if not case:
            api.abort(404, "Запись с таким ID не найдена")
        case["quarantine_level"] = api.payload["quarantine_level"]
        case["is_emergency"] = api.payload["is_emergency"]
        return case


@api.route("/list/country/<string:country>")
class CasesByCountry(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, country):
        result = [case for case in disease_cases_data if country.lower() in case.get("country", "").lower()]
        if not result:
            api.abort(404, "Записи по указанной стране не найдены")
        return result


@api.route("/list/continent/<string:continent>")
class CasesByContinent(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, continent):
        result = [case for case in disease_cases_data if continent.lower() in case.get("continent", "").lower()]
        if not result:
            api.abort(404, "Записи по указанному континенту не найдены")
        return result


@api.route("/list/disease/<string:disease_name>")
class CasesByDisease(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, disease_name):
        result = [case for case in disease_cases_data if disease_name.lower() in case.get("disease_name", "").lower()]
        if not result:
            api.abort(404, "Записи по указанному заболеванию не найдены")
        return result


@api.route("/list/quarantine/<string:quarantine_level>")
class CasesByQuarantine(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, quarantine_level):
        result = [case for case in disease_cases_data if quarantine_level.lower() in case.get("quarantine_level", "").lower()]
        if not result:
            api.abort(404, "Записи с указанным уровнем карантина не найдены")
        return result


@api.route("/list/emergency")
class CasesEmergency(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self):
        return [case for case in disease_cases_data if case.get("is_emergency")]


@api.route("/list/high_active_cases/<int:min_cases>")
class CasesHighActive(Resource):
    @api.marshal_list_with(CASE_MODEL, envelope="cases")
    def get(self, min_cases):
        return [case for case in disease_cases_data if case.get("active_cases", 0) >= min_cases]
