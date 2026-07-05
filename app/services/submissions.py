import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calculation import Calculation, NutritionGoal, WorkType
from app.models.client import Client, ClientStatus, Gender
from app.models.submission import Submission, SubmissionType
from app.services.calculator_extractor import extract as extract_calculator_inputs
from app.services.nutrition_calculator import calculate as run_calculator


def _coerce_gender(raw: Any) -> Gender | None:
    if not isinstance(raw, str):
        return None
    try:
        return Gender(raw.lower())
    except ValueError:
        return None


async def _find_or_create_client(
    session: AsyncSession, answers: dict[str, Any]
) -> Client:
    first = str(answers.get("firstname") or answers.get("firstName") or "").strip()
    last = str(answers.get("lastname") or answers.get("lastName") or "").strip()
    full_name = f"{first} {last}".strip() or "Anonymous"
    email = (answers.get("email") or None) and str(answers["email"]).strip().lower() or None
    phone = (answers.get("phone") or None) and str(answers["phone"]).strip() or None

    if email:
        existing = await session.scalar(
            select(Client).where(func.lower(Client.email) == email)
        )
        if existing is not None:
            return existing
    if phone:
        existing = await session.scalar(select(Client).where(Client.phone == phone))
        if existing is not None:
            return existing

    client = Client(
        full_name=full_name,
        email=email,
        phone=phone,
        gender=_coerce_gender(answers.get("gender")),
        status=ClientStatus.onboarding,
        source="landing",
    )
    session.add(client)
    await session.flush()
    return client


async def _maybe_create_calculation(
    session: AsyncSession,
    submission: Submission,
    client: Client,
    answers: dict[str, Any],
) -> uuid.UUID | None:
    inputs = extract_calculator_inputs(answers)
    if inputs is None:
        return None
    result = run_calculator(inputs)
    row = Calculation(
        submission_id=submission.id,
        client_id=client.id,
        weight_kg=inputs.weight,
        gender=Gender(inputs.gender),
        work_type=WorkType(inputs.work_type),
        goal=NutritionGoal(inputs.goal),
        training_types=[t.model_dump() for t in inputs.training_types],
        bmr=result.bmr,
        bmr_with_paf=result.bmr_with_paf,
        tee=result.tee,
        min_calories=result.min_calories,
        max_calories=result.max_calories,
    )
    session.add(row)
    await session.flush()
    return row.id


async def create_onboarding_submission(
    session: AsyncSession, answers: dict[str, str | list[str]]
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None]:
    client = await _find_or_create_client(session, answers)
    submission = Submission(
        client_id=client.id,
        type=SubmissionType.onboarding,
        payload=answers,
    )
    session.add(submission)
    await session.flush()
    calculation_id = await _maybe_create_calculation(
        session, submission, client, answers
    )
    await session.commit()
    return submission.id, client.id, calculation_id
