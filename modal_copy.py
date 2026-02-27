"""
Modal.com 배포용 AI 카피라이터 생성 API

배포:  modal deploy modal_copy.py
개발:  modal serve modal_copy.py

파이프라인: 제품 Brief → 리서치 분석 → 13섹션 카피 생성
"""

import json
import os
from typing import Optional

import modal

# ──────────────────────────────────────────────
# Modal 앱 & 이미지 정의
# ──────────────────────────────────────────────
app = modal.App("copywriter-generator")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("boto3", "fastapi[standard]")
)


# ──────────────────────────────────────────────
# Bedrock 헬퍼
# ──────────────────────────────────────────────
def _get_bedrock_client(credentials: Optional[dict] = None):
    import boto3
    from botocore.config import Config

    creds = credentials or {}
    access_key = creds.get("aws_access_key_id") or os.environ.get("AWS_ACCESS_KEY_ID", "")
    secret_key = creds.get("aws_secret_access_key") or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    region = creds.get("aws_region") or os.environ.get("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        raise ValueError("AWS credentials are required.")

    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}, read_timeout=300),
    )


def _call_converse(
    client,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 4096,
    temperature: float = 0.1,
    model_id: str = "us.anthropic.claude-sonnet-4-20250514",
) -> str:
    """Bedrock Converse API를 사용하여 LLM 호출

    AgentCore 패턴 적용:
    - temperature 제어 (낮을수록 일관된 JSON 출력)
    - 응답 구조 검증
    - invoke_model 폴백
    """
    try:
        resp = client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )

        stop_reason = resp.get("stopReason", "unknown")
        print(f"  Converse stopReason={stop_reason}")

        output = resp.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])
        if not content_blocks:
            raise ValueError("Converse API returned empty content")

        text = content_blocks[0].get("text", "").strip()

        # max_tokens로 잘린 경우 JSON 닫기 시도
        if stop_reason == "max_tokens" and text.count("{") > text.count("}"):
            missing = text.count("{") - text.count("}")
            text += '"' + "}" * missing
            print(f"  Auto-closed {missing} unclosed braces")

        return text

    except client.exceptions.ValidationException as e:
        print(f"  Converse validation error, falling back to invoke_model: {e}")
        return _call_opus(client, system_prompt, user_message, max_tokens)


def _call_opus(client, system_prompt: str, user_prompt: str, max_tokens: int = 4096) -> str:
    model_id = os.environ.get("BEDROCK_TEXT_MODEL", "us.anthropic.claude-opus-4-6-v1")
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


# ──────────────────────────────────────────────
# Step 1: 리서치 분석
# ──────────────────────────────────────────────
RESEARCH_SYSTEM = """당신은 고전환 상세페이지 전문 리서치 분석가입니다.
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

## 분석 항목

### 1. 페인포인트 분석 (5개)
- 감정적 고통, 반복 실패 경험, 시간/돈 낭비, 사회적 압박, 미래 불안

### 2. 실패 원인 분석 (3개)
- 기존 방법의 한계, 숨겨진 진짜 원인, 구조적 문제 (당신 탓이 아닌)

### 3. After 이미지 (변화 후 모습)
- 구체적 결과, 감정적 해방, 시간/돈 절약 수치, 라이프스타일 변화

### 4. 반대 의견/우려 예측 (5개)
- 예상 반론, 가격 저항, 신뢰 문제, 실행 우려, 타이밍 문제

### 5. 차별화 포인트 (3개)
- Unique Mechanism, 결과 보장, 접근성

## 출력 JSON 형식:
{{
  "pain_points": [
    {{"category": "emotional|failure|waste|social|future", "pain": "...", "emotional_hook": "..."}}
  ],
  "failure_reasons": [
    {{"reason": "...", "explanation": "...", "reframe": "..."}}
  ],
  "after_image": {{
    "concrete_result": "...",
    "emotional_freedom": "...",
    "time_saved": "...",
    "lifestyle_change": "..."
  }},
  "objections": [
    {{"objection": "...", "counter": "..."}}
  ],
  "differentiators": [
    {{"point": "...", "explanation": "..."}}
  ],
  "message_framework": {{
    "core_promise": "...",
    "proof_points": ["..."],
    "emotional_journey": "고통 → 원인 이해 → 해결책 발견 → 변화 확신"
  }}
}}"""


# ──────────────────────────────────────────────
# Step 2: 13섹션 카피 생성
# ──────────────────────────────────────────────
COPY_SYSTEM = """당신은 한국 최고의 다이렉트 리스폰스 카피라이터입니다.
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
    "headline_options": ["핵심 혜택+결과 옵션1", "옵션2", "옵션3"],
    "subheadline": "타겟 명시 + 방법 힌트",
    "urgency_badge": "한정 요소",
    "cta_text": "행동 유도 버튼 텍스트"
  }},
  "section_02_pain": {{
    "intro": "공감 질문",
    "pain_points": ["구체적 고통1", "고통2", "고통3", "고통4"],
    "emotional_hook": "감정적 마무리"
  }},
  "section_03_problem": {{
    "hook": "반전 문구 (당신 탓이 아닙니다)",
    "reasons": ["진짜 원인1", "원인2", "원인3"],
    "reframe": "관점 전환 문구"
  }},
  "section_04_story": {{
    "before": "과거 상태 (공감)",
    "turning_point": "전환점",
    "after": "변화 후 상태",
    "proof": "증거/수치"
  }},
  "section_05_solution": {{
    "intro": "소개 문구",
    "product_name": "제품명",
    "one_liner": "핵심 정의",
    "target_fit": "타겟 적합성 문구"
  }},
  "section_06_how_it_works": {{
    "headline": "작동 방식 헤드라인",
    "steps": [
      {{"number": 1, "title": "...", "description": "...", "result": "..."}},
      {{"number": 2, "title": "...", "description": "...", "result": "..."}},
      {{"number": 3, "title": "...", "description": "...", "result": "..."}}
    ]
  }},
  "section_07_social_proof": {{
    "headline": "이미 검증된 결과",
    "stats": [{{"number": "...", "label": "..."}}, ...],
    "testimonials": [
      {{"name": "...", "role": "...", "quote": "...", "result": "...", "rating": 5}},
      ...
    ]
  }},
  "section_08_authority": {{
    "intro": "소개 문구",
    "bio": "이력/실적",
    "credentials": ["자격/성과1", "..."],
    "message": "진정성 메시지"
  }},
  "section_09_benefits": {{
    "headline": "혜택 헤드라인",
    "main_benefits": ["혜택1", "혜택2", ...],
    "bonus_items": [{{"name": "...", "value": "..."}}, ...],
    "total_value": "총 가치 금액"
  }},
  "section_10_risk_removal": {{
    "guarantee": "환불/보장 정책",
    "faq": [
      {{"question": "...", "answer": "..."}},
      ...
    ],
    "support": "지원 내용"
  }},
  "section_11_comparison": {{
    "without": ["없으면1", "없으면2", "없으면3"],
    "with": ["있으면1", "있으면2", "있으면3"],
    "question": "선택 질문"
  }},
  "section_12_target_filter": {{
    "recommended": ["추천 대상1", "추천2", "추천3"],
    "not_recommended": ["비추천1", "비추천2", "비추천3"]
  }},
  "section_13_final_cta": {{
    "headline": "마지막 헤드라인",
    "urgency": "긴급성 재강조",
    "price_display": "가격 표시 (정가 취소선 + 할인가)",
    "cta_button": "CTA 버튼 텍스트",
    "closing": "마무리 문구"
  }}
}}"""


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
# Modal 함수: 전체 카피 파이프라인
# ──────────────────────────────────────────────
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=300,
)
def generate_copy(brief: Optional[dict] = None, credentials: Optional[dict] = None) -> dict:
    """
    리서치 → 13섹션 카피 생성 파이프라인

    Returns:
        {
            "research": {...},
            "copy": {...},
            "brief": {...}
        }
    """
    if brief is None:
        brief = SAMPLE_BRIEF

    client = _get_bedrock_client(credentials)

    # Step 1: 리서치 분석
    print("[1/2] Running research analysis...")
    research_raw = _call_opus(client, RESEARCH_SYSTEM, _build_research_prompt(brief))
    research = _parse_json_response(research_raw)
    print(f"  Research done: {len(research)} keys")

    # Step 2: 13섹션 카피 생성
    print("[2/2] Generating 13-section copy...")
    copy_raw = _call_opus(client, COPY_SYSTEM, _build_copy_prompt(brief, research), max_tokens=8192)
    copy_result = _parse_json_response(copy_raw)
    print(f"  Copy done: {len(copy_result)} sections")

    return {
        "research": research,
        "copy": copy_result,
        "brief": brief,
    }


# ──────────────────────────────────────────────
# Web Endpoint: FastAPI
# ──────────────────────────────────────────────
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST", docs=True)
def generate(payload: Optional[dict] = None):
    """POST /generate - 카피 생성 API

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

    try:
        result = generate_copy.local(brief, credentials)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# ──────────────────────────────────────────────
# Deep Research (Perplexity-style)
# ──────────────────────────────────────────────
DEEP_RESEARCH_SYSTEM = """당신은 고전환 상세페이지 전문 리서치 분석가입니다.
사용자가 자유 형식으로 입력한 제품/서비스 정보를 분석하여 심층 리서치를 수행합니다.

## 역할
1. 사용자 입력에서 제품명, 타겟 고객, 핵심 문제, 핵심 혜택 등을 자동으로 추출
2. 추출한 정보를 바탕으로 타겟 고객의 심층 분석과 설득 메시지 프레임을 설계
3. 정보가 부족한 부분은 합리적으로 추론하여 채움

## 분석 원칙
1. 구체성: 추상적 표현 대신 숫자와 상황으로
2. 감정 연결: 타겟이 "이거 내 얘기다" 느끼도록
3. 진정성: 과장 없이 실제 해결 가능한 것만
4. 논리 흐름: 고통 → 원인 → 해결 → 결과의 자연스러운 연결

## 출력 JSON 형식
반드시 아래 JSON 형식으로만 응답하세요:
{
  "extracted_brief": {
    "product_name": "추출된 제품명",
    "one_liner": "추출된 한 줄 정의",
    "target_audience": "추출된 타겟 고객",
    "main_problem": "추출된 핵심 문제",
    "key_benefit": "추출된 핵심 혜택"
  },
  "pain_points": [
    {"category": "emotional|failure|waste|social|future", "pain": "...", "emotional_hook": "..."}
  ],
  "failure_reasons": [
    {"reason": "...", "explanation": "...", "reframe": "..."}
  ],
  "after_image": {
    "concrete_result": "...",
    "emotional_freedom": "...",
    "time_saved": "...",
    "lifestyle_change": "..."
  },
  "objections": [
    {"objection": "...", "counter": "..."}
  ],
  "differentiators": [
    {"point": "...", "explanation": "..."}
  ],
  "message_framework": {
    "core_promise": "...",
    "proof_points": ["..."],
    "emotional_journey": "고통 → 원인 이해 → 해결책 발견 → 변화 확신"
  }
}"""


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("aws-bedrock-secrets")],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST", docs=True)
def deep_research(payload: Optional[dict] = None):
    """POST /deep_research - 자유 텍스트 기반 심층 리서치

    Body:
    {
        "aws_credentials": {"aws_access_key_id": "...", "aws_secret_access_key": "...", "aws_region": "..."},
        "query": "자유 텍스트 제품/서비스 설명"
    }
    """
    from fastapi.responses import JSONResponse

    if not payload or not payload.get("query"):
        return JSONResponse(content={"error": "query 필드가 필요합니다."}, status_code=400)

    query = payload["query"]
    credentials = payload.get("aws_credentials")

    try:
        client = _get_bedrock_client(credentials)
        raw = _call_converse(client, DEEP_RESEARCH_SYSTEM, query, max_tokens=16384)
        research = _parse_json_response(raw)
        return JSONResponse(content={"research": research, "query": query})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.function(image=image, secrets=[modal.Secret.from_name("aws-bedrock-secrets")])
@modal.fastapi_endpoint(method="GET", docs=True)
def health():
    """GET /health - API 상태 확인"""
    return {
        "status": "healthy",
        "service": "copywriter-generator",
        "text_model": os.environ.get("BEDROCK_TEXT_MODEL", "us.anthropic.claude-opus-4-6-v1"),
    }


# ──────────────────────────────────────────────
# CLI 엔트리포인트
# ──────────────────────────────────────────────
@app.local_entrypoint()
def main():
    print("Generating copy...")
    result = generate_copy.remote(SAMPLE_BRIEF)
    print(f"Research keys: {list(result['research'].keys())}")
    print(f"Copy sections: {list(result['copy'].keys())}")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
