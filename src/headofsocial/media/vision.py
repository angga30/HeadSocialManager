"""Vision-based reference analysis for media fidelity (M4).

The Media Generation Agent calls this to derive a structured identity description from a
real brand reference photo (face / logo / product) before generating media, so the
generation prompt carries explicit fidelity cues — not just the asset's textual `label`.
"""

import base64
import json
import logging
from pathlib import Path

from headofsocial.domain.enums import BrandAssetKind
from headofsocial.llm.models import role_model_string

logger = logging.getLogger(__name__)

_SUBJECT_BY_KIND = {
    BrandAssetKind.FACE_PHOTO.value: "person",
    BrandAssetKind.LOGO.value: "logo",
    BrandAssetKind.LOGO_DARK.value: "logo",
    BrandAssetKind.PRODUCT_PHOTO.value: "product",
    BrandAssetKind.REFERENCE_STYLE.value: "style",
}

_FIDELITY_PROMPTS = {
    "person": (
        "Analyze this person's face for identity-preserving image generation. "
        "Describe precisely: bone structure (jaw, cheekbones, nose shape), eye shape and "
        "spacing, skin tone and undertone, facial proportions, hair (style/color), and any "
        "unique/distinguishing markers (moles, scars, asymmetry). The goal is maximum "
        "photorealistic resemblance."
    ),
    "logo": (
        "Analyze this logo. Describe exactly: geometry, typography (font style/weight), "
        "precise brand colors (hex if determinable), proportions, and layout. Treat the logo "
        "as immutable — it must be reproduced without distortion or stylistic alteration."
    ),
    "product": (
        "Analyze this product image. Identify its defining characteristics: silhouette/shape, "
        "texture, material finish, structural details, and any significant identifying marks "
        "or labels that make it instantly recognizable."
    ),
    "style": (
        "Describe this image as a visual style reference: palette, tone, composition, and the "
        "overall aesthetic mood to reproduce."
    ),
}

_RESPONSE_SCHEMA_HINT = (
    'Return ONLY a JSON object with keys "identity" (an object of the details above) and '
    '"fidelity_note" (a single concise paragraph summarising the identity for an image '
    'generator). No markdown, no prose outside the JSON.'
)


def subject_for_kind(kind: str) -> str:
    return _SUBJECT_BY_KIND.get(kind, "style")


def _file_to_data_url(path: Path) -> str | None:
    try:
        raw = Path(path).read_bytes()
    except OSError:
        return None
    suffix = Path(path).suffix.lower().lstrip(".") or "png"
    mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _parse(response_text: str) -> dict:
    """Extract a JSON object from the model's reply; degrade to the raw text on failure."""
    text = response_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        return {"fidelity_note": text}


async def analyze_reference_image(path: Path, kind: str) -> dict:
    """Run a vision model over a reference image and return a structured fidelity dict.

    Always returns a dict (never raises): `{"ok": False, "error": ...}` on failure, else
    `{"ok": True, "subject": ..., "identity": {...}, "fidelity_note": "..."}`.
    """
    subject = subject_for_kind(kind)
    data_url = _file_to_data_url(path)
    if data_url is None:
        return {"ok": False, "error": f"File tidak bisa dibaca: {path}"}

    prompt = _FIDELITY_PROMPTS.get(subject, _FIDELITY_PROMPTS["style"]) + "\n\n" + _RESPONSE_SCHEMA_HINT

    try:
        import litellm

        response = await litellm.acompletion(
            model=role_model_string("media"),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        text = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - surface as a tool error, never raise
        logger.exception("Vision analysis failed for %s (%s)", path, kind)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    parsed = _parse(text)
    return {
        "ok": True,
        "subject": subject,
        "identity": parsed.get("identity", {}),
        "fidelity_note": parsed.get("fidelity_note", text.strip()),
    }
