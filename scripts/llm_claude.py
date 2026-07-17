#!/usr/bin/env python3
"""Claude 래퍼 — 콜드스타트 seed 우도 추론용 complete_fn 제공 (개방 체크리스트 항목 4).

engines/coldstart.build_llm_infer(complete_fn)에 주입해 seed 자연어 우도를
오프라인 키워드 휴리스틱 → 실제 LLM으로 승격한다. engines/ 는 Flask·SDK 무의존
원칙이라(CLAUDE.md 규칙 2) 이 SDK 의존 어댑터는 scripts/ 에 둔다(주입식).

anthropic SDK는 지연 임포트 — 미설치 환경(서버 gunicorn 등)에서 이 모듈을
임포트하지 않는 한 영향 없음. 자격증명은 SDK 기본 해석
(ANTHROPIC_API_KEY 또는 `ant auth login` 프로필) — 이 코드는 키를 받지 않는다.

사용:
    from scripts.llm_claude import build_claude_complete_fn
    from engines.coldstart import build_llm_infer, predict_coffee_type
    infer = build_llm_infer(build_claude_complete_fn())
    predict_coffee_type(age, gender, seeds=["아메리카노 진하게"], llm_infer=infer)
"""

# seed→극 우도는 단문 분류라 대형 추론 불필요. skill 지침상 기본은 opus-4-8,
# 대량 분류엔 --llm-model claude-haiku-4-5 가 훨씬 저렴(하네스에서 노출).
DEFAULT_LLM_MODEL = "claude-opus-4-8"


def build_claude_complete_fn(model: str = DEFAULT_LLM_MODEL, max_tokens: int = 64,
                             cache: bool = True, client=None):
    """prompt(str) -> 응답 텍스트(str) 콜러블 반환.

    build_llm_infer가 이 콜러블에 LLM_LIKELIHOOD_PROMPT를 넘기고, 반환 텍스트에서
    JSON을 파싱한다(파싱/클램프/폴백은 build_llm_infer 책임). 여기선 순수 완성만.

    model: Claude 모델 ID. seed 극 분류는 경량 작업 — 대량이면 haiku가 경제적.
    max_tokens: JSON 한 줄이면 충분(작게 유지 = 지연·비용↓).
    cache: 동일 seed 프롬프트 메모이즈(하네스가 중복 seed를 반복 호출해도 1회 과금).
    client: 테스트용 주입구(미지정 시 anthropic.Anthropic() 지연 생성).
    """
    if client is None:
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - 환경 의존
            raise RuntimeError(
                "anthropic SDK 미설치 — LLM seed 우도 경로(--llm)에 필요. "
                "`.venv/bin/pip install anthropic` 후 재실행."
            ) from e
        client = anthropic.Anthropic()  # 자격증명은 SDK 기본 해석(키 미보유)

    memo = {}

    def complete(prompt: str) -> str:
        if cache and prompt in memo:
            return memo[prompt]
        # 단문 분류라 thinking 불필요(opus-4-8은 thinking 미지정 시 off). JSON 한 줄만.
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        if cache:
            memo[prompt] = text
        return text

    return complete
