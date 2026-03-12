"""프로필 → 취향 타입 분류"""


def get_personality_type(profile: dict) -> dict:
    """프로필 → 취향 타입명 + 설명"""
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
        return {
            "type": "충동적 탐험가",
            "emoji": "🔥",
            "tagline": "계획 없이 떠나도 어딘가엔 도착한다",
            "detail": "당신 주변 사람들은 이미 알고 있습니다. 다음 여행지는 이미 마음속에 있다는 걸."
        }
    elif ae > 0.65 and mx < 0.4 and ur > 0.55:
        return {
            "type": "감각적 미니멀리스트",
            "emoji": "🖤",
            "tagline": "적게 가질수록 더 잘 보인다",
            "detail": "공간이든 옷장이든, 당신이 고른 것들엔 이유가 있습니다. 그게 눈에 띄는 이유고요."
        }
    elif bi > 0.6 and ae > 0.55 and bu > 0.55:
        return {
            "type": "스페셜티 커피 스노브",
            "emoji": "☕",
            "tagline": "원산지 모르면 그건 그냥 음료다",
            "detail": "카페 들어가면 먼저 원두 칠판부터 확인하는 사람. 맞죠?"
        }
    elif s > 0.6 and en > 0.55 and ur > 0.55:
        return {
            "type": "도시의 에너지 덩어리",
            "emoji": "⚡",
            "tagline": "쉬는 것도 계획이 있어야 한다",
            "detail": "주말에 약속 없으면 오히려 불안한 타입. 이미 다음 주 캘린더 절반 채운 거 알고 있어요."
        }
    elif co > 0.65 and s > 0.55:
        return {
            "type": "동네 사랑방 단골",
            "emoji": "🏡",
            "tagline": "단골집 사장님이 내 이름 아는 삶",
            "detail": "익숙한 사람, 익숙한 공간, 익숙한 메뉴. 그 안정감이 사실 제일 사치스러운 겁니다."
        }
    elif mx > 0.65 and ae > 0.55:
        return {
            "type": "취향 수집가",
            "emoji": "✨",
            "tagline": "모든 물건엔 사연이 있어야 한다",
            "detail": "공간 보면 그 사람 안다고 했습니다. 당신 방은 지금 몇 가지 이야기를 하고 있나요?"
        }
    elif av > 0.55 and ae > 0.6:
        return {
            "type": "감성 미식 탐험가",
            "emoji": "🍽️",
            "tagline": "맛집은 발로 찾는 거다",
            "detail": "메뉴판에 모르는 이름이 많을수록 기대되는 타입. 혼밥도 이벤트입니다."
        }
    elif ur < 0.4 and co > 0.6:
        return {
            "type": "자연 속 힐링러",
            "emoji": "🌿",
            "tagline": "도시가 줄 수 없는 게 있다",
            "detail": "창문 밖 나무 한 그루가 힘이 되는 사람. 번잡함 대신 깊이를 선택합니다."
        }
    elif s < 0.4 and ae > 0.6:
        return {
            "type": "혼자가 편한 감성인",
            "emoji": "🎧",
            "tagline": "나만의 세계가 있다는 건 사치가 아니다",
            "detail": "카페에 혼자 앉아서 2시간이 금방 가는 사람. 그게 충전입니다."
        }
    else:
        return {
            "type": "균형잡힌 취향인",
            "emoji": "🌀",
            "tagline": "튀지 않지만 어디서나 어울린다",
            "detail": "유행에 휩쓸리지 않고 자기 기준이 있는 사람. 그게 생각보다 드뭅니다."
        }
