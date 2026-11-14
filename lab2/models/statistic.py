import numpy as np
from flask_restx import Namespace, Resource, fields
from data.data import disease_cases_data

api = Namespace("disease_cases_statistics", description="Статистика по заболевшим опасным заболеванием по странам")

CASE_STATISTIC_MODEL = api.model(
    "DiseaseCaseStatistic",
    {
        "min": fields.Float(required=True, description="Минимальное значение"),
        "max": fields.Float(required=True, description="Максимальное значение"),
        "mean": fields.Float(required=True, description="Среднее значение"),
        "median": fields.Float(description="Медианное значение"),
        "std_dev": fields.Float(description="Стандартное отклонение"),
        "count": fields.Integer(description="Количество элементов"),
    },
)

NUMERIC_FIELDS = [
    "infected_count",
    "recovered_count",
    "deaths_count",
    "active_cases",
    "critical_cases",
    "tests_count",
    "population",
]


def get_numeric_value(case, field):
    infected = case.get("infected_count", 0)
    population = case.get("population", 0)
    if field == "recovery_rate":
        return (case.get("recovered_count", 0) / infected * 100) if infected else 0
    if field == "mortality_rate":
        return (case.get("deaths_count", 0) / infected * 100) if infected else 0
    if field == "infection_rate_per_100k":
        return (infected / population * 100000) if population else 0
    return case.get(field)


def calculate_statistics(field):
    values = []
    for case in disease_cases_data:
        value = get_numeric_value(case, field)
        if value is not None:
            values.append(float(value))

    if not values:
        return {"error": f'Нет данных для поля "{field}"'}, 400

    arr = np.array(values, dtype=np.float64)
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std_dev": float(np.std(arr)),
        "count": len(arr),
    }


def create_stat_route(field_name):
    @api.route(f"/of/{field_name}")
    class StatOfField(Resource):
        @api.marshal_with(CASE_STATISTIC_MODEL, envelope="statistics")
        def get(self):
            return calculate_statistics(field_name)

    StatOfField.__name__ = f"StatOf_{field_name}"
    StatOfField.__qualname__ = f"StatOf_{field_name}"


for _field in NUMERIC_FIELDS + ["recovery_rate", "mortality_rate", "infection_rate_per_100k"]:
    create_stat_route(_field)


@api.route("/by/continent")
class StatisticsByContinent(Resource):
    def get(self):
        continents = {}
        for case in disease_cases_data:
            continent = case.get("continent")
            continents[continent] = continents.get(continent, 0) + 1
        return {"continents": continents, "total": len(disease_cases_data)}


@api.route("/by/quarantine")
class StatisticsByQuarantine(Resource):
    def get(self):
        levels = {}
        for case in disease_cases_data:
            level = case.get("quarantine_level")
            levels[level] = levels.get(level, 0) + 1
        return {"quarantine_levels": levels, "total": len(disease_cases_data)}


@api.route("/infected/by/continent")
class InfectedByContinent(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            continent = case.get("continent")
            result[continent] = result.get(continent, 0) + case.get("infected_count", 0)
        return result


@api.route("/recovered/by/continent")
class RecoveredByContinent(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            continent = case.get("continent")
            result[continent] = result.get(continent, 0) + case.get("recovered_count", 0)
        return result


@api.route("/deaths/by/continent")
class DeathsByContinent(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            continent = case.get("continent")
            result[continent] = result.get(continent, 0) + case.get("deaths_count", 0)
        return result


@api.route("/summary/by/country")
class SummaryByCountry(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            result[case.get("country")] = {
                "infected_count": case.get("infected_count", 0),
                "recovered_count": case.get("recovered_count", 0),
                "deaths_count": case.get("deaths_count", 0),
                "active_cases": case.get("active_cases", 0),
            }
        return result


@api.route("/rates/by/country")
class RatesByCountry(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            infected = case.get("infected_count", 0)
            population = case.get("population", 0)
            result[case.get("country")] = {
                "recovery_rate": round((case.get("recovered_count", 0) / infected * 100), 2) if infected else 0,
                "mortality_rate": round((case.get("deaths_count", 0) / infected * 100), 2) if infected else 0,
                "infection_rate_per_100k": round((infected / population * 100000), 2) if population else 0,
            }
        return result


@api.route("/emergency/summary")
class EmergencySummary(Resource):
    def get(self):
        emergency = len([case for case in disease_cases_data if case.get("is_emergency")])
        normal = len([case for case in disease_cases_data if not case.get("is_emergency")])
        return {"emergency": emergency, "normal": normal, "total": len(disease_cases_data)}


@api.route("/tests/by/continent")
class TestsByContinent(Resource):
    def get(self):
        result = {}
        for case in disease_cases_data:
            continent = case.get("continent")
            result[continent] = result.get(continent, 0) + case.get("tests_count", 0)
        return result
