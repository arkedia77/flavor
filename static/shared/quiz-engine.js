/* ═══════════════════════════════════════════
   quiz-engine.js — flavor 퀴즈 공통 엔진

   사용법: 각 퀴즈 HTML에서 QUIZ_CONFIG 정의 후 이 스크립트 로드

   QUIZ_CONFIG = {
     mode: 'dna' | 'saju',
     quizType: 'vol4_travel',
     storageKey: 'flavor_profile_dna',

     intro: { startButton: '...' },
     quiz: { innateLabel: '...' },
     loading: { emoji: '...', text: '...', sub: '...' },
     result: {
       innateLabel, actualLabel,
       legendInnate, legendActual,
       nameSub, sectionTraits, sectionDomains,
       ctaLead, ctaSub, shareText,
       shareUrl: '/travel'  // 공유 시 보낼 URL path
     },

     questions: [...],  // QUESTIONS 배열
     types: [...],      // 유형 분류 배열
     traits: [...],     // 트레이트 정의 배열
   }
   ═══════════════════════════════════════════ */

const API_BASE = window.location.origin;

let currentQ = 0;
let answers = [];
let qStartTime = 0;
let userData = {};
let innateProfile = {};
let sipsinData = {};
let resultShareUrl = '';

/* ═══ 초기화 ═══ */
function initQuiz() {
  const C = window.QUIZ_CONFIG;
  if (!C) { console.error('QUIZ_CONFIG not defined'); return; }

  // 연도/월/일 셀렉트 채우기
  populateSelects();

  // 사주 모드면 시간 셀렉트 추가 (HTML에 이미 있어야 함)
  if (C.mode === 'saju') {
    populateHourSelect();
  }

  // 로딩 화면 텍스트 세팅
  const loadEmoji = document.querySelector('#screen-loading .loading-emoji');
  const loadText = document.querySelector('#screen-loading .loading-text');
  const loadSub = document.querySelector('#screen-loading .loading-sub');
  if (loadEmoji && C.loading) loadEmoji.textContent = C.loading.emoji;
  if (loadText && C.loading) loadText.textContent = C.loading.text;
  if (loadSub && C.loading) loadSub.textContent = C.loading.sub;

  // 프로필 자동 채움
  prefillFromProfile();
}

function populateSelects() {
  const yearSel = document.getElementById('birth_year');
  if (yearSel) {
    for (let y = 2010; y >= 1940; y--) {
      const o = document.createElement('option');
      o.value = y; o.textContent = y + '년';
      yearSel.appendChild(o);
    }
  }
  const monthSel = document.getElementById('birth_month');
  if (monthSel) {
    for (let m = 1; m <= 12; m++) {
      const o = document.createElement('option');
      o.value = String(m).padStart(2, '0'); o.textContent = m + '월';
      monthSel.appendChild(o);
    }
  }
  const daySel = document.getElementById('birth_day');
  if (daySel) {
    for (let d = 1; d <= 31; d++) {
      const o = document.createElement('option');
      o.value = String(d).padStart(2, '0'); o.textContent = d + '일';
      daySel.appendChild(o);
    }
  }
}

function populateHourSelect() {
  const hourSel = document.getElementById('birth_hour');
  if (!hourSel) return;
  const hours = [
    {v:'0',  t:'자시 (23:00~01:00)'},
    {v:'2',  t:'축시 (01:00~03:00)'},
    {v:'4',  t:'인시 (03:00~05:00)'},
    {v:'6',  t:'묘시 (05:00~07:00)'},
    {v:'8',  t:'진시 (07:00~09:00)'},
    {v:'10', t:'사시 (09:00~11:00)'},
    {v:'12', t:'오시 (11:00~13:00)'},
    {v:'14', t:'미시 (13:00~15:00)'},
    {v:'16', t:'신시 (15:00~17:00)'},
    {v:'18', t:'유시 (17:00~19:00)'},
    {v:'20', t:'술시 (19:00~21:00)'},
    {v:'22', t:'해시 (21:00~23:00)'},
    {v:'unknown', t:'모르겠어요'},
  ];
  hours.forEach(h => {
    const o = document.createElement('option');
    o.value = h.v; o.textContent = h.t;
    hourSel.appendChild(o);
  });
}

function prefillFromProfile() {
  try {
    const C = window.QUIZ_CONFIG;
    const profile = JSON.parse(localStorage.getItem(C.storageKey));
    if (!profile) return;
    if (profile.name) document.getElementById('name').value = profile.name;
    if (profile.birth_date) {
      const [y, m, d] = profile.birth_date.split('-');
      document.getElementById('birth_year').value = y;
      document.getElementById('birth_month').value = m.replace(/^0/, '');
      document.getElementById('birth_day').value = d.replace(/^0/, '');
    }
    if (profile.gender) {
      const btn = document.querySelector(`[data-gender="${profile.gender}"]`);
      if (btn) btn.classList.add('selected');
    }
    if (C.mode === 'saju' && profile.birth_hour && document.getElementById('birth_hour')) {
      document.getElementById('birth_hour').value = profile.birth_hour;
    }
    setTimeout(() => checkFormReady(), 0);
  } catch(e) {}
}

/* ═══ 폼 검증 ═══ */
function checkFormReady() {
  const C = window.QUIZ_CONFIG;
  const name = document.getElementById('name').value.trim();
  const year = document.getElementById('birth_year').value;
  const month = document.getElementById('birth_month').value;
  const day = document.getElementById('birth_day').value;
  const gender = document.querySelector('.gender-btn.selected');
  let ready = name && year && month && day && gender;

  if (C.mode === 'saju') {
    const hour = document.getElementById('birth_hour');
    if (hour && !hour.value) ready = false;
  }

  const btn = document.getElementById('btn-start');
  if (ready) {
    btn.disabled = false;
    btn.classList.remove('disabled');
    btn.classList.add('ready');
  } else {
    btn.disabled = true;
    btn.classList.add('disabled');
    btn.classList.remove('ready');
  }
}

function selectGender(btn) {
  document.querySelectorAll('.gender-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  checkFormReady();
}

/* ═══ 퀴즈 시작 ═══ */
function startQuiz() {
  const C = window.QUIZ_CONFIG;
  const name = document.getElementById('name').value.trim();
  const year = document.getElementById('birth_year').value;
  const month = document.getElementById('birth_month').value;
  const day = document.getElementById('birth_day').value;
  const genderBtn = document.querySelector('.gender-btn.selected');
  if (!name || !year || !month || !day || !genderBtn) return;

  let hour = null;
  if (C.mode === 'saju') {
    const hourVal = document.getElementById('birth_hour').value;
    hour = hourVal === 'unknown' ? null : parseInt(hourVal);
  }

  userData = {
    name,
    birth_date: `${year}-${month}-${day}`,
    birth_time: C.mode === 'saju' ? (hour !== null ? String(hour) : 'unknown') : '12',
    gender: genderBtn.dataset.gender
  };

  // 십신 계산
  if (C.mode === 'saju') {
    sipsinData = calcSipsinFull(parseInt(year), parseInt(month), parseInt(day), hour);
    const hasHour = hour !== null;
    innateProfile = sipsinToInnate(sipsinData, hasHour ? 5 : 4);
  } else {
    sipsinData = calcSipsin(parseInt(year), parseInt(month), parseInt(day));
    innateProfile = sipsinToInnate(sipsinData, 5);
  }

  document.getElementById('screen-intro').style.display = 'none';
  document.getElementById('screen-quiz').style.display = 'flex';
  document.body.classList.add('no-scroll');
  showQuestion(0);
}

/* ═══ 문항 표시 ═══ */
function showQuestion(idx) {
  const C = window.QUIZ_CONFIG;
  const q = C.questions[idx];
  const innateVal = innateProfile[q.dimension] || 0.5;
  const isHigh = innateVal >= 0.5;

  // 선천 성향 배너
  document.getElementById('innate-text').textContent =
    `넌 "${isHigh ? q.highText : q.lowText}" 타입이야`;

  if (isHigh) {
    document.getElementById('emoji-a').textContent = q.A.emoji;
    document.getElementById('text-a').textContent  = q.A.label;
    document.getElementById('emoji-b').textContent = q.B.emoji;
    document.getElementById('text-b').textContent  = q.B.label;
  } else {
    document.getElementById('emoji-a').textContent = q.B.emoji;
    document.getElementById('text-a').textContent  = q.B.label.replace('아닌데?', '맞아,');
    document.getElementById('emoji-b').textContent = q.A.emoji;
    document.getElementById('text-b').textContent  = q.A.label.replace('맞아,', '아닌데?');
  }

  document.getElementById('opt-a').className = 'ab-option';
  document.getElementById('opt-b').className = 'ab-option';
  document.getElementById('progress-fill').style.width = (idx / C.questions.length * 100) + '%';
  document.getElementById('progress-text').textContent = `${idx + 1} / ${C.questions.length}`;
  qStartTime = Date.now();
}

function choose(side) {
  const C = window.QUIZ_CONFIG;
  if (currentQ >= C.questions.length) return;
  const q = C.questions[currentQ];
  const responseMs = Date.now() - qStartTime;
  const innateVal = innateProfile[q.dimension] || 0.5;
  const isHigh = innateVal >= 0.5;

  document.getElementById(`opt-${side.toLowerCase()}`).classList.add(`selected-${side.toLowerCase()}`);

  let chosenVal;
  if (side === 'A') {
    chosenVal = isHigh ? q.A.val : q.B.val;
  } else {
    chosenVal = isHigh ? q.B.val : q.A.val;
  }

  answers.push({
    id: q.id,
    dimension: q.dimension,
    choice: side,
    value: chosenVal,
    innate_value: innateVal,
    agreed_with_innate: side === 'A',
    response_ms: responseMs
  });

  currentQ++;

  if (currentQ < C.questions.length) {
    setTimeout(() => showQuestion(currentQ), 220);
  } else {
    setTimeout(submitAnswers, 300);
  }
}

/* ═══ 프로필 계산 ═══ */
function buildProfile() {
  const dims = {};
  const counts = {};
  answers.forEach(a => {
    dims[a.dimension] = (dims[a.dimension] || 0) + a.value;
    counts[a.dimension] = (counts[a.dimension] || 0) + 1;
  });
  const profile = {};
  Object.keys(dims).forEach(d => { profile[d] = dims[d] / counts[d]; });
  DIMENSIONS.forEach(d => { if (profile[d] === undefined) profile[d] = 0.5; });
  return profile;
}

function getQuizType(profile) {
  const C = window.QUIZ_CONFIG;
  for (const rt of C.types) {
    if (rt.cond(profile)) return rt;
  }
  return C.types[C.types.length - 1];
}

/* ═══ 갭 분석 ═══ */
function analyzeGap(innate, actual) {
  let totalGap = 0;
  const gaps = [];
  const dimLabels = {
    social:'소통', adventurous:'모험', aesthetic:'감성',
    comfort:'안정', budget:'소비', maximalist:'표현',
    energetic:'활동', urban:'도시', bitter:'깊이'
  };

  DIMENSIONS.forEach(d => {
    const gap = Math.abs(innate[d] - actual[d]);
    totalGap += gap;
    if (gap > 0.15) {
      const dir = actual[d] > innate[d] ? '↑' : '↓';
      gaps.push({ dim: d, label: dimLabels[d], gap, dir });
    }
  });

  const avgGap = totalGap / DIMENSIONS.length;
  gaps.sort((a, b) => b.gap - a.gap);

  let title, detail;
  if (avgGap < 0.08) {
    title = "🎯 DNA 그대로! 유전자 순응형";
    detail = "타고난 성향 그대로 사는 중이시네요. DNA 말 잘 듣는 모범생!";
  } else if (avgGap < 0.18) {
    title = "🔄 DNA를 살짝 비튼 진화형";
    const top = gaps[0];
    detail = top
      ? `${top.label} 쪽에서 DNA랑 좀 달라졌어요. 세상이 당신을 바꿔놨군요 ㅋㅋ`
      : "미세하게 커스텀하신 분이시네요.";
  } else {
    title = "🌀 DNA 반항아! 뒤집기 장인";
    const topTwo = gaps.slice(0, 2).map(g => g.label).join(', ');
    detail = `특히 ${topTwo}에서 DNA랑 정반대예요. 유전자도 예상 못 한 반전!`;
  }

  return { title, detail, avgGap, gaps };
}

/* ═══ 트레이트 렌더링 ═══ */
function getTraits(innate, actual) {
  const C = window.QUIZ_CONFIG;
  return C.traits.map(t => {
    const iVal = innate[t.dim] || 0.5;
    const aVal = actual[t.dim] || 0.5;
    const gap = Math.abs(iVal - aVal);
    let gapText = '';
    if (gap > 0.15) {
      gapText = aVal > iVal ? `DNA보다 ${t.high} 쪽으로!` : `DNA보다 ${t.low} 쪽으로!`;
    }
    const desc = aVal > 0.55 ? t.high : aVal < 0.45 ? t.low : `${t.low} ↔ ${t.high}`;
    return { ...t, innateVal: iVal, actualVal: aVal, desc, gapText };
  });
}

function renderTraits(innate, actual) {
  const traitsDiv = document.getElementById('r-traits');
  traitsDiv.innerHTML = '';
  getTraits(innate, actual).forEach(t => {
    const row = document.createElement('div');
    row.className = 'trait-row';

    const iPct = Math.round(t.innateVal * 100);
    const aPct = Math.round(t.actualVal * 100);
    const diff = aPct - iPct;
    const absDiff = Math.abs(diff);

    let changeClass, changeText;
    if (absDiff <= 5) {
      changeClass = 'same'; changeText = '= 동일';
    } else if (diff > 0) {
      changeClass = 'up'; changeText = `↑ +${absDiff}`;
    } else {
      changeClass = 'down'; changeText = `↓ -${absDiff}`;
    }

    const iPos = Math.max(8, Math.min(92, iPct));
    const aPos = Math.max(8, Math.min(92, aPct));
    const shiftLeft = Math.min(iPos, aPos);
    const shiftWidth = Math.abs(aPos - iPos);

    row.innerHTML = `
      <div class="trait-header">
        <span class="trait-label">${t.label}</span>
        <span class="trait-change ${changeClass}">${changeText}</span>
      </div>
      <div class="trait-axis-labels">
        <span>${t.low}</span>
        <span>${t.high}</span>
      </div>
      <div class="trait-track">
        <div class="trait-track-bg"></div>
        ${shiftWidth > 3 ? `<div class="trait-shift-zone" style="left:${shiftLeft}%;width:${shiftWidth}%"></div>` : ''}
        ${shiftWidth > 3 ? `<div class="trait-arrow" style="left:${shiftLeft}%;width:${shiftWidth}%"></div>` : ''}
        <div class="trait-marker-innate" style="left:${iPos}%"></div>
        <div class="trait-marker-actual" style="left:${aPos}%"></div>
      </div>`;
    traitsDiv.appendChild(row);
  });
}

function renderDomains(results) {
  const grid = document.getElementById('r-domains');
  grid.innerHTML = '';
  Object.entries(results).forEach(([domain, rec]) => {
    const card = document.createElement('div');
    card.className = 'domain-card';
    const descHtml = rec.description ? `<div class="d-desc">"${rec.description}"</div>` : '';
    card.innerHTML = `
      <div class="d-head">
        <span class="d-icon">${DOMAIN_EMOJI[domain]||'✨'}</span>
        <span class="d-label">${domain}</span>
      </div>
      <div class="d-item">${rec.item||''}</div>
      <div class="d-reason">${rec.reason||''}</div>
      ${descHtml}
      <div class="d-feedback" data-domain="${domain}">
        <button class="fb-btn" data-v="2" onclick="sendFeedback(this,'${domain}',2)"><span class="fb-emoji">🎯</span><span class="fb-text">소름 나야 이거</span></button>
        <button class="fb-btn" data-v="1" onclick="sendFeedback(this,'${domain}',1)"><span class="fb-emoji">👍</span><span class="fb-text">맞아맞아</span></button>
        <button class="fb-btn" data-v="-1" onclick="sendFeedback(this,'${domain}',-1)"><span class="fb-emoji">🤷</span><span class="fb-text">글쎄...</span></button>
        <button class="fb-btn" data-v="-2" onclick="sendFeedback(this,'${domain}',-2)"><span class="fb-emoji">👎</span><span class="fb-text">완전 아닌데</span></button>
      </div>`;
    grid.appendChild(card);
  });
}

/* ═══ 피드백 전송 ═══ */
let _submissionId = null;

function sendFeedback(btn, domain, thumb) {
  if (!_submissionId) return;
  const wrap = btn.parentElement;
  if (wrap.classList.contains('voted')) return;

  wrap.classList.add('voted');
  wrap.querySelectorAll('.fb-btn').forEach(b => b.disabled = true);
  btn.classList.add('selected');

  fetch(`${API_BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ submission_id: _submissionId, domain, thumb })
  }).catch(() => {});
}

/* 사주 모드: 팔주 디스플레이 */
function renderPillars(pillars) {
  const wrap = document.getElementById('r-pillars');
  if (!wrap) return;

  const pillarData = [
    { label: '시주', stem: pillars.hs, branch: pillars.hb },
    { label: '일주', stem: pillars.ds, branch: pillars.db },
    { label: '월주', stem: pillars.ms, branch: pillars.mb },
    { label: '년주', stem: pillars.ys, branch: pillars.yb },
  ];

  wrap.innerHTML = '';
  pillarData.forEach(pd => {
    if (!pd.stem || !pd.branch) return;
    const el = STEM_ELEMENT[pd.stem] || '토';
    const div = document.createElement('div');
    div.className = `pillar el-${el}`;
    div.innerHTML = `
      <div class="pillar-label">${pd.label}</div>
      <div class="pillar-stem">${pd.stem}</div>
      <div class="pillar-branch">${pd.branch}</div>`;
    wrap.appendChild(div);
  });
}

/* ═══ 제출 ═══ */
async function submitAnswers() {
  const C = window.QUIZ_CONFIG;
  document.getElementById('screen-quiz').style.display = 'none';
  document.getElementById('screen-loading').style.display = 'flex';

  const actualProfile = buildProfile();

  try {
    const resp = await fetch(`${API_BASE}/api/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...userData,
        quiz_type: C.quizType,
        ab_answers: answers,
        survey: actualProfile,
        innate_profile: innateProfile,
        sipsin_data: { dominant: sipsinData.dominant, distribution: sipsinData.distribution, day_stem: sipsinData.dayStem }
      })
    });
    const data = await resp.json();
    if (data.status === 'ok') {
      showResult(data, actualProfile);
    } else {
      throw new Error(data.message);
    }
  } catch (e) {
    showResultLocal(actualProfile);
  }
}

function showResult(data, actualProfile) {
  const C = window.QUIZ_CONFIG;
  document.getElementById('screen-loading').style.display = 'none';
  document.getElementById('screen-result').style.display = 'block';
  document.body.classList.remove('no-scroll');
  document.body.classList.add('scrollable');

  const innateType = getQuizType(innateProfile);
  const actualType = getQuizType(actualProfile);

  document.getElementById('r-innate-emoji').textContent = innateType.emoji;
  document.getElementById('r-innate-type').textContent  = innateType.type;
  document.getElementById('r-actual-emoji').textContent = actualType.emoji;
  document.getElementById('r-actual-type').textContent  = actualType.type;
  document.getElementById('r-name').textContent = data.name || '';

  // 페르소나
  if (data.persona && data.persona.name) {
    document.getElementById('r-persona').textContent = `${data.persona.emoji || ''} ${data.persona.name} — ${data.persona.vibe || ''}`;
  }

  // 갭 분석
  const gap = analyzeGap(innateProfile, actualProfile);
  document.getElementById('r-gap-title').textContent = gap.title;
  document.getElementById('r-gap-detail').textContent = gap.detail;

  // 트레이트
  renderTraits(innateProfile, actualProfile);

  // 사주 모드: 팔주 표시
  if (C.mode === 'saju' && sipsinData.pillars) {
    renderPillars(sipsinData.pillars);
  }

  // 도메인 추천
  renderDomains(data.results || {});

  if (data.id) {
    _submissionId = data.id;
    resultShareUrl = `${API_BASE}/result/${data.id}`;
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
  updateFlavorProfile(C.quizType, innateProfile, actualProfile);
}

function showResultLocal(actualProfile) {
  const C = window.QUIZ_CONFIG;
  document.getElementById('screen-loading').style.display = 'none';
  document.getElementById('screen-result').style.display = 'block';
  document.body.classList.remove('no-scroll');
  document.body.classList.add('scrollable');

  const innateType = getQuizType(innateProfile);
  const actualType = getQuizType(actualProfile);

  document.getElementById('r-innate-emoji').textContent = innateType.emoji;
  document.getElementById('r-innate-type').textContent  = innateType.type;
  document.getElementById('r-actual-emoji').textContent = actualType.emoji;
  document.getElementById('r-actual-type').textContent  = actualType.type;
  document.getElementById('r-name').textContent = userData.name || '';

  const persona = DAY_MASTER_PERSONA[sipsinData.dayStem];
  if (persona) {
    document.getElementById('r-persona').textContent = `${persona.emoji} ${persona.name} — ${persona.vibe}`;
  }

  const gap = analyzeGap(innateProfile, actualProfile);
  document.getElementById('r-gap-title').textContent = gap.title;
  document.getElementById('r-gap-detail').textContent = gap.detail;

  renderTraits(innateProfile, actualProfile);

  if (C.mode === 'saju' && sipsinData.pillars) {
    renderPillars(sipsinData.pillars);
  }
  updateFlavorProfile(C.quizType, innateProfile, actualProfile);
}

function updateFlavorProfile(quizType, innate, actual) {
  const C = window.QUIZ_CONFIG;
  try {
    let profile = JSON.parse(localStorage.getItem(C.storageKey)) || {};
    profile.name = profile.name || userData.name;
    profile.birth_date = profile.birth_date || userData.birth_date;
    profile.gender = profile.gender || userData.gender;
    if (C.mode === 'saju' && userData.birth_time && userData.birth_time !== 'unknown') {
      profile.birth_hour = userData.birth_time;
    }
    if (!profile.completed_quizzes) profile.completed_quizzes = [];
    if (!profile.completed_quizzes.includes(quizType)) profile.completed_quizzes.push(quizType);
    if (!profile.quiz_results) profile.quiz_results = {};
    if (innate && actual) {
      const innateType = getQuizType(innate);
      const actualType = getQuizType(actual);
      profile.quiz_results[quizType] = {
        innate_emoji: innateType.emoji, innate_type: innateType.type,
        actual_emoji: actualType.emoji, actual_type: actualType.type,
        done_at: new Date().toISOString()
      };
    }
    if (!profile.created_at) profile.created_at = new Date().toISOString();
    localStorage.setItem(C.storageKey, JSON.stringify(profile));
  } catch(e) {}
}

function copyResult() {
  const C = window.QUIZ_CONFIG;
  const shareUrl = `${API_BASE}${C.result.shareUrl || '/'}`;
  navigator.clipboard.writeText(shareUrl).then(() => {
    const btn = document.querySelector('.btn-primary');
    const originalText = btn.textContent;
    btn.textContent = C.result.shareConfirm || '✅ 복사 완료! 보내서 도발해 🔥';
    setTimeout(() => { btn.textContent = originalText; }, 2500);
  }).catch(() => { prompt('아래 링크를 복사하세요', shareUrl); });
}

/* ═══ DOM Ready ═══ */
document.addEventListener('DOMContentLoaded', initQuiz);
