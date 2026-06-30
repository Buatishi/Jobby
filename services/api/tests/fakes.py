from __future__ import annotations

from typing import Any


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeTableQuery:
    def __init__(self, supabase: FakeSupabase, table_name: str) -> None:
        self.supabase = supabase
        self.table_name = table_name
        self.filters: dict[str, Any] = {}
        self.update_payload: dict[str, Any] | None = None
        self.insert_payload: dict[str, Any] | None = None
        self.upsert_payload: dict[str, Any] | None = None
        self.should_delete = False
        self.single_row = False
        self.limit_count: int | None = None
        self.order_column: str | None = None
        self.order_desc = False

    def select(self, _columns: str) -> FakeTableQuery:
        return self

    def eq(self, column: str, value: Any) -> FakeTableQuery:
        self.filters[column] = value
        return self

    def single(self) -> FakeTableQuery:
        self.single_row = True
        return self

    def order(self, column: str, desc: bool = False) -> FakeTableQuery:
        self.order_column = column
        self.order_desc = desc
        return self

    def limit(self, count: int) -> FakeTableQuery:
        self.limit_count = count
        return self

    def update(self, payload: dict[str, Any]) -> FakeTableQuery:
        self.update_payload = payload
        return self

    def insert(self, payload: dict[str, Any]) -> FakeTableQuery:
        self.insert_payload = payload
        return self

    def upsert(self, payload: dict[str, Any]) -> FakeTableQuery:
        self.upsert_payload = payload
        return self

    def delete(self) -> FakeTableQuery:
        self.should_delete = True
        return self

    async def execute(self) -> FakeResponse:
        rows = self.supabase.tables[self.table_name]

        if self.insert_payload is not None:
            inserted = self.insert_payload.copy()
            inserted.setdefault("id", f"{self.table_name}-{len(rows) + 1}")
            rows.append(inserted)
            return FakeResponse([inserted.copy()])

        if self.upsert_payload is not None:
            upserted = self.upsert_payload.copy()
            upserted.setdefault("id", f"{self.table_name}-{len(rows) + 1}")
            rows.append(upserted)
            return FakeResponse([upserted.copy()])

        if self.should_delete:
            kept_rows = []
            deleted_rows = []
            for row in rows:
                if all(row.get(key) == value for key, value in self.filters.items()):
                    deleted_rows.append(row.copy())
                else:
                    kept_rows.append(row)
            self.supabase.tables[self.table_name] = kept_rows
            if self.table_name == "users":
                for deleted_row in deleted_rows:
                    self.supabase.cascade_delete_user(str(deleted_row.get("id")))
            return FakeResponse(deleted_rows)

        if self.update_payload is not None:
            updated_rows = []
            for row in rows:
                if all(row.get(key) == value for key, value in self.filters.items()):
                    row.update(self.update_payload)
                    updated_rows.append(row.copy())
            return FakeResponse(updated_rows)

        matching_rows = [
            row.copy()
            for row in rows
            if all(row.get(key) == value for key, value in self.filters.items())
        ]

        if self.order_column is not None:
            matching_rows.sort(
                key=lambda row: row.get(self.order_column) or "",
                reverse=self.order_desc,
            )

        if self.limit_count is not None:
            matching_rows = matching_rows[: self.limit_count]

        if self.single_row:
            return FakeResponse(matching_rows[0] if matching_rows else None)

        return FakeResponse(matching_rows)


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
                    "tier": "free",
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
            "uploaded_documents": [],
            "skills": [],
            "rejected_skills": [],
            "experiences": [],
            "educations": [],
            "languages": [],
            "certifications": [],
            "job_descriptions": [],
            "job_matches": [],
            "linkedin_scrape_cache": [],
            "interview_kits": [],
        }
        self.completeness = 21
        self.storage = FakeStorage()
        self.auth = FakeAuth()

    def table(self, table_name: str) -> FakeTableQuery:
        return FakeTableQuery(self, table_name)

    def rpc(self, function_name: str, _params: dict[str, Any]) -> FakeRpcQuery:
        if function_name == "set_primary_uploaded_document":
            user_id = _params["p_user_id"]
            document_id = _params["p_document_id"]
            selected_document = None
            for document in self.tables["uploaded_documents"]:
                if document.get("user_id") == user_id and document.get("type") == "cv":
                    document["is_primary"] = False
                if (
                    document.get("id") == document_id
                    and document.get("user_id") == user_id
                ):
                    selected_document = document
            if selected_document is not None:
                selected_document["is_primary"] = True
                selected_document["status"] = "pending"
                return FakeRpcQuery(selected_document.copy())
            return FakeRpcQuery(None)

        if function_name != "compute_completeness":
            return FakeRpcQuery(None)

        return FakeRpcQuery(self.completeness)

    def cascade_delete_user(self, user_id: str) -> None:
        profile_ids = {
            row["id"]
            for row in self.tables["master_profiles"]
            if row.get("user_id") == user_id
        }
        for table_name, rows in self.tables.items():
            if table_name == "users":
                continue
            self.tables[table_name] = [
                row
                for row in rows
                if row.get("user_id") != user_id
                and row.get("profile_id") not in profile_ids
            ]


class FakeAuthAdmin:
    def __init__(self) -> None:
        self.deleted_users: list[str] = []

    async def delete_user(self, supabase_uid: str) -> None:
        self.deleted_users.append(supabase_uid)


class FakeAuth:
    def __init__(self) -> None:
        self.admin = FakeAuthAdmin()


class FakeStorageBucket:
    def __init__(self, storage: FakeStorage) -> None:
        self.storage = storage

    async def download(self, storage_path: str) -> bytes:
        return self.storage.files[storage_path]

    async def list(self, path: str) -> list[dict[str, Any]]:
        prefix = f"{path.strip('/')}/"
        names: set[str] = set()
        for storage_path in self.storage.files:
            if not storage_path.startswith(prefix):
                continue
            remainder = storage_path.removeprefix(prefix)
            first_segment = remainder.split("/", 1)[0]
            names.add(first_segment)
        return [
            {
                "name": name,
                "metadata": {} if "." in name else None,
            }
            for name in sorted(names)
        ]

    async def remove(self, storage_paths: list[str]) -> list[dict[str, str]]:
        removed = []
        for storage_path in storage_paths:
            if storage_path in self.storage.files:
                self.storage.files.pop(storage_path)
                removed.append({"name": storage_path})
        return removed


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def from_(self, _bucket: str) -> FakeStorageBucket:
        return FakeStorageBucket(self)
