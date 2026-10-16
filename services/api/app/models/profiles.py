from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Topes de largo contra abuso, no de forma: ningún CV real se acerca. Las tablas guardan
# TEXT sin límite y estos textos terminan en los prompts de IA, así que esta es la única
# barrera. Las skills que extrae la IA del CV pasan por `SkillCreate` y
# `RejectedSkillCreate` desde el paso 3 del asistente: por eso van holgados.
NAME_MAX_LENGTH = 200  # empresa, cargo, institución, idioma, skill (como `headline`)
LABEL_MAX_LENGTH = 100  # categoría, nivel, fuente
NOTE_MAX_LENGTH = 500  # motivo de un rechazo
LONG_TEXT_MAX_LENGTH = 5_000  # descripción de una experiencia (como `summary`)
ACHIEVEMENT_MAX_LENGTH = 1_000
ACHIEVEMENTS_MAX_ITEMS = 50
STORAGE_PATH_MAX_LENGTH = 1_024  # el máximo de nombre de objeto de Supabase Storage
FILENAME_MAX_LENGTH = 512  # los sistemas de archivos llegan a 255

Name = Annotated[str, StringConstraints(max_length=NAME_MAX_LENGTH)]
Achievement = Annotated[str, StringConstraints(max_length=ACHIEVEMENT_MAX_LENGTH)]


class MasterProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    headline: str | None = None
    summary: str | None = None
    target_role: str | None = None
    target_seniority: str | None = None
    work_modality: str | None = None
    target_industry: list[str] | None = None
    linkedin_url: str | None = None
    completeness_pct: int = 0
    inferred_soft_skills: list[str] = Field(default_factory=list)
    soft_skills_computed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MasterProfileUpdate(BaseModel):
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    target_role: str | None = Field(default=None, max_length=200)
    target_seniority: str | None = Field(default=None, max_length=100)
    work_modality: str | None = Field(default=None, max_length=100)
    target_industry: list[Name] | None = Field(default=None, max_length=20)
    linkedin_url: str | None = Field(default=None, max_length=2048)

    def to_update_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class UploadedDocumentCreate(BaseModel):
    profile_id: str = Field(max_length=64)
    type: str = Field(max_length=32)
    storage_path: str = Field(max_length=STORAGE_PATH_MAX_LENGTH)
    cv_slot: int | None = None
    is_primary: bool = False
    original_filename: str | None = Field(default=None, max_length=FILENAME_MAX_LENGTH)
    mime_type: str | None = Field(default=None, max_length=255)
    file_size: int | None = None


class UploadedDocument(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    user_id: str
    profile_id: str
    type: str
    cv_slot: int | None = None
    is_primary: bool = False
    storage_path: str
    original_filename: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    status: str = "pending"
    parsed_data: dict[str, Any] | None = None
    error_msg: str | None = None
    task_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SkillCreate(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    category: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)
    level: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)
    in_cv: bool = False
    confirmed: bool = False


class RejectedSkillCreate(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    source: str = Field(default="manual", max_length=LABEL_MAX_LENGTH)
    reason: str | None = Field(default=None, max_length=NOTE_MAX_LENGTH)


class ExperienceCreate(BaseModel):
    company: str = Field(max_length=NAME_MAX_LENGTH)
    title: str = Field(max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=LONG_TEXT_MAX_LENGTH)
    achievements: list[Achievement] = Field(
        default_factory=list, max_length=ACHIEVEMENTS_MAX_ITEMS
    )


class EducationCreate(BaseModel):
    institution: str = Field(max_length=NAME_MAX_LENGTH)
    field_of_study: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    degree_level: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)


class LanguageCreate(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    level: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)


class PrintableCVContact(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""


class PrintableCVExperience(BaseModel):
    company: str = ""
    title: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    is_current: bool = False
    description: str | None = None
    achievements: list[str] = Field(default_factory=list)


class PrintableCVEducation(BaseModel):
    institution: str = ""
    field_of_study: str | None = None
    degree_level: str | None = None


class PrintableCVLanguage(BaseModel):
    name: str = ""
    level: str | None = None


class PrintableCVCertification(BaseModel):
    name: str = ""
    issuer: str | None = None


class PrintableCV(BaseModel):
    contact: PrintableCVContact
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experiences: list[PrintableCVExperience] = Field(default_factory=list)
    educations: list[PrintableCVEducation] = Field(default_factory=list)
    languages: list[PrintableCVLanguage] = Field(default_factory=list)
    certifications: list[PrintableCVCertification] = Field(default_factory=list)


class ExperienceUpdate(BaseModel):
    """Cambio parcial: solo se tocan los campos que llegan en el cuerpo."""

    company: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    title: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=LONG_TEXT_MAX_LENGTH)
    achievements: list[Achievement] | None = Field(
        default=None, max_length=ACHIEVEMENTS_MAX_ITEMS
    )

    def to_update_payload(self) -> dict[str, Any]:
        # company y title son NOT NULL: un null explícito no los vacía.
        changes = self.model_dump(exclude_unset=True)
        for column in ("company", "title"):
            if changes.get(column, "") is None:
                del changes[column]
        return changes


class EducationUpdate(BaseModel):
    institution: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    field_of_study: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    degree_level: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)

    def to_update_payload(self) -> dict[str, Any]:
        changes = self.model_dump(exclude_unset=True)
        if changes.get("institution", "") is None:
            del changes["institution"]
        return changes


class LanguageUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    level: str | None = Field(default=None, max_length=LABEL_MAX_LENGTH)

    def to_update_payload(self) -> dict[str, Any]:
        """Con las columnas de la tabla: el nivel se guarda en `proficiency`."""
        changes = self.model_dump(exclude_unset=True)
        if changes.get("name", "") is None:
            del changes["name"]
        if "level" in changes:
            changes["proficiency"] = changes.pop("level")
        return changes


class ProfileExperienceItem(BaseModel):
    id: str
    company: str = ""
    title: str = ""
    description: str | None = None


class ProfileEducationItem(BaseModel):
    id: str
    institution: str = ""
    field_of_study: str | None = None
    degree_level: str | None = None


class ProfileLanguageItem(BaseModel):
    id: str
    name: str = ""
    level: str | None = None


class ProfileDetails(BaseModel):
    """Lo que la persona ya cargó a mano, de la más nueva a la más vieja."""

    experiences: list[ProfileExperienceItem] = Field(default_factory=list)
    educations: list[ProfileEducationItem] = Field(default_factory=list)
    languages: list[ProfileLanguageItem] = Field(default_factory=list)
