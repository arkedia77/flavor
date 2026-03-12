"""8개 도메인별 추천 (규칙 기반)"""

from config import HIGH, LOW, MHI, MLO


def recommend_coffee(profile: dict) -> dict:
    bitter  = profile.get("bitter", 0.5)
    budget  = profile.get("budget", 0.5)
    comfort = profile.get("comfort", 0.5)
    if bitter > 0.65:
        if budget > 0.6:
            return {"item": "스페셜티 싱글오리진 핸드드립", "reason": "진하고 복잡한 맛을 즐기는 미식가형",
                    "description": "원두 농장 이름까지 외우는 당신, 바리스타도 긴장합니다"}
        return {"item": "에스프레소·아이스 아메리카노", "reason": "강하고 깔끔한 커피를 선호하는 타입",
                "description": "내 몸의 60%는 아메리카노로 이루어져 있습니다"}
    elif bitter < 0.35:
        if comfort > 0.65:
            return {"item": "카페라떼·바닐라라떼", "reason": "부드럽고 달콤한, 언제나 변함없이 믿는 메뉴",
                    "description": "커피는 핑계, 진짜 목적은 우유 (이것도 틀린 말은 아님)"}
        return {"item": "달달한 라떼·플랫화이트", "reason": "부드럽고 달콤한 풍미를 즐기는 타입",
                "description": "디카페인도 '맛있는 커피'라 부르는 낙천적인 타입"}
    else:
        if budget > MHI:
            if comfort < LOW:
                return {"item": "스페셜티 콜드브루·블랙워터", "reason": "새로운 커피 경험을 찾는 감각적인 탐험가",
                        "description": "카페 메뉴판을 위에서 아래로 순서대로 정복 중인 사람"}
            return {"item": "오트밀크 라떼·콜드브루", "reason": "트렌디하고 감각적인 카페 경험을 선호",
                    "description": "인스타 올리기 전에 한 모금 마셔보는 진짜 감식가"}
        elif comfort > HIGH:
            return {"item": "따뜻한 아메리카노·단골 블렌드", "reason": "매일 같은 메뉴에서 안정감을 찾는 타입",
                    "description": "사장님이 보이면 이미 주문이 들어가 있는 그 메뉴"}
        return {"item": "아이스 라떼·아메리카노", "reason": "무난하지만 믿을 수 있는 클래식한 취향",
                "description": "고민 없이 고르는 게 이미 고수의 경지입니다"}


def recommend_perfume(profile: dict) -> dict:
    aesthetic   = profile.get("aesthetic", 0.5)
    maximalist  = profile.get("maximalist", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if maximalist < LOW and aesthetic > 0.5:
        return {"item": "머스크·클린 미니멀 향", "reason": "정제되고 세련된 감각, 은은한 존재감을 선호",
                "description": "없는 듯 있는 향, 그게 제일 어렵고 제일 세련된 겁니다"}
    elif maximalist > HIGH:
        return {"item": "오리엔탈·우디 레이어드 향", "reason": "풍부하고 개성 강한 향으로 존재감을 표현",
                "description": "엘리베이터에서 한 번쯤 '무슨 향이에요?' 듣는 그 사람"}
    elif adventurous > MHI:
        return {"item": "니치 퍼퓸·아방가르드 향", "reason": "남들과 다른 독특한 향기에 끌리는 탐험가 취향",
                "description": "브랜드 이름 10번 쳐도 못 찾는 향, 그게 좋은 이유입니다"}
    elif comfort > HIGH:
        return {"item": "클래식 시그니처 향·익숙한 우디 향", "reason": "오래 써온 익숙한 향이 주는 안정감을 선호",
                "description": "10년째 같은 향수, 그게 이미 당신의 시그니처입니다"}
    else:
        return {"item": "시트러스·그린 플로럴", "reason": "청량하고 자연스러운 향으로 편안한 인상",
                "description": "봄날 공원 벤치 옆에 앉은 사람 같은 향, 기분 좋아지는 타입"}


def recommend_music(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    aesthetic = profile.get("aesthetic", 0.5)
    comfort   = profile.get("comfort", 0.5)
    if energetic > HIGH and social > MHI:
        return {"item": "업템포 팝·하우스·EDM", "reason": "활동적이고 사교적인 에너지에 맞는 비트",
                "description": "AirPods 끼는 순간 자동으로 걸음이 빨라지는 타입"}
    elif energetic > HIGH:
        return {"item": "힙합·트랩·록", "reason": "강한 에너지를 혼자서도 즐기는 집중형 취향",
                "description": "이어폰 빼라는 말 세 번째 듣고 있는 중 (못 들었음)"}
    elif aesthetic > MHI and energetic < 0.5:
        return {"item": "재즈·보사노바·어쿠스틱", "reason": "감각적이고 여유로운 무드를 즐기는 타입",
                "description": "카페 플레이리스트 운영하면 무조건 대박날 취향"}
    elif energetic < LOW:
        return {"item": "로파이 힙합·앰비언트", "reason": "조용하고 집중력 있는 배경음악 선호",
                "description": "비 오는 날 창문 보며 일하는 게 인생 최고 세팅"}
    elif comfort > HIGH:
        return {"item": "잔잔한 팝·어쿠스틱 발라드", "reason": "편안하고 익숙한 멜로디, 마음이 쉬어가는 음악",
                "description": "가사가 오늘 내 일기인 것 같을 때가 종종 있는 타입"}
    else:
        return {"item": "인디 팝·얼터너티브 R&B", "reason": "감성과 에너지 사이에서 균형 잡힌 취향",
                "description": "유튜브 알고리즘이 당신을 완벽하게 파악하고 있음"}


def recommend_restaurant(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    budget      = profile.get("budget", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if adventurous > 0.65:
        return {"item": "에스닉·퓨전 레스토랑", "reason": "새로운 맛과 문화를 탐험하는 미식 모험가",
                "description": "메뉴판에 모르는 단어 많을수록 더 기대되는 타입"}
    elif aesthetic > 0.65 and budget > 0.55:
        return {"item": "분위기 좋은 파인다이닝·비스트로", "reason": "음식만큼 공간과 경험을 중요하게 여기는 타입",
                "description": "음식 사진보다 공간 사진이 더 많은 갤러리의 주인"}
    elif budget < 0.35:
        return {"item": "로컬 맛집·가성비 한식", "reason": "진짜 맛을 아는 가성비 맛집 전문가",
                "description": "줄 서서 먹는 건 무조건 이유가 있다고 믿는 사람"}
    elif comfort > 0.65:
        return {"item": "단골 한식집·동네 맛집", "reason": "익숙하고 편안한 곳에서 제대로 된 한 끼를 즐기는 타입",
                "description": "사장님이 반겨주는 그 집, 그 자리, 그 메뉴가 최고"}
    else:
        return {"item": "이탈리안·모던 한식", "reason": "익숙하면서도 수준 있는 식사를 즐기는 타입",
                "description": "분위기도 맛도, 딱 기대한 만큼 나오는 식당이 제일 좋은 타입"}


def recommend_exercise(profile: dict) -> dict:
    energetic = profile.get("energetic", 0.5)
    social    = profile.get("social", 0.5)
    urban     = profile.get("urban", 0.5)
    comfort   = profile.get("comfort", 0.5)
    if energetic > 0.7:
        return {"item": "크로스핏·HIIT·복싱", "reason": "강렬한 자극과 도전을 즐기는 고강도 운동 타입",
                "description": "운동 후 기절 직전이 오히려 쾌감인 사람, 맞죠?"}
    elif energetic > 0.5 and urban < 0.4:
        return {"item": "등산·트레일 러닝·사이클", "reason": "자연 속에서 활동적으로 움직이는 아웃도어 타입",
                "description": "정상 인증샷 없으면 다녀온 게 아니라는 신념의 소유자"}
    elif social > 0.6 and energetic > 0.4:
        return {"item": "필라테스·클라이밍·댄스", "reason": "함께하며 성장하는 커뮤니티 운동을 선호",
                "description": "선생님 이름도 외우고 단골 자리도 있는 찐 단골"}
    elif energetic < 0.35:
        return {"item": "요가·스트레칭·산책", "reason": "몸과 마음의 균형을 챙기는 마음챙김형 운동",
                "description": "오늘 운동? 계단 탔습니다 (이것도 운동이라고 진심으로 믿음)"}
    elif comfort > 0.65:
        return {"item": "홈트·수영·꾸준한 헬스", "reason": "익숙한 루틴으로 꾸준히 이어가는 안정형 운동",
                "description": "3년째 같은 루틴, 그 꾸준함이 사실 제일 무서운 거예요"}
    else:
        return {"item": "수영·헬스·러닝", "reason": "꾸준하고 안정적인 루틴 운동을 선호하는 타입",
                "description": "특별하진 않지만 꾸준함이 특별함을 만드는 타입"}


def recommend_travel(profile: dict) -> dict:
    adventurous = profile.get("adventurous", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    urban       = profile.get("urban", 0.5)
    budget      = profile.get("budget", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if adventurous > 0.7:
        return {"item": "동남아 배낭여행·중남미 트레킹", "reason": "예측 불가능한 모험을 즐기는 진짜 탐험가",
                "description": "귀국 비행기 안에서 다음 여행지 검색하는 사람"}
    elif aesthetic > 0.65 and urban > 0.5:
        return {"item": "유럽 예술·건축 도시 투어", "reason": "아름다운 것을 찾아 떠나는 감성 여행자",
                "description": "미술관 입장 전부터 굿즈숍 뭐 살지 미리 찜해두는 타입"}
    elif urban < 0.35:
        return {"item": "제주·규슈·뉴질랜드 자연 여행", "reason": "도시를 벗어나 자연 속 힐링을 원하는 타입",
                "description": "숙소 창문 뷰가 여행의 절반이라고 생각하는 사람"}
    elif budget > 0.65:
        return {"item": "럭셔리 리조트·몰디브·발리", "reason": "완벽한 휴식과 프리미엄 경험을 추구하는 타입",
                "description": "체크인부터 체크아웃까지 풀서비스가 진짜 여행이라는 신봉자"}
    elif comfort > 0.65:
        return {"item": "일본·대만 꼼꼼 자유여행", "reason": "안전하고 친숙한 환경에서 여유 있게 즐기는 타입",
                "description": "엑셀 여행 계획표에 여유시간까지 잡아두는 완벽주의 여행자"}
    else:
        return {"item": "일본 소도시·대만·포르투갈", "reason": "편안하면서도 감성적인 감각 여행을 선호",
                "description": "구글 지도 즐겨찾기가 500개는 넘었을 것 같은 사람"}


def recommend_fashion(profile: dict) -> dict:
    maximalist  = profile.get("maximalist", 0.5)
    aesthetic   = profile.get("aesthetic", 0.5)
    budget      = profile.get("budget", 0.5)
    adventurous = profile.get("adventurous", 0.5)
    comfort     = profile.get("comfort", 0.5)
    if maximalist < 0.3:
        return {"item": "미니멀·모노톤 룩", "reason": "군더더기 없는 정제된 스타일로 세련미를 표현",
                "description": "옷이 10벌인데 어떻게 매일 달라 보이냐는 말 자주 듣는 타입"}
    elif maximalist > 0.7 and adventurous > 0.5:
        return {"item": "스트리트·빈티지 레이어드", "reason": "개성 강한 믹스매치로 눈에 띄는 스타일링",
                "description": "세컨핸드 샵 직원이 얼굴을 먼저 알아보는 단골"}
    elif aesthetic > MHI and budget > MHI:
        return {"item": "컨템포러리·디자이너 캐주얼", "reason": "감각적이고 수준 있는 아이템에 투자하는 타입",
                "description": "가격표 안 보는 척하면서 사실 다 보는 그런 타입 (우리 다 알고 있음)"}
    elif comfort > HIGH:
        return {"item": "편안한 캐주얼·슬랙스 무드", "reason": "편안함이 최우선, 오래 입어도 질리지 않는 기본",
                "description": "3초 코디인데 왜 이렇게 잘 입은 것처럼 보이냐, 비결이 뭐예요"}
    elif maximalist > 0.5:
        return {"item": "내추럴·보헤미안 스타일", "reason": "편안하면서도 감성적인 무드를 즐기는 타입",
                "description": "린넨 소재 들어가면 일단 손부터 가는 사람"}
    else:
        return {"item": "스마트 캐주얼·트렌디 베이직", "reason": "무난하지만 트렌드를 놓치지 않는 스타일",
                "description": "유행 따라가되 휩쓸리지 않는 균형 감각, 이게 제일 어려운 겁니다"}


def recommend_interior(profile: dict) -> dict:
    maximalist = profile.get("maximalist", 0.5)
    urban      = profile.get("urban", 0.5)
    aesthetic  = profile.get("aesthetic", 0.5)
    budget     = profile.get("budget", 0.5)
    comfort    = profile.get("comfort", 0.5)
    if maximalist < 0.3 and urban > 0.5:
        return {"item": "스칸디나비안·재패니즈 미니멀", "reason": "깔끔한 여백과 기능적 아름다움을 추구",
                "description": "물건 하나 살 때 하나 버리는 원칙, 실천하는 사람"}
    elif maximalist > HIGH and aesthetic > 0.5:
        return {"item": "맥시멀리스트·보헤미안 스타일", "reason": "다양한 오브제와 텍스처로 개성 넘치는 공간",
                "description": "어디서 구했냐는 질문을 제일 좋아하는 공간 큐레이터"}
    elif urban < LOW:
        return {"item": "우드톤·내추럴 소재 인테리어", "reason": "자연 소재로 따뜻하고 편안한 공간 구성",
                "description": "러그 하나 깔았을 뿐인데 공간이 완전히 달라지는 마법 아시죠?"}
    elif budget > HIGH and aesthetic > MHI:
        return {"item": "모던 럭셔리·하이엔드 인테리어", "reason": "퀄리티 있는 소재와 감각적인 조명을 중시",
                "description": "조명 교체에 100만 원 써도 후회 없는, 공간 투자 신봉자"}
    elif comfort > HIGH:
        return {"item": "코지 홈·패브릭 소재 따뜻한 공간", "reason": "홈카페 감성, 쉬고 싶어지는 아늑한 공간",
                "description": "손님이 '나 여기서 살고 싶다'는 말 자주 듣는 집 주인"}
    else:
        return {"item": "모던 빈티지·인더스트리얼 믹스", "reason": "트렌디하면서 개성 있는 공간을 선호",
                "description": "새것 같은 빈티지, 빈티지 같은 새것, 그 경계 어딘가"}


def run_all_domains(profile: dict) -> dict:
    return {
        "커피": recommend_coffee(profile),
        "향수": recommend_perfume(profile),
        "음악": recommend_music(profile),
        "식당": recommend_restaurant(profile),
        "운동": recommend_exercise(profile),
        "여행": recommend_travel(profile),
        "패션": recommend_fashion(profile),
        "인테리어": recommend_interior(profile),
    }
