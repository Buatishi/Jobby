from typing import Any


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeTableQuery:
    def __init__(self, supabase: "FakeSupabase", table_name: str) -> None:
        self.supabase = supabase
        self.table_name = table_name
        self.filters: dict[str, Any] = {}
        self.update_payload: dict[str, Any] | None = None

    def select(self, _columns: str) -> "FakeTableQuery":
        return self

    def eq(self, column: str, value: Any) -> "FakeTableQuery":
        self.filters[column] = value
        return self

    def single(self) -> "FakeTableQuery":
        return self

    def update(self, payload: dict[str, Any]) -> "FakeTableQuery":
        self.update_payload = payload
        return self

    async def execute(self) -> FakeResponse:
        rows = self.supabase.tables[self.table_name]

        if self.update_payload is not None:
            updated_rows = []
            for row in rows:
                if all(row.get(key) == value for key, value in self.filters.items()):
                    row.update(self.update_payload)
                    updated_rows.append(row.copy())
            return FakeResponse(updated_rows)

        for row in rows:
            if all(row.get(key) == value for key, value in self.filters.items()):
                return FakeResponse(row.copy())

        return FakeResponse(None)


class FakeRpcQuery:
    def __init__(self, data: Any) -> None:
        self.data = data

    async def execute(self) -> FakeResponse:
        return FakeResponse(self.data)


class FakeSupabase:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "users": [
                {
                    "id": "user-1",
                    "supabase_uid": "auth-user-1",
                    "email": "person@example.com",
                }
            ],
            "master_profiles": [
                {
                    "id": "profile-1",
                    "user_id": "user-1",
                    "headline": "Backend Engineer",
                    "summary": None,
                    "target_role": None,
                    "target_seniority": None,
                    "work_modality": None,
                    "target_industry": [],
                    "linkedin_url": None,
                    "completeness_pct": 8,
                    "inferred_soft_skills": [],
                    "soft_skills_computed_at": None,
                    "created_at": None,
                    "updated_at": None,
                }
            ],
        }
        self.completeness = 21

    def table(self, table_name: str) -> FakeTableQuery:
        return FakeTableQuery(self, table_name)

    def rpc(self, function_name: str, _params: dict[str, Any]) -> FakeRpcQuery:
        if function_name != "compute_completeness":
            return FakeRpcQuery(None)

        return FakeRpcQuery(self.completeness)
