"""프로필 → 취향 타입 분류 (Phase 2: L1/L2 + 9D 하이브리드)

L1: 일간 기반 10타입 (saju_detail.day_master)
L2: 격국×강약 기반 세부 타입 (saju_detail.type_code)
L3: 9차원 프로필 기반 취향 타입 (기존 호환)
"""

from engines.saju_tables import DAY_MASTER_TYPES


# ──────────────────────────────────────────────
# L2 타입: 격국(10) × 강약(2) = 20 조합
# ──────────────────────────────────────────────

L2_TYPES = {
    # 비겁격 계열 — 자아 강한 독립형
    "비견격_강": {"name": "주도형 독립인", "tagline": "내 길은 내가 정한다",
                 "trait": "자기 확신이 강하고 독립적, 취향도 확고함"},
    "비견격_약": {"name": "협력형 탐색자", "tagline": "함께할 때 더 나다운",
                 "trait": "자아는 있지만 유연하게 타인 취향도 수용"},
    "겁재격_강": {"name": "경쟁적 실행가", "tagline": "일단 해보는 거다",
                 "trait": "과감하고 도전적, 트렌드를 앞서감"},
    "겁재격_약": {"name": "전략적 관망자", "tagline": "기다릴 줄 아는 사람이 이긴다",
                 "trait": "신중하게 판단 후 행동, 실패 없는 선택"},

    # 식상격 계열 — 표현과 창조
    "식신격_강": {"name": "감각적 미식가", "tagline": "맛있는 게 정의다",
                 "trait": "오감이 발달, 먹고 즐기는 데 재능이 있음"},
    "식신격_약": {"name": "조용한 감식가", "tagline": "말은 적지만 고르는 건 정확하다",
                 "trait": "내면의 기준이 높고 취향이 정교함"},
    "상관격_강": {"name": "파격적 창조자", "tagline": "기존 틀은 깨라고 있는 거다",
                 "trait": "독창적이고 개성 강함, 남들과 다른 선택"},
    "상관격_약": {"name": "섬세한 표현가", "tagline": "디테일에 신이 산다",
                 "trait": "예민한 감각으로 섬세한 취향을 발휘"},

    # 재성격 계열 — 실용과 투자
    "편재격_강": {"name": "대범한 투자가", "tagline": "좋은 건 가격표를 안 본다",
                 "trait": "과감한 소비, 경험에 투자하는 타입"},
    "편재격_약": {"name": "실속형 큐레이터", "tagline": "가성비의 끝판왕",
                 "trait": "가치 대비 효용을 정확히 계산"},
    "정재격_강": {"name": "프리미엄 수집가", "tagline": "좋은 건 하나만 오래 쓴다",
                 "trait": "검증된 고품질에 꾸준히 투자"},
    "정재격_약": {"name": "꼼꼼한 비교자", "tagline": "리뷰 50개는 봐야 산다",
                 "trait": "정보를 철저히 비교하고 합리적으로 선택"},

    # 관성격 계열 — 규율과 체계
    "편관격_강": {"name": "카리스마 리더", "tagline": "결정은 빠르게, 후회는 없다",
                 "trait": "강한 추진력, 트렌드를 이끄는 타입"},
    "편관격_약": {"name": "성실한 탐구자", "tagline": "꾸준함이 답이다",
                 "trait": "체계적이고 꾸준, 검증된 것을 선호"},
    "정관격_강": {"name": "세련된 클래식", "tagline": "격식이 있되 딱딱하지 않게",
                 "trait": "품격 있는 취향, 클래식에 현대적 감각"},
    "정관격_약": {"name": "신중한 수호자", "tagline": "변하지 않는 것의 가치를 안다",
                 "trait": "전통과 안정을 선호, 검증된 취향"},

    # 인성격 계열 — 지적 탐구
    "편인격_강": {"name": "독창적 사유가", "tagline": "남들이 안 가는 길이 더 재밌다",
                 "trait": "독특하고 개성 넘치는 취향, 마이너 선호"},
    "편인격_약": {"name": "깊이 있는 관찰자", "tagline": "겉보다 속이 중요하다",
                 "trait": "본질을 파고드는 취향, 깊이를 중시"},
    "정인격_강": {"name": "지적 큐레이터", "tagline": "아는 만큼 즐긴다",
                 "trait": "지식 기반 취향, 배경과 스토리를 중시"},
    "정인격_약": {"name": "감성적 수용자", "tagline": "느끼는 대로 따라간다",
                 "trait": "직관적이고 감성적, 분위기에 민감"},
}


# ──────────────────────────────────────────────
# L3: 9차원 프로필 기반 취향 키워드 (기존 호환)
# ──────────────────────────────────────────────

def _get_flavor_archetype(profile: dict) -> dict:
    """9차원 프로필 → 취향 아키타입 (기존 get_personality_type 로직 유지)"""
    s  = profile.get("social", 0.5)
    av = profile.get("adventurous", 0.5)
    ae = profile.get("aesthetic", 0.5)
    co = profile.get("comfort", 0.5)
    bu = profile.get("budget", 0.5)
    mx = profile.get("maximalist", 0.5)
    en = profile.get("energetic", 0.5)
    ur = profile.get("urban", 0.5)
    bi = profile.get("bitter", 0.5)

    if av > 0.65 and en > 0.6:
        return {"type": "충동적 탐험가", "emoji": "🔥",
                "tagline": "계획 없이 떠나도 어딘가엔 도착한다",
                "detail": "당신 주변 사람들은 이미 알고 있습니다. 다음 여행지는 이미 마음속에 있다는 걸."}
    elif ae > 0.65 and mx < 0.4 and ur > 0.55:
        return {"type": "감각적 미니멀리스트", "emoji": "🖤",
                "tagline": "적게 가질수록 더 잘 보인다",
                "detail": "공간이든 옷장이든, 당신이 고른 것들엔 이유가 있습니다. 그게 눈에 띄는 이유고요."}
    elif bi > 0.6 and ae > 0.55 and bu > 0.55:
        return {"type": "스페셜티 커피 스노브", "emoji": "☕",
                "tagline": "원산지 모르면 그건 그냥 음료다",
                "detail": "카페 들어가면 먼저 원두 칠판부터 확인하는 사람. 맞죠?"}
    elif s > 0.6 and en > 0.55 and ur > 0.55:
        return {"type": "도시의 에너지 덩어리", "emoji": "⚡",
                "tagline": "쉬는 것도 계획이 있어야 한다",
                "detail": "주말에 약속 없으면 오히려 불안한 타입. 이미 다음 주 캘린더 절반 채운 거 알고 있어요."}
    elif co > 0.65 and s > 0.55:
        return {"type": "동네 사랑방 단골", "emoji": "🏡",
                "tagline": "단골집 사장님이 내 이름 아는 삶",
                "detail": "익숙한 사람, 익숙한 공간, 익숙한 메뉴. 그 안정감이 사실 제일 사치스러운 겁니다."}
    elif mx > 0.65 and ae > 0.55:
        return {"type": "취향 수집가", "emoji": "✨",
                "tagline": "모든 물건엔 사연이 있어야 한다",
                "detail": "공간 보면 그 사람 안다고 했습니다. 당신 방은 지금 몇 가지 이야기를 하고 있나요?"}
    elif av > 0.55 and ae > 0.6:
        return {"type": "감성 미식 탐험가", "emoji": "🍽️",
                "tagline": "맛집은 발로 찾는 거다",
                "detail": "메뉴판에 모르는 이름이 많을수록 기대되는 타입. 혼밥도 이벤트입니다."}
    elif ur < 0.4 and co > 0.6:
        return {"type": "자연 속 힐링러", "emoji": "🌿",
                "tagline": "도시가 줄 수 없는 게 있다",
                "detail": "창문 밖 나무 한 그루가 힘이 되는 사람. 번잡함 대신 깊이를 선택합니다."}
    elif s < 0.4 and ae > 0.6:
        return {"type": "혼자가 편한 감성인", "emoji": "🎧",
                "tagline": "나만의 세계가 있다는 건 사치가 아니다",
                "detail": "카페에 혼자 앉아서 2시간이 금방 가는 사람. 그게 충전입니다."}
    else:
        return {"type": "균형잡힌 취향인", "emoji": "🌀",
                "tagline": "튀지 않지만 어디서나 어울린다",
                "detail": "유행에 휩쓸리지 않고 자기 기준이 있는 사람. 그게 생각보다 드뭅니다."}


# ──────────────────────────────────────────────
# 통합 타입 시스템
# ──────────────────────────────────────────────

def get_personality_type(profile: dict, saju_detail: dict = None) -> dict:
    """프로필 + 사주 상세 → 통합 취향 타입

    Args:
        profile: 9차원 블렌드 프로필
        saju_detail: calc_saju()의 saju_detail (Phase 1). None이면 L3만 반환 (하위호환)

    Returns:
        dict: type, emoji, tagline, detail + (L1, L2 if saju_detail)
    """
    # L3: 기존 9차원 기반 아키타입 (항상 반환)
    result = _get_flavor_archetype(profile)

    if saju_detail is None:
        return result

    # L1: 일간 기반 (10종)
    day_master = saju_detail["day_master"]
    result["L1"] = {
        "name": day_master["type"]["name"],
        "emoji": day_master["type"]["emoji"],
        "stem": day_master["stem"],
        "element": day_master["type"]["element"],
    }

    # L2: 격국×강약 기반 (20종)
    type_code = saju_detail["type_code"]
    # type_code = "경_편관격_약" → geokguk_key = "편관격_약"
    parts = type_code.split("_", 1)
    geokguk_key = parts[1] if len(parts) > 1 else type_code

    l2_info = L2_TYPES.get(geokguk_key, {
        "name": "탐색 중인 취향인",
        "tagline": "아직 정의되지 않은 독특한 조합",
        "trait": "당신만의 고유한 취향 패턴을 가지고 있습니다",
    })

    result["L2"] = {
        "type_code": type_code,
        "name": l2_info["name"],
        "tagline": l2_info["tagline"],
        "trait": l2_info["trait"],
        "geokguk": saju_detail["geokguk"],
        "strength": saju_detail["strength_label"],
    }

    return result
