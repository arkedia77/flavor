/* ═══════════════════════════════════════════
   saju-engine.js — 십신/사주 계산 엔진
   lunar-javascript (6tail/lunar) 기반 만세력
   DNA + 사주 모드 공통
   한국 명리학 기준 KST 직접 사용
   ═══════════════════════════════════════════ */

/* ── 한자 → 한글 매핑 ── */
const _STEM_CK = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계'};
const _BRANCH_CK = {'子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'};
const _SIPSIN_CK = {'比肩':'비견','劫财':'겁재','劫財':'겁재','食神':'식신','伤官':'상관','傷官':'상관','偏财':'편재','偏財':'편재','正财':'정재','正財':'정재','七杀':'편관','七殺':'편관','正官':'정관','偏印':'편인','正印':'정인'};

function _toKr(ch) { return _STEM_CK[ch] || _BRANCH_CK[ch] || ch; }
function _sipsinKr(s) { return _SIPSIN_CK[s] || s; }

/* ── 기존 상수 (하위 호환) ── */
const STEMS = ["갑","을","병","정","무","기","경","신","임","계"];
const BRANCHES = ["자","축","인","묘","진","사","오","미","신","유","술","해"];

const STEM_ELEMENT   = {갑:"목",을:"목",병:"화",정:"화",무:"토",기:"토",경:"금",신:"금",임:"수",계:"수"};
const STEM_POLARITY  = {갑:"양",을:"음",병:"양",정:"음",무:"양",기:"음",경:"양",신:"음",임:"양",계:"음"};
const BRANCH_ELEMENT  = {자:"수",축:"토",인:"목",묘:"목",진:"토",사:"화",오:"화",미:"토",신:"금",유:"금",술:"토",해:"수"};
const BRANCH_POLARITY = {자:"양",축:"음",인:"양",묘:"음",진:"양",사:"음",오:"양",미:"음",신:"양",유:"음",술:"양",해:"음"};

const PRODUCES = {목:"화",화:"토",토:"금",금:"수",수:"목"};
const OVERCOMES = {목:"토",토:"수",수:"화",화:"금",금:"목"};

/* ── lunar 라이브러리 EightChar 가져오기 ── */
function _getEightChar(year, month, day, hour) {
  // 한국 명리학: KST 시간 그대로 사용
  var h = (hour !== null && hour !== undefined) ? parseInt(hour) : 12;
  var solar = Solar.fromYmdHms(year, month, day, h, 0, 0);
  return solar.getLunar().getEightChar();
}

/* DNA 모드: 6글자 (시주 없음) — 기본 시간 12시(정오) */
function calcPillars(year, month, day) {
  var ba = _getEightChar(year, month, day, 12);
  var ys = _toKr(ba.getYearGan());
  var yb = _toKr(ba.getYearZhi());
  var ms = _toKr(ba.getMonthGan());
  var mb = _toKr(ba.getMonthZhi());
  var ds = _toKr(ba.getDayGan());
  var db = _toKr(ba.getDayZhi());
  return { ys: ys, yb: yb, ms: ms, mb: mb, ds: ds, db: db };
}

/* 사주 모드: 8글자 (시주 포함) */
function calcPillarsFull(year, month, day, hour) {
  if (hour === null || hour === undefined) return calcPillars(year, month, day);
  var ba = _getEightChar(year, month, day, hour);
  var ys = _toKr(ba.getYearGan());
  var yb = _toKr(ba.getYearZhi());
  var ms = _toKr(ba.getMonthGan());
  var mb = _toKr(ba.getMonthZhi());
  var ds = _toKr(ba.getDayGan());
  var db = _toKr(ba.getDayZhi());
  var hs = _toKr(ba.getTimeGan());
  var hb = _toKr(ba.getTimeZhi());
  return { ys: ys, yb: yb, ms: ms, mb: mb, ds: ds, db: db, hs: hs, hb: hb };
}

/* ── 십신: lunar 라이브러리 결과 → 기존 분포 형식 ── */
function _buildSipsinDist(ba, includeHour) {
  var dist = {};
  ["비견","겁재","식신","상관","편재","정재","편관","정관","편인","정인"].forEach(function(n) { dist[n] = 0; });

  // 천간 십신 (년간, 월간 + 선택적 시간)
  var ganList = [
    _sipsinKr(ba.getYearShiShenGan()),
    _sipsinKr(ba.getMonthShiShenGan())
  ];
  if (includeHour) {
    ganList.push(_sipsinKr(ba.getTimeShiShenGan()));
  }
  ganList.forEach(function(s) { if (dist[s] !== undefined) dist[s]++; });

  // 지지 십신 (년지, 월지, 일지 + 선택적 시지)
  var zhiLists = [
    ba.getYearShiShenZhi(),
    ba.getMonthShiShenZhi(),
    ba.getDayShiShenZhi()
  ];
  if (includeHour) {
    zhiLists.push(ba.getTimeShiShenZhi());
  }
  zhiLists.forEach(function(arr) {
    if (arr && arr.length > 0) {
      // 지장간 본기만 카운트 — lunar 순서는 [본기, 중기, 여기] (index 0 = 본기).
      // 2026-07-12: arr[length-1](여기)로 읽던 버그 수정 — 서버 sipsin.py의
      // 2026-07-10 수정(arr[-1]→arr[0])과 동일 버그가 클라이언트에 남아 있었음
      var s = _sipsinKr(arr[0]);
      if (dist[s] !== undefined) dist[s]++;
    }
  });

  var dominant = "비견", maxCount = 0;
  Object.keys(dist).forEach(function(k) {
    if (dist[k] > maxCount) { maxCount = dist[k]; dominant = k; }
  });

  return { distribution: dist, dominant: dominant };
}

/* DNA 모드: 십신 분포 (6글자) */
function calcSipsin(year, month, day) {
  var ba = _getEightChar(year, month, day, 12);
  var ds = _toKr(ba.getDayGan());
  var dayEl = STEM_ELEMENT[ds];
  var dayPol = STEM_POLARITY[ds];
  var p = calcPillars(year, month, day);
  var result = _buildSipsinDist(ba, false);
  return { dayStem: ds, dayEl: dayEl, dayPol: dayPol, distribution: result.distribution, dominant: result.dominant, pillars: p };
}

/* 사주 모드: 십신 분포 (8글자, 시주 포함) */
function calcSipsinFull(year, month, day, hour) {
  var ba = _getEightChar(year, month, day, hour || 12);
  var ds = _toKr(ba.getDayGan());
  var dayEl = STEM_ELEMENT[ds];
  var dayPol = STEM_POLARITY[ds];
  var p = calcPillarsFull(year, month, day, hour);
  var includeHour = (hour !== null && hour !== undefined);
  var result = _buildSipsinDist(ba, includeHour);
  return { dayStem: ds, dayEl: dayEl, dayPol: dayPol, distribution: result.distribution, dominant: result.dominant, pillars: p };
}

/* ── 십신 → 9차원 innate 벡터 (표시용) ──
   서버 engines/saju_features.py SIPSIN_FLAVOR_MAP_V2 = 정본.
   여기 델타 값은 서버와 **정확히 일치**해야 함 (tests/test_lexicon_separation.py
   TestMapParity가 검사). 2026-07-12: 감사 이전 구맵 → V2 동기화.
   (구맵은 식신 social-/energetic- 등 감사에서 폐기한 델타를 표시하고 있었음)
   주의: 클라이언트 가중은 십신 count 기반 근사(서버는 궁성·지장간 가중) — 값은
   같아도 최종 innate는 근사치다. 정확 prior는 서버 saju_prior_9d가 정본. */
const SIPSIN_FLAVOR_MAP = {
  "비견": {adventurous:+0.05, comfort:+0.03, social:-0.05},
  "겁재": {social:+0.07, budget:+0.06, maximalist:+0.06, energetic:+0.05, urban:+0.05},
  "식신": {aesthetic:+0.07, comfort:+0.06, bitter:+0.05},
  "상관": {maximalist:+0.08, adventurous:+0.08, social:+0.04, aesthetic:+0.05, comfort:-0.05},
  "편재": {adventurous:+0.08, social:+0.07, urban:+0.06, budget:+0.06, comfort:-0.04},
  "정재": {comfort:+0.08, budget:-0.08, adventurous:-0.06, social:-0.04, urban:+0.03},
  "편관": {energetic:+0.08, adventurous:+0.06, maximalist:+0.05, urban:+0.04, comfort:-0.06},
  "정관": {urban:+0.06, comfort:+0.05, aesthetic:+0.04, maximalist:-0.06, adventurous:-0.05},
  "편인": {adventurous:+0.07, bitter:+0.06, aesthetic:+0.04, social:-0.06, urban:-0.03},
  "정인": {comfort:+0.07, bitter:+0.04, aesthetic:+0.03, maximalist:-0.05, budget:-0.03},
};

const DIMENSIONS = ["social","adventurous","aesthetic","comfort","budget","maximalist","energetic","urban","bitter"];

function sipsinToInnate(sipsinResult, amplify) {
  const innate = {};
  DIMENSIONS.forEach(d => innate[d] = 0.5);

  const dist = sipsinResult.distribution;
  const total = Object.values(dist).reduce((a, b) => a + b, 0);
  if (total === 0) return innate;

  Object.entries(dist).forEach(([name, count]) => {
    if (count === 0) return;
    const weight = count / total;
    const map = SIPSIN_FLAVOR_MAP[name] || {};
    Object.entries(map).forEach(([dim, val]) => {
      innate[dim] += val * weight;
    });
  });

  const amp = amplify || 5;
  DIMENSIONS.forEach(d => {
    const delta = innate[d] - 0.5;
    innate[d] = Math.max(0.1, Math.min(0.9, 0.5 + delta * amp));
  });

  return innate;
}

/* ── 일간 페르소나 ──
   어휘 분리 (2026-07-12): 9차원 설문 어휘(config/dimension_lexicon.json) 사용 금지.
   서버 engines/persona.py와 동일해야 함 (tests/test_lexicon_separation.py가 패리티 검사) */
const DAY_MASTER_PERSONA = {
  "갑": {name:"큰 나무의 개척자", emoji:"🌲", element:"목", vibe:"가장 먼저 땅을 뚫고 하늘로 뻗는 기세"},
  "을": {name:"덩굴의 적응가", emoji:"🌿", element:"목", vibe:"어디서든 제 자리를 찾아내는 유연함"},
  "병": {name:"태양의 무대인", emoji:"☀️", element:"화", vibe:"무대 한가운데서 가장 밝게 타오르는 존재감"},
  "정": {name:"촛불의 이야기꾼", emoji:"🕯️", element:"화", vibe:"어둠이 짙을수록 또렷해지는 은은한 불빛"},
  "무": {name:"대지의 중심축", emoji:"🏔️", element:"토", vibe:"산맥처럼 흔들림 없는 묵직한 중심"},
  "기": {name:"정원의 일꾼", emoji:"🌾", element:"토", vibe:"무엇을 심어도 자라나게 하는 손길"},
  "경": {name:"강철의 대장장이", emoji:"⚔️", element:"금", vibe:"불에 달구고 두드려 벼려낸 단단한 기준"},
  "신": {name:"보석의 세공사", emoji:"💎", element:"금", vibe:"원석 속에서 빛을 골라내는 눈"},
  "임": {name:"바다의 항해사", emoji:"🌊", element:"수", vibe:"수평선 너머를 향해 쉬지 않고 흐르는 물길"},
  "계": {name:"이슬의 관찰자", emoji:"💧", element:"수", vibe:"새벽 안개처럼 스며들어 속을 꿰뚫는 직관"},
};

const DOMAIN_EMOJI = { '커피':'☕','향수':'🌸','음악':'🎵','식당':'🍽️','운동':'🏃','여행':'✈️','패션':'👗','인테리어':'🏠' };
