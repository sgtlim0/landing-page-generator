"""
Modal.com 배포용 랜딩 페이지 생성 API

배포:  modal deploy modal_app.py
개발:  modal serve modal_app.py
"""

import io
import json
import os
import base64
import time
from pathlib import Path
from typing import Optional

import modal

# ──────────────────────────────────────────────
# Modal 앱 & 이미지 정의
# ──────────────────────────────────────────────
app = modal.App("landing-page-generator")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("boto3", "Pillow", "fastapi[standard]")
)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────
NOVA_CANVAS_MAX_CHARS = 1024
FIXED_WIDTH = 1200

SECTION_HEIGHTS = {
    "01_hero": 800, "02_pain": 600, "03_problem": 500,
    "04_story": 700, "05_solution": 400, "06_how_it_works": 600,
    "07_social_proof": 800, "08_authority": 500, "09_benefits": 700,
    "10_risk_removal": 500, "11_comparison": 400, "12_target_filter": 400,
    "13_final_cta": 600,
}


# ──────────────────────────────────────────────
# Bedrock 헬퍼
# ──────────────────────────────────────────────
def _get_bedrock_client(credentials: Optional[dict] = None):
    """
    Bedrock Runtime 클라이언트를 생성합니다.
    credentials가 제공되면 해당 키를 사용하고,
    없으면 환경변수(Modal Secret)에서 가져옵니다.
    """
    import boto3
    from botocore.config import Config

    creds = credentials or {}
    access_key = creds.get("aws_access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID", "")
    secret_key = creds.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    region = creds.get("aws_region") or os.environ.get("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        raise ValueError("AWS credentials are required. Provide aws_access_key_id and aws_secret_access_key.")

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}, read_timeout=300),
    )


def _round16(v: int) -> int:
    return max(320, min(4096, round(v / 16) * 16))


def _compress_prompt(client, prompt: str) -> str:
    """Opus 4.6으로 프롬프트를 1024자 이내로 압축합니다."""
    if len(prompt) <= NOVA_CANVAS_MAX_CHARS:
        return prompt

    model_id = os.environ.get("BEDROCK_TEXT_MODEL", "us.anthropic.claude-sonnet-4-6-v1")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": (
                f"Compress this image generation prompt to UNDER {NOVA_CANVAS_MAX_CHARS} characters "
                f"for Nova Canvas API.\n\nRULES:\n"
                "- Keep ALL visual layout details (positions, colors, sizes)\n"
                "- Keep Korean text content exactly as-is\n"
                "- Remove verbose style descriptions - use short keywords\n"
                "- Output ONLY the compressed prompt\n\n"
                f"ORIGINAL:\n{prompt}"
            ),
        }],
    }

    try:
        resp = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(resp["body"].read())
        compressed = result.get("content", [{}])[0].get("text", "").strip()
        return compressed[:NOVA_CANVAS_MAX_CHARS] if compressed else prompt[:NOVA_CANVAS_MAX_CHARS]
    except Exception:
        return prompt[:NOVA_CANVAS_MAX_CHARS]


def _generate_one_image(client, prompt: str, width: int, height: int) -> Optional[bytes]:
    """Nova Canvas로 이미지 1장을 생성하여 PNG bytes를 반환합니다."""
    w, h = _round16(width), _round16(height)
    max_px = 4_194_304
    if w * h > max_px:
        r = (max_px / (w * h)) ** 0.5
        w, h = _round16(int(w * r)), _round16(int(h * r))

    full = f"Photorealistic professional Korean landing page section, DSLR quality, studio lighting, Sulwhasoo/Laneige ad style. {prompt}"
    if len(full) > NOVA_CANVAS_MAX_CHARS:
        full = _compress_prompt(client, full)

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": full,
            "negativeText": (
                "cartoon, illustration, vector art, flat colors, digital art, "
                "anime, comic, overly smooth skin, plastic look, AI artifacts, "
                "low quality, blurry, watermark, text errors"
            ),
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": w,
            "height": h,
            "quality": "premium",
            "seed": int(time.time()) % 2_147_483_647,
        },
    }

    model_id = os.environ.get("BEDROCK_IMAGE_MODEL", "amazon.nova-canvas-v1:0")
    resp = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(resp["body"].read())
    images = result.get("images", [])
    return base64.b64decode(images[0]) if images else None


# ──────────────────────────────────────────────
# 프롬프트 생성 (generate_page.py 로직 포함)
# ──────────────────────────────────────────────
def _build_prompts(brief: dict) -> dict:
    style = brief.get("style_preset", "minimal")
    colors = brief.get("brand_colors", {})
    primary = colors.get("primary", "#2563EB")
    accent = colors.get("accent", "#F59E0B")
    product_name = brief.get("product_name", "제품명")
    one_liner = brief.get("one_liner", "제품 설명")
    target = brief.get("target_audience", "타겟 고객")
    problem = brief.get("main_problem", "해결하는 문제")
    benefit = brief.get("key_benefit", "핵심 혜택")
    price = brief.get("price", {})
    urgency = brief.get("urgency", {})

    anchor = (
        f"Style: {style}, modern Korean landing page. "
        f"Colors: Primary {primary}, Accent {accent}, white/gray bg. "
        f"Bold Korean headlines, clean body text."
    )

    return {
        "01_hero": {
            "prompt": f"{anchor} Hero section 1200x800. Gradient {primary} bg. Top-right urgency badge \"{urgency.get('value','한정 특가')}\". Center: large headline area. Below: subheadline. Bottom: CTA button \"지금 시작하기\". Geometric shapes, glow effects. Key message: \"{benefit}\"",
            "width": 1200, "height": 800, "filename": "01_hero.png",
        },
        "02_pain": {
            "prompt": f"{anchor} Pain points 1200x600. Light gray #F3F4F6 bg. Header \"이런 고민 하고 계신가요?\". 3 horizontal pain point cards with worry icons. Related to: \"{problem}\". Empathetic mood.",
            "width": 1200, "height": 600, "filename": "02_pain.png",
        },
        "03_problem": {
            "prompt": f"{anchor} Problem section 1200x500. White bg. Hook \"당신 탓이 아닙니다\". 3 numbered reason cards with connecting arrows. Reframing the problem.",
            "width": 1200, "height": 500, "filename": "03_problem.png",
        },
        "04_story": {
            "prompt": f"{anchor} Before/After 1200x700. Left: \"Before\" muted colors, stressed. Center: transformation arrow. Right: \"After\" vibrant success. Before: \"{problem}\". After: \"{benefit}\". Upward graphs, checkmarks.",
            "width": 1200, "height": 700, "filename": "04_story.png",
        },
        "05_solution": {
            "prompt": f"{anchor} Solution intro 1200x400. White bg. Center: product name \"{product_name}\". Below: \"{one_liner}\". Clean, impactful, brand colors.",
            "width": 1200, "height": 400, "filename": "05_solution.png",
        },
        "06_how_it_works": {
            "prompt": f"{anchor} How it works 1200x600. Light gray bg. Header \"이렇게 작동합니다\". 3-step horizontal process with number circles, icons, connecting lines.",
            "width": 1200, "height": 600, "filename": "06_how_it_works.png",
        },
        "07_social_proof": {
            "prompt": f"{anchor} Social proof 1200x800. White bg. Top: 3 stat numbers bar. Center: 3 testimonial cards with avatar, quote, name, star ratings, verified badges.",
            "width": 1200, "height": 800, "filename": "07_social_proof.png",
        },
        "08_authority": {
            "prompt": f"{anchor} Authority 1200x500. Light gray bg. Left: professional headshot circle. Right: bio, credentials list. Trust indicators.",
            "width": 1200, "height": 500, "filename": "08_authority.png",
        },
        "09_benefits": {
            "prompt": f"{anchor} Benefits 1200x700. Subtle {primary} tint bg. Header \"What you get\". Left: 5-6 checkmark benefits. Right: bonus items with gift icons. Bottom: total value calculation.",
            "width": 1200, "height": 700, "filename": "09_benefits.png",
        },
        "10_risk_removal": {
            "prompt": f"{anchor} Risk removal 1200x500. White bg. Center: guarantee badge/seal. Guarantee text. Bottom: 2-3 FAQ accordion items. Shield icon.",
            "width": 1200, "height": 500, "filename": "10_risk_removal.png",
        },
        "11_comparison": {
            "prompt": f"{anchor} Comparison 1200x400. Light gray bg. Two columns: Left \"Without\" red X marks. Right \"With\" green checkmarks. Bottom: \"어떤 걸 선택하시겠습니까?\"",
            "width": 1200, "height": 400, "filename": "11_comparison.png",
        },
        "12_target_filter": {
            "prompt": f"{anchor} Target filter 1200x400. White bg. Two columns: Left \"이런 분께 추천\" green checkmarks. Right \"이런 분은 비추천\" gray X marks. Target: \"{target}\"",
            "width": 1200, "height": 400, "filename": "12_target_filter.png",
        },
        "13_final_cta": {
            "prompt": f"{anchor} Final CTA 1200x600. Dark {primary} gradient bg. Compelling headline. Price: {price.get('original','199,000원')} strikethrough, {price.get('discounted','99,000원')} highlighted large. CTA button \"지금 시작하기\" {accent} color. Urgency: \"{urgency.get('value','한정 수량')}\". Glowing button.",
            "width": 1200, "height": 600, "filename": "13_final_cta.png",
        },
    }


def _stitch_images(image_bytes_list: list[bytes]) -> bytes:
    """PNG bytes 리스트를 세로로 이어붙여 최종 PNG bytes를 반환합니다."""
    from PIL import Image

    pil_images = []
    for raw in image_bytes_list:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        if img.width != FIXED_WIDTH:
            ratio = FIXED_WIDTH / img.width
            img = img.resize((FIXED_WIDTH, int(img.height * ratio)), Image.Resampling.LANCZOS)
        pil_images.append(img)

    total_h = sum(i.height for i in pil_images)
    canvas = Image.new("RGBA", (FIXED_WIDTH, total_h), (255, 255, 255, 255))

    y = 0
    for img in pil_images:
        canvas.paste(img, (0, y), img)
        y += img.height

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ──────────────────────────────────────────────
# 샘플 Brief
# ──────────────────────────────────────────────
SAMPLE_BRIEF = {
    "product_name": "AI 마케팅 자동화",
    "one_liner": "광고비 50% 절감하는 AI 기반 마케팅 최적화 시스템",
    "target_audience": "월 광고비 100만원 이상 쓰는 스마트스토어 셀러",
    "main_problem": "광고 최적화에 하루 2시간 소비하면서도 ROAS는 제자리",
    "key_benefit": "AI가 24시간 자동으로 광고 최적화, 평균 광고비 50% 절감",
    "price": {"original": "199,000원", "discounted": "99,000원", "period": "월"},
    "urgency": {"type": "quantity", "value": "선착순 100명", "bonus": "1:1 셋업 컨설팅 무료"},
    "style_preset": "minimal",
    "brand_colors": {"primary": "#2563EB", "secondary": "#60A5FA", "accent": "#F59E0B"},
}


# ──────────────────────────────────────────────
# Modal 함수: 전체 파이프라인
# ──────────────────────────────────────────────
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=900,  # 15분
)
def generate_landing_page(brief: Optional[dict] = None, credentials: Optional[dict] = None) -> dict:
    """
    전체 상세페이지를 생성하고 결과를 반환합니다.

    Args:
        brief: 제품 정보
        credentials: AWS 자격증명 (없으면 환경변수 사용)

    Returns:
        {
            "sections": {"01_hero": "<base64 png>", ...},
            "final_page": "<base64 png>",
            "metadata": {...}
        }
    """
    if brief is None:
        brief = SAMPLE_BRIEF

    client = _get_bedrock_client(credentials)
    prompts = _build_prompts(brief)

    sections = {}
    section_bytes_ordered = []
    total = len(prompts)

    for i, (key, data) in enumerate(prompts.items(), 1):
        print(f"[{i}/{total}] Generating {key}...")
        png_bytes = _generate_one_image(client, data["prompt"], data["width"], data["height"])

        if png_bytes:
            sections[key] = base64.b64encode(png_bytes).decode()
            section_bytes_ordered.append(png_bytes)
            print(f"  Done: {len(png_bytes)} bytes")
        else:
            print(f"  Failed: {key}")

        if i < total:
            time.sleep(3)

    final_bytes = _stitch_images(section_bytes_ordered) if section_bytes_ordered else b""

    return {
        "sections": sections,
        "final_page": base64.b64encode(final_bytes).decode() if final_bytes else "",
        "metadata": {
            "total_sections": total,
            "generated_sections": len(sections),
            "brief": brief,
        },
    }


# ──────────────────────────────────────────────
# 카피라이터 헬퍼 함수
# ──────────────────────────────────────────────
def _call_opus(client, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    """Opus 4.6으로 텍스트를 생성합니다."""
    model_id = os.environ.get("BEDROCK_TEXT_MODEL", "us.anthropic.claude-sonnet-4-6-v1")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    resp = client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(resp["body"].read())
    return result.get("content", [{}])[0].get("text", "").strip()


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 안전하게 추출합니다."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {"error": "Failed to parse JSON", "raw_text": text[:500]}


_RESEARCH_SYSTEM = """당신은 고전환 상세페이지 전문 리서치 분석가입니다.
제품 정보를 바탕으로 타겟 고객의 심층 분석과 설득 메시지 프레임을 설계합니다.

분석 원칙:
1. 구체성: 추상적 표현 대신 숫자와 상황으로
2. 감정 연결: 타겟이 "이거 내 얘기다" 느끼도록
3. 진정성: 과장 없이 실제 해결 가능한 것만
4. 논리 흐름: 고통 → 원인 → 해결 → 결과의 자연스러운 연결

반드시 JSON 형식으로만 응답하세요."""


def _build_research_prompt(brief: dict) -> str:
    return f"""다음 제품 정보를 분석하여 리서치 결과를 JSON으로 생성하세요.

## 제품 정보
- 제품명: {brief.get('product_name', '')}
- 한 줄 정의: {brief.get('one_liner', '')}
- 타겟 고객: {brief.get('target_audience', '')}
- 핵심 문제: {brief.get('main_problem', '')}
- 핵심 혜택: {brief.get('key_benefit', '')}
- 가격: 정가 {brief.get('price', {}).get('original', '')}, 할인가 {brief.get('price', {}).get('discounted', '')}
- 긴급성: {brief.get('urgency', {}).get('value', '')}

## 출력 JSON 형식:
{{
  "pain_points": [
    {{"category": "emotional|failure|waste|social|future", "pain": "구체적 고통", "emotional_hook": "감정적 연결 문구"}}
  ],
  "failure_reasons": [
    {{"reason": "실패 원인", "explanation": "설명", "reframe": "관점 전환"}}
  ],
  "after_image": {{
    "concrete_result": "구체적 결과",
    "emotional_freedom": "감정적 해방",
    "time_saved": "시간 절약",
    "lifestyle_change": "라이프스타일 변화"
  }},
  "objections": [
    {{"objection": "예상 반론", "counter": "반박"}}
  ],
  "differentiators": [
    {{"point": "차별점", "explanation": "설명"}}
  ],
  "message_framework": {{
    "core_promise": "핵심 약속",
    "proof_points": ["증거1", "증거2"],
    "emotional_journey": "고통 → 원인 이해 → 해결책 발견 → 변화 확신"
  }}
}}"""


_COPY_SYSTEM = """당신은 한국 최고의 다이렉트 리스폰스 카피라이터입니다.
리서치 결과를 바탕으로 13개 섹션의 고전환 판매 카피를 작성합니다.

카피 원칙:
1. 한국어 자연스러운 구어체 - 번역투 금지
2. 감정 → 논리 흐름 - 먼저 공감, 그 다음 설명
3. 구체적 숫자 - "많은" 대신 "143명", "빠르게" 대신 "3일 만에"
4. 2인칭 활용 - "당신", "여러분" 적절히
5. 짧은 문장 - 한 문장 20자 내외

반드시 JSON 형식으로만 응답하세요."""


def _build_copy_prompt(brief: dict, research: dict) -> str:
    price = brief.get("price", {})
    urgency = brief.get("urgency", {})
    return f"""다음 제품 정보와 리서치 결과를 바탕으로 13섹션 카피를 JSON으로 생성하세요.

## 제품 정보
- 제품명: {brief.get('product_name', '')}
- 한 줄 정의: {brief.get('one_liner', '')}
- 타겟: {brief.get('target_audience', '')}
- 핵심 문제: {brief.get('main_problem', '')}
- 핵심 혜택: {brief.get('key_benefit', '')}
- 정가: {price.get('original', '')}
- 할인가: {price.get('discounted', '')}
- 기간: {price.get('period', '월')}
- 긴급성: {urgency.get('value', '')}
- 보너스: {urgency.get('bonus', '')}

## 리서치 결과
{json.dumps(research, ensure_ascii=False, indent=2)}

## 13섹션 출력 형식:
{{
  "section_01_hero": {{
    "headline_options": ["옵션1", "옵션2", "옵션3"],
    "subheadline": "타겟 명시 + 방법 힌트",
    "urgency_badge": "한정 요소",
    "cta_text": "행동 유도 버튼"
  }},
  "section_02_pain": {{
    "intro": "공감 질문",
    "pain_points": ["고통1", "고통2", "고통3", "고통4"],
    "emotional_hook": "감정적 마무리"
  }},
  "section_03_problem": {{
    "hook": "반전 문구",
    "reasons": ["원인1", "원인2", "원인3"],
    "reframe": "관점 전환"
  }},
  "section_04_story": {{
    "before": "과거 상태",
    "turning_point": "전환점",
    "after": "변화 후",
    "proof": "증거"
  }},
  "section_05_solution": {{
    "intro": "소개",
    "product_name": "제품명",
    "one_liner": "핵심 정의",
    "target_fit": "적합성"
  }},
  "section_06_how_it_works": {{
    "headline": "헤드라인",
    "steps": [{{"number": 1, "title": "...", "description": "...", "result": "..."}}]
  }},
  "section_07_social_proof": {{
    "headline": "이미 검증된 결과",
    "stats": [{{"number": "...", "label": "..."}}],
    "testimonials": [{{"name": "...", "role": "...", "quote": "...", "result": "...", "rating": 5}}]
  }},
  "section_08_authority": {{
    "intro": "소개",
    "bio": "이력",
    "credentials": ["성과1"],
    "message": "진정성 메시지"
  }},
  "section_09_benefits": {{
    "headline": "헤드라인",
    "main_benefits": ["혜택1"],
    "bonus_items": [{{"name": "...", "value": "..."}}],
    "total_value": "총 가치"
  }},
  "section_10_risk_removal": {{
    "guarantee": "보장 정책",
    "faq": [{{"question": "...", "answer": "..."}}],
    "support": "지원"
  }},
  "section_11_comparison": {{
    "without": ["없으면1"],
    "with": ["있으면1"],
    "question": "선택 질문"
  }},
  "section_12_target_filter": {{
    "recommended": ["추천1"],
    "not_recommended": ["비추천1"]
  }},
  "section_13_final_cta": {{
    "headline": "헤드라인",
    "urgency": "긴급성",
    "price_display": "가격 표시",
    "cta_button": "CTA 텍스트",
    "closing": "마무리"
  }}
}}"""


# ──────────────────────────────────────────────
# Web Endpoint: FastAPI
# ──────────────────────────────────────────────
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=900,
)
@modal.fastapi_endpoint(method="POST", docs=True)
def generate(payload: Optional[dict] = None):
    """POST /generate - 상세페이지 생성 API

    Body format:
    {
        "aws_credentials": {"aws_access_key_id": "...", "aws_secret_access_key": "...", "aws_region": "..."},
        "brief": { ...product info... }
    }
    Or legacy format (brief only): { "product_name": "...", ... }
    """
    from fastapi.responses import Response

    credentials = None
    brief = None

    if payload and "aws_credentials" in payload:
        credentials = payload.get("aws_credentials")
        brief = payload.get("brief")
    else:
        brief = payload

    result = generate_landing_page.local(brief, credentials)

    if result["final_page"]:
        return Response(
            content=base64.b64decode(result["final_page"]),
            media_type="image/png",
            headers={
                "X-Sections-Generated": str(result["metadata"]["generated_sections"]),
                "X-Sections-Total": str(result["metadata"]["total_sections"]),
            },
        )
    return {"error": "Failed to generate landing page", "metadata": result["metadata"]}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST", docs=True)
def generate_copy(payload: Optional[dict] = None):
    """POST /generate_copy - AI 카피라이터: 리서치 분석 + 13섹션 카피 생성

    Body:
    {
        "aws_credentials": {"aws_access_key_id": "...", "aws_secret_access_key": "...", "aws_region": "..."},
        "brief": { ...product info... }
    }
    """
    from fastapi.responses import JSONResponse

    credentials = None
    brief = None

    if payload and "aws_credentials" in payload:
        credentials = payload.get("aws_credentials")
        brief = payload.get("brief")
    else:
        brief = payload

    if brief is None:
        brief = SAMPLE_BRIEF

    try:
        client = _get_bedrock_client(credentials)

        # Step 1: 리서치 분석
        print("[Copy 1/2] Running research analysis...")
        research_raw = _call_opus(client, _RESEARCH_SYSTEM, _build_research_prompt(brief))
        research = _parse_json_response(research_raw)
        print(f"  Research done: {len(research)} keys")

        # Step 2: 13섹션 카피 생성
        print("[Copy 2/2] Generating 13-section copy...")
        copy_raw = _call_opus(client, _COPY_SYSTEM, _build_copy_prompt(brief, research), max_tokens=8192)
        copy_result = _parse_json_response(copy_raw)
        print(f"  Copy done: {len(copy_result)} sections")

        return JSONResponse(content={
            "research": research,
            "copy": copy_result,
            "brief": brief,
        })
    except Exception as e:
        import traceback
        print(f"[generate_copy] Error: {traceback.format_exc()}")
        return JSONResponse(content={"error": "Copy generation failed. Please check your credentials and try again."}, status_code=500)


@app.function(image=image, secrets=[modal.Secret.from_name("aws-bedrock-secrets")])
@modal.fastapi_endpoint(method="GET", docs=True)
def health():
    """GET /health - API 상태 확인 (환경변수 자격증명 사용)"""
    client = _get_bedrock_client(None)
    text_model = os.environ.get("BEDROCK_TEXT_MODEL", "us.anthropic.claude-sonnet-4-6-v1")

    try:
        resp = client.invoke_model(
            modelId=text_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 20,
                "messages": [{"role": "user", "content": "Say OK"}],
            }),
        )
        result = json.loads(resp["body"].read())
        text = result.get("content", [{}])[0].get("text", "")
        return {
            "status": "healthy",
            "text_model": text_model,
            "image_model": os.environ.get("BEDROCK_IMAGE_MODEL", "amazon.nova-canvas-v1:0"),
            "test_response": text,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ──────────────────────────────────────────────
# CLI 엔트리포인트 (modal run modal_app.py)
# ──────────────────────────────────────────────
@app.local_entrypoint()
def main():
    print("Generating landing page...")
    result = generate_landing_page.remote(SAMPLE_BRIEF)
    print(f"Generated {result['metadata']['generated_sections']}/{result['metadata']['total_sections']} sections")

    if result["final_page"]:
        output_path = Path("output/modal_final_page.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(result["final_page"]))
        print(f"Saved: {output_path}")
