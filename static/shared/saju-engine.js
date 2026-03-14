/* ═══════════════════════════════════════════
   saju-engine.js — 십신/사주 계산 엔진
   DNA + 사주 모드 공통
   ═══════════════════════════════════════════ */

const STEMS = ["갑","을","병","정","무","기","경","신","임","계"];
const BRANCHES = ["자","축","인","묘","진","사","오","미","신","유","술","해"];

const STEM_ELEMENT   = {갑:"목",을:"목",병:"화",정:"화",무:"토",기:"토",경:"금",신:"금",임:"수",계:"수"};
const STEM_POLARITY  = {갑:"양",을:"음",병:"양",정:"음",무:"양",기:"음",경:"양",신:"음",임:"양",계:"음"};
const BRANCH_ELEMENT  = {자:"수",축:"토",인:"목",묘:"목",진:"토",사:"화",오:"화",미:"토",신:"금",유:"금",술:"토",해:"수"};
const BRANCH_POLARITY = {자:"양",축:"음",인:"양",묘:"음",진:"양",사:"음",오:"양",미:"음",신:"양",유:"음",술:"양",해:"음"};

const PRODUCES = {목:"화",화:"토",토:"금",금:"수",수:"목"};
const OVERCOMES = {목:"토",토:"수",수:"화",화:"금",금:"목"};

function getSipsin(dayEl, dayPol, tEl, tPol) {
  const samePol = dayPol === tPol;
  if (tEl === dayEl) return samePol ? "비견" : "겁재";
  if (tEl === PRODUCES[dayEl]) return samePol ? "식신" : "상관";
  if (tEl === OVERCOMES[dayEl]) return samePol ? "편재" : "정재";
  if (dayEl === PRODUCES[tEl]) return samePol ? "편인" : "정인";
  if (dayEl === OVERCOMES[tEl]) return samePol ? "편관" : "정관";
  return "비견";
}

function calcJDN(year, month, day) {
  const a = Math.floor((14 - month) / 12);
  const y = year + 4800 - a;
  const m = month + 12 * a - 3;
  return day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
}

/* DNA 모드: 6글자 (시주 없음) */
function calcPillars(year, month, day) {
  const ys = STEMS[(year - 4 + 1000) % 10];
  const yb = BRANCHES[(year - 4 + 1200) % 12];
  const ysIdx = ((year - 4) % 10 + 10) % 10;
  const baseMap = [2,4,6,8,0,2,4,6,8,0];
  const ms = STEMS[(baseMap[ysIdx] + month - 1) % 10];
  const mb = BRANCHES[(month + 1) % 12];
  const jdn = calcJDN(year, month, day);
  const ds = STEMS[((jdn % 10) + 10) % 10];
  const db = BRANCHES[((jdn % 12) + 12) % 12];
  return { ys, yb, ms, mb, ds, db };
}

/* 사주 모드: 시간 → 지지 (12시진) */
function hourToBranch(hour) {
  if (hour === null || hour === undefined) return null;
  const h = parseInt(hour);
  const map = [[23,0,'자'],[1,2,'축'],[3,4,'인'],[5,6,'묘'],[7,8,'진'],[9,10,'사'],
               [11,12,'오'],[13,14,'미'],[15,16,'신'],[17,18,'유'],[19,20,'술'],[21,22,'해']];
  for (const [s, e, br] of map) {
    if (s <= e) { if (h >= s && h <= e) return br; }
    else { if (h >= s || h <= e) return br; }
  }
  return '오';
}

/* 사주 모드: 8글자 (시주 포함) */
function calcPillarsFull(year, month, day, hour) {
  const base = calcPillars(year, month, day);
  if (hour === null || hour === undefined) return base;

  const hb = hourToBranch(hour);
  const dsIdx = STEMS.indexOf(base.ds);
  const startMap = [0,2,4,6,8,0,2,4,6,8];
  const hbIdx = BRANCHES.indexOf(hb);
  const hs = STEMS[(startMap[dsIdx] + hbIdx) % 10];

  return { ...base, hs, hb };
}

/* DNA 모드: 십신 분포 (6글자) */
function calcSipsin(year, month, day) {
  const p = calcPillars(year, month, day);
  const dayEl = STEM_ELEMENT[p.ds];
  const dayPol = STEM_POLARITY[p.ds];

  const targets = [
    [p.ys, "stem"], [p.yb, "branch"],
    [p.ms, "stem"], [p.mb, "branch"],
    [p.db, "branch"]
  ];

  const dist = {};
  ["비견","겁재","식신","상관","편재","정재","편관","정관","편인","정인"].forEach(n => dist[n] = 0);

  targets.forEach(([ch, type]) => {
    const tEl = type === "stem" ? STEM_ELEMENT[ch] : BRANCH_ELEMENT[ch];
    const tPol = type === "stem" ? STEM_POLARITY[ch] : BRANCH_POLARITY[ch];
    const s = getSipsin(dayEl, dayPol, tEl, tPol);
    dist[s]++;
  });

  let dominant = "비견", maxCount = 0;
  Object.entries(dist).forEach(([k, v]) => { if (v > maxCount) { maxCount = v; dominant = k; } });

  return { dayStem: p.ds, dayEl, dayPol, distribution: dist, dominant, pillars: p };
}

/* 사주 모드: 십신 분포 (8글자, 시주 포함) */
function calcSipsinFull(year, month, day, hour) {
  const p = calcPillarsFull(year, month, day, hour);
  const dayEl = STEM_ELEMENT[p.ds];
  const dayPol = STEM_POLARITY[p.ds];

  const targets = [
    [p.ys, "stem"], [p.yb, "branch"],
    [p.ms, "stem"], [p.mb, "branch"],
    [p.db, "branch"]
  ];

  // 시주가 있으면 추가
  if (p.hs && p.hb) {
    targets.push([p.hs, "stem"], [p.hb, "branch"]);
  }

  const dist = {};
  ["비견","겁재","식신","상관","편재","정재","편관","정관","편인","정인"].forEach(n => dist[n] = 0);

  targets.forEach(([ch, type]) => {
    const tEl = type === "stem" ? STEM_ELEMENT[ch] : BRANCH_ELEMENT[ch];
    const tPol = type === "stem" ? STEM_POLARITY[ch] : BRANCH_POLARITY[ch];
    const s = getSipsin(dayEl, dayPol, tEl, tPol);
    dist[s]++;
  });

  let dominant = "비견", maxCount = 0;
  Object.entries(dist).forEach(([k, v]) => { if (v > maxCount) { maxCount = v; dominant = k; } });

  return { dayStem: p.ds, dayEl, dayPol, distribution: dist, dominant, pillars: p };
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

  // amplify: DNA=5, 사주(8글자)=5, 사주(6글자)=4
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
