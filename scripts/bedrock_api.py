"""
AWS Bedrock를 사용하여 상세페이지 섹션 이미지를 생성하는 모듈
- 이미지 생성: Amazon Nova Canvas (amazon.nova-canvas-v1:0)
- 프롬프트 압축: Claude Sonnet 4.6 (us.anthropic.claude-sonnet-4-6)
- Nova Canvas 프롬프트 제한: 최대 1024자
"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
IMAGE_MODEL_ID = os.getenv("BEDROCK_IMAGE_MODEL", "amazon.nova-canvas-v1:0")
TEXT_MODEL_ID = os.getenv("BEDROCK_TEXT_MODEL", "us.anthropic.claude-opus-4-6-v1")

NOVA_CANVAS_MAX_CHARS = 1024

_bedrock_client = None


def _get_client():
    """Bedrock Runtime 클라이언트를 반환합니다 (싱글턴)."""
    global _bedrock_client
    if _bedrock_client is None:
        config = Config(
            retries={"max_attempts": 3, "mode": "adaptive"},
            read_timeout=300,
        )
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=config,
        )
    return _bedrock_client


def _round_to_multiple(value: int, multiple: int = 16) -> int:
    """Nova Canvas는 16의 배수 크기만 허용합니다."""
    return max(320, min(4096, round(value / multiple) * multiple))


def _compress_prompt_with_sonnet(prompt: str, max_chars: int = NOVA_CANVAS_MAX_CHARS) -> str:
    """
    Sonnet 4.6을 사용하여 긴 프롬프트를 Nova Canvas 제한(1024자) 내로 압축합니다.
    핵심 시각적 요소와 레이아웃 지시를 유지하면서 불필요한 텍스트를 제거합니다.
    """
    if len(prompt) <= max_chars:
        return prompt

    client = _get_client()

    compress_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": f"""Compress this image generation prompt to UNDER {max_chars} characters for Nova Canvas API.

RULES:
- Keep ALL visual layout details (positions, colors, sizes)
- Keep Korean text content exactly as-is
- Remove verbose style descriptions - use short keywords instead
- Remove checklists and redundant instructions
- Output ONLY the compressed prompt, nothing else

ORIGINAL PROMPT:
{prompt}"""
            }
        ],
    }

    try:
        response = client.invoke_model(
            modelId=TEXT_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(compress_request),
        )

        result = json.loads(response["body"].read())
        compressed = result.get("content", [{}])[0].get("text", "").strip()

        if len(compressed) <= max_chars and len(compressed) > 0:
            print(f"  Prompt compressed: {len(prompt)} -> {len(compressed)} chars")
            return compressed

        # 압축 후에도 초과하면 잘라냄
        print(f"  Prompt still long ({len(compressed)} chars), truncating to {max_chars}")
        return compressed[:max_chars]

    except Exception as e:
        print(f"  Prompt compression failed: {e}, truncating directly")
        return prompt[:max_chars]


def generate_image(
    prompt: str,
    output_path: str,
    width: int = 1200,
    height: int = 1200,
    negative_prompt: str = "",
) -> Optional[str]:
    """
    Amazon Nova Canvas를 사용하여 이미지를 생성합니다.
    프롬프트가 1024자를 초과하면 Sonnet 4.6으로 자동 압축합니다.

    Args:
        prompt: 이미지 생성 프롬프트
        output_path: 저장할 파일 경로
        width: 이미지 너비
        height: 이미지 높이
        negative_prompt: 네거티브 프롬프트

    Returns:
        저장된 파일 경로 또는 None (실패시)
    """
    client = _get_client()

    adj_width = _round_to_multiple(width)
    adj_height = _round_to_multiple(height)

    # 총 픽셀 수 제한 (4,194,304)
    max_pixels = 4_194_304
    if adj_width * adj_height > max_pixels:
        ratio = (max_pixels / (adj_width * adj_height)) ** 0.5
        adj_width = _round_to_multiple(int(adj_width * ratio))
        adj_height = _round_to_multiple(int(adj_height * ratio))

    # 스타일 키워드를 포함한 간결한 프롬프트 구성
    full_prompt = (
        f"Photorealistic professional Korean landing page section, "
        f"DSLR quality, studio lighting, Sulwhasoo/Laneige ad style. "
        f"{prompt}"
    )

    # Nova Canvas 1024자 제한 처리: Sonnet 4.6으로 압축
    if len(full_prompt) > NOVA_CANVAS_MAX_CHARS:
        print(f"  Prompt exceeds {NOVA_CANVAS_MAX_CHARS} chars ({len(full_prompt)}), compressing with Sonnet...")
        full_prompt = _compress_prompt_with_sonnet(full_prompt)

    default_negative = (
        "cartoon, illustration, vector art, flat colors, digital art, "
        "anime, comic, overly smooth skin, plastic look, AI artifacts, "
        "low quality, blurry, watermark, text errors"
    )
    neg = negative_prompt if negative_prompt else default_negative

    body = {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": full_prompt,
            "negativeText": neg,
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": adj_width,
            "height": adj_height,
            "quality": "premium",
            "seed": int(time.time()) % 2_147_483_647,
        },
    }

    try:
        print(f"Calling Bedrock: {IMAGE_MODEL_ID} ({adj_width}x{adj_height})")

        response = client.invoke_model(
            modelId=IMAGE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        result = json.loads(response["body"].read())

        if result.get("error"):
            print(f"Error: {result['error']}")
            return None

        images = result.get("images", [])
        if not images:
            print("Error: No images in response")
            return None

        image_bytes = base64.b64decode(images[0])

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(image_bytes)

        print(f"Image saved: {output_path} ({adj_width}x{adj_height})")
        return output_path

    except client.exceptions.ThrottlingException:
        print("Error: API throttled. Retrying after 10s...")
        time.sleep(10)
        return generate_image(prompt, output_path, width, height, negative_prompt)
    except client.exceptions.ValidationException as e:
        print(f"Error: Validation failed - {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_text(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """
    Claude Sonnet (Bedrock)을 사용하여 텍스트를 생성합니다.

    Args:
        prompt: 텍스트 생성 프롬프트
        max_tokens: 최대 토큰 수

    Returns:
        생성된 텍스트 또는 None
    """
    client = _get_client()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    try:
        print(f"Calling Bedrock: {TEXT_MODEL_ID}")

        response = client.invoke_model(
            modelId=TEXT_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        result = json.loads(response["body"].read())
        text_blocks = [
            block["text"]
            for block in result.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks) if text_blocks else None

    except Exception as e:
        print(f"Error: {e}")
        return None


def generate_all_sections(
    prompts_file: str,
    output_dir: str,
    delay_between: float = 2.0,
) -> list:
    """
    모든 섹션 이미지를 순차적으로 생성합니다.

    Args:
        prompts_file: prompts.json 파일 경로
        output_dir: 출력 디렉토리
        delay_between: API 호출 간 대기 시간 (초)

    Returns:
        생성된 이미지 경로 리스트
    """
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    generated_images = []
    total_sections = len(prompts_data)

    for i, (section_key, section_data) in enumerate(prompts_data.items(), 1):
        print(f"\n[{i}/{total_sections}] Generating {section_key}...")

        prompt = section_data["prompt"]
        width = section_data.get("width", 1200)
        height = section_data.get("height", 600)
        filename = section_data.get("filename", f"{section_key}.png")

        output_path = os.path.join(output_dir, filename)

        result = generate_image(prompt, output_path, width, height)

        if result:
            generated_images.append(result)
        else:
            print(f"Warning: Failed to generate {section_key}")

        if i < total_sections:
            print(f"Waiting {delay_between}s before next request...")
            time.sleep(delay_between)

    print(f"\nGeneration complete: {len(generated_images)}/{total_sections} images")
    return generated_images


def test_api_connection() -> bool:
    """API 연결을 테스트합니다."""
    try:
        client = _get_client()
        print(f"Region: {AWS_REGION}")
        print(f"Image Model: {IMAGE_MODEL_ID}")
        print(f"Text Model: {TEXT_MODEL_ID}")

        # Sonnet으로 간단한 텍스트 생성 테스트
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [
                {"role": "user", "content": "Say 'API connection successful' in Korean."}
            ],
        }

        response = client.invoke_model(
            modelId=TEXT_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        result = json.loads(response["body"].read())
        text = result.get("content", [{}])[0].get("text", "")
        print(f"Sonnet response: {text}")
        print("API connection successful!")
        return True

    except Exception as e:
        print(f"API test error: {e}")
        return False


if __name__ == "__main__":
    print("Testing AWS Bedrock API connection...")
    test_api_connection()
