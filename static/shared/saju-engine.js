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
      // 지장간의 첫 번째(본기)만 카운트 — 기존 로직과 일관성 유지
      var s = _sipsinKr(arr[arr.length - 1]);
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

/* ── 십신 → 9차원 innate 벡터 ── */
const SIPSIN_FLAVOR_MAP = {
  "비견": {adventurous:+0.06, energetic:+0.04, comfort:-0.04},
  "겁재": {social:+0.08, energetic:+0.06, budget:+0.04},
  "식신": {aesthetic:+0.08, comfort:+0.04, bitter:+0.04},
  "상관": {maximalist:+0.08, adventurous:+0.06, aesthetic:+0.04},
  "편재": {social:+0.06, budget:+0.08, urban:+0.04},
  "정재": {comfort:+0.08, budget:-0.06, urban:+0.04},
  "편관": {energetic:+0.08, urban:+0.06, maximalist:+0.04},
  "정관": {comfort:+0.06, urban:+0.06, aesthetic:+0.04},
  "편인": {adventurous:+0.08, aesthetic:+0.06, social:-0.04},
  "정인": {comfort:+0.08, social:+0.04, aesthetic:+0.04},
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

/* ── 일간 페르소나 ── */
const DAY_MASTER_PERSONA = {
  "갑": {name:"큰 나무의 개척자", emoji:"🌲", element:"목", vibe:"새로운 길을 만드는 사람"},
  "을": {name:"덩굴의 적응가", emoji:"🌿", element:"목", vibe:"어디서든 자리를 잡는 유연한 감각"},
  "병": {name:"태양의 무대인", emoji:"☀️", element:"화", vibe:"주목받을 때 빛나는 에너지"},
  "정": {name:"촛불의 감성가", emoji:"🕯️", element:"화", vibe:"은은하지만 깊은 감각의 소유자"},
  "무": {name:"대지의 중심축", emoji:"🏔️", element:"토", vibe:"흔들리지 않는 안정감"},
  "기": {name:"정원의 큐레이터", emoji:"🌾", element:"토", vibe:"사소한 것도 아름답게 가꾸는 손길"},
  "경": {name:"강철의 완벽주의자", emoji:"⚔️", element:"금", vibe:"타협 없는 기준, 날카로운 취향"},
  "신": {name:"보석의 감식가", emoji:"💎", element:"금", vibe:"정제된 아름다움을 알아보는 눈"},
  "임": {name:"바다의 탐험가", emoji:"🌊", element:"수", vibe:"끝없이 새로운 것을 향해 흐르는 호기심"},
  "계": {name:"이슬의 관찰자", emoji:"💧", element:"수", vibe:"조용히 스며들어 본질을 꿰뚫는 직관"},
};

const DOMAIN_EMOJI = { '커피':'☕','향수':'🌸','음악':'🎵','식당':'🍽️','운동':'🏃','여행':'✈️','패션':'👗','인테리어':'🏠' };
