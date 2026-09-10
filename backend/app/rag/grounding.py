# Creado por Aldo Garcia.
"""Verificador de grounding y allowlist de fuentes.

Dos garantias que este modulo hace cumplir:

1. **Toda cita debe existir.** Si el modelo cita un ``source_id`` que no estaba
   entre la evidencia recuperada, la sintesis se rechaza. Un source ID inventado
   es indistinguible para el usuario de uno real, y es la forma mas peligrosa de
   alucinacion en un asistente de politicas de RH.
2. **La memoria no es evidencia.** El resumen de la conversacion entra al prompt
   como contexto, nunca como respaldo factual de una politica.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.common.logging import get_logger
from app.rag.schemas import Evidence

logger = get_logger(__name__)

#: Formato de cita esperado en la respuesta del modelo: [[categoria/archivo#n]]
CITATION_RE = re.compile(r"\[\[([^\]]{1,240})\]\]")

#: Frases con las que el asistente reconoce que no tiene respaldo. Si aparecen,
#: la ausencia de citas es correcta y no debe tratarse como fallo de grounding.
_INSUFFICIENCY_MARKERS = (
    "no cuento con informacion",
    "no cuento con información",
    "no tengo informacion",
    "no tengo información",
    "no hay evidencia",
    "evidencia insuficiente",
    "evidencia es insuficiente",
    "informacion insuficiente",
    "información insuficiente",
    "no dispongo de documentos",
    "no encontre informacion",
    "no encontré información",
    "no tiene acceso",
    "fuera del alcance",
)


@dataclass(frozen=True, slots=True)
class GroundingReport:
    """Contrato de citas y fidelidad extractiva, no una prueba de verdad.

    ``grounded`` acredita este contrato limitado. ``extractive_verified`` exige
    unidades recuperadas completas; ``factual_verified`` se reserva para una
    verificacion semantica independiente que este modulo NO implementa.
    """

    grounded: bool
    cited_source_ids: tuple[str, ...] = field(default_factory=tuple)
    invalid_source_ids: tuple[str, ...] = field(default_factory=tuple)
    declares_insufficiency: bool = False
    reason: str = ""
    citations_valid: bool = False
    factual_verified: bool = False
    extractive_verified: bool = False

    @property
    def has_invalid_citations(self) -> bool:
        return bool(self.invalid_source_ids)


def extract_citations(answer: str) -> tuple[str, ...]:
    """Extrae los source IDs citados en el texto."""
    return tuple(dict.fromkeys(m.group(1).strip() for m in CITATION_RE.finditer(answer)))


def declares_insufficiency(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in _INSUFFICIENCY_MARKERS)


def _normalized_extract(value: str) -> str:
    """Tolera espacios y punto final, nunca signos numericos ni conectores.

    Se conserva la puntuacion interna, incluidas cifras decimales. No se usa
    una busqueda de substrings: la unidad es el Evidence completo, incluso si
    contiene varios parrafos o una excepcion en la ultima linea.
    """
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    # Un guion al inicio puede ser un signo, y un punto inicial puede iniciar
    # un decimal (.5). No tratarlos como bullets o puntuacion decorativa.
    return " ".join(value.split()).removesuffix(".").rstrip()


def _structured_extracts(result) -> tuple[str, ...]:
    """Filas completas con encabezados: una cifra aislada pierde su significado."""
    variants = [result.as_markdown_table()]
    header = "| " + " | ".join(result.columns) + " |"
    separator = "| " + " | ".join("---" for _ in result.columns) + " |"
    # Coincide con la ventana visible de StructuredEvidence.as_markdown_table.
    for row in result.rows[:25]:
        values = ["" if value is None else str(value) for value in row]
        variants.append("\n".join((header, separator, "| " + " | ".join(values) + " |")))
        variants.append(" | ".join(f"{column}: {value}" for column, value in zip(result.columns, values, strict=True)))
    return tuple(variants)


def verify_grounding(
    answer: str,
    evidences: tuple[Evidence, ...],
    *,
    require_citation: bool = True,
    structured: tuple = (),
) -> GroundingReport:
    """Valida citas y unidades completas sin atribuirles verificacion semantica."""
    sources = {e.source_id: e.text for e in evidences}
    sources.update({e.source_id: e.as_markdown_table() for e in structured})
    supported_units = {e.source_id: (_normalized_extract(e.text),) for e in evidences}
    supported_units.update({
        e.source_id: tuple(_normalized_extract(text) for text in _structured_extracts(e)) for e in structured
    })
    # Un mismo identificador no puede acreditar dos documentos diferentes.
    raw_sources = [(e.source_id, e.text) for e in evidences]
    raw_sources.extend((e.source_id, e.as_markdown_table()) for e in structured)
    ambiguous = {sid for sid, text in raw_sources if sources[sid] != text}
    allowlist = set(sources)
    cited = extract_citations(answer)
    invalid = tuple(sid for sid in cited if sid not in allowlist)
    insufficiency = declares_insufficiency(answer)

    if invalid:
        logger.warning(
            "rag.grounding.invalid_citation",
            extra={"invalid_count": len(invalid), "allowlist_size": len(allowlist)},
        )
        return GroundingReport(
            grounded=False,
            cited_source_ids=cited,
            invalid_source_ids=invalid,
            declares_insufficiency=insufficiency,
            reason="citas fuera de la evidencia recuperada",
        )

    if set(cited).intersection(ambiguous):
        return GroundingReport(
            grounded=False, cited_source_ids=cited,
            reason="identificador de fuente ambiguo entre evidencias diferentes",
        )

    # Un marcador dentro de una afirmacion no acredita una abstencion.
    from app.agents.prompts import DENIED_ANSWER, INSUFFICIENT_ANSWER

    safe_refusals = {
        DENIED_ANSWER,
        INSUFFICIENT_ANSWER,
        "No cuento con informacion documental suficiente.",
        "No tiene acceso a esa informacion.",
    }
    if answer.strip() in safe_refusals:
        # Respuestas de abstencion completas y controladas.
        return GroundingReport(
            grounded=True,
            cited_source_ids=cited,
            declares_insufficiency=True,
            reason="declara insuficiencia de evidencia",
        )

    if require_citation and sources and not cited:
        return GroundingReport(
            grounded=False,
            cited_source_ids=(),
            declares_insufficiency=False,
            reason="respuesta documental sin ninguna cita",
        )

    if require_citation and not sources:
        # Sin evidencia, la unica respuesta admisible es declarar insuficiencia.
        return GroundingReport(
            grounded=False,
            cited_source_ids=cited,
            declares_insufficiency=False,
            reason="respuesta afirmativa sin evidencia disponible",
        )

    if require_citation:
        # Cifras solo contra las fuentes citadas, no contra todo el corpus.
        cited_text = " ".join(sources[sid] for sid in cited)
        content = CITATION_RE.sub("", answer)
        numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?", content))
        known_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?%?", cited_text))
        if not numbers.issubset(known_numbers):
            return GroundingReport(
                grounded=False,
                cited_source_ids=cited,
                citations_valid=True,
                reason="afirmacion numerica sin respaldo",
            )

        cursor = 0
        previous_claim = ""
        for match in CITATION_RE.finditer(answer):
            fragment = answer[cursor : match.start()]
            if cursor:
                # El punto tras una cita cierra la unidad anterior. Solo se
                # retira cuando esta separado del nuevo texto por espacios:
                # nunca quitar el punto de un decimal como .5.
                fragment = re.sub(r"^\s*\.\s+", "", fragment, count=1)
            claim = _normalized_extract(fragment)
            if not claim:
                claim = previous_claim
            sid = match.group(1).strip()
            if not claim or claim not in supported_units[sid]:
                return GroundingReport(
                    grounded=False,
                    cited_source_ids=cited,
                    citations_valid=True,
                    reason="requiere una unidad de evidencia completa; no se acredita una frase parcial",
                )
            previous_claim = claim
            cursor = match.end()
        if _normalized_extract(answer[cursor:]):
            return GroundingReport(
                grounded=False, cited_source_ids=cited, citations_valid=True, reason="afirmacion final sin cita"
            )
        return GroundingReport(
            grounded=True,
            cited_source_ids=cited,
            reason="fidelidad extractiva de unidades completas; veracidad semantica no evaluada",
            citations_valid=True,
            extractive_verified=True,
        )
    return GroundingReport(grounded=True, cited_source_ids=cited, reason="sin contrato factual")


def filter_answer_citations(answer: str, evidences: tuple[Evidence, ...]) -> str:
    """Elimina del texto las citas invalidas como ultima red de seguridad.

    Se usa solo cuando ya se decidio devolver una respuesta degradada: la ruta
    normal ante citas invalidas es regenerar o declarar insuficiencia.
    """
    allowlist = {e.source_id for e in evidences}

    def _replace(match: re.Match[str]) -> str:
        source_id = match.group(1).strip()
        return match.group(0) if source_id in allowlist else ""

    return CITATION_RE.sub(_replace, answer).strip()


def coverage_ratio(answer: str, evidences: tuple[Evidence, ...]) -> float:
    """Fraccion de la evidencia recuperada que la respuesta llega a citar.

    Una cobertura muy baja con evidencia abundante sugiere que la ruta rapida
    ignoro parte del material: es una de las senales que activan la ruta profunda.
    """
    if not evidences:
        return 0.0
    cited = set(extract_citations(answer))
    return len(cited & {e.source_id for e in evidences}) / len(evidences)
