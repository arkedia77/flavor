"""공개 페이지 Blueprint: /, /survey, /result, /ab, /swipe, /compare, /health"""

import os
import json
from flask import Blueprint, redirect, jsonify, render_template_string

from config import DOMAIN_EMOJI
from engines.personality import get_personality_type
from db.repository import get_submission

public = Blueprint('public', __name__)


@public.route("/")
def hub():
    hub_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "hub", "hub.html")
    with open(hub_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/saju")
def hub_saju():
    hub_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "hub", "hub_saju.html")
    with open(hub_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/health")
def health():
    return jsonify({"status": "ok", "service": "flavor-saju"})


@public.route("/survey")
def survey():
    survey_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_stages", "survey.html")
    with open(survey_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/ab")
def ab_quiz():
    ab_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol2_ab", "ab.html")
    with open(ab_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/swipe")
def swipe_quiz():
    swipe_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol3_swipe", "swipe.html")
    with open(swipe_path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/romance")
def romance_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol2_romance", "romance.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/romance-v2")
def romance_v2_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol2_romance", "romance_v2.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/romance-v2-saju")
def romance_v2_saju_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol2_romance", "romance_v2_saju.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/food")
def food_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol3_food", "food.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/food-saju")
def food_saju_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol3_food", "food_saju.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/travel")
def travel_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol4_travel", "travel.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/travel-saju")
def travel_saju_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol4_travel", "travel_saju.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/work")
def work_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol5_work", "work.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/work-saju")
def work_saju_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol5_work", "work_saju.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/fashion")
def fashion_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol6_fashion", "fashion.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/fashion-saju")
def fashion_saju_quiz():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "vol6_fashion", "fashion_saju.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/compare")
def compare():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "quizzes", "compare", "compare.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}


@public.route("/result/<result_id>")
def result_page(result_id):
    row = get_submission(result_id)

    if not row:
        return "결과를 찾을 수 없습니다.", 404

    rid, name, birth_date, birth_time, gender, profile_json, results_json = row

    profile = json.loads(profile_json) if profile_json else {}
    results = json.loads(results_json) if results_json else {}

    pt = get_personality_type(profile)
    ptype     = pt["type"]
    pemoji    = pt["emoji"]
    ptagline  = pt["tagline"]
    pdetail   = pt["detail"]

    cards_html = ""
    for domain, rec in results.items():
        emoji = DOMAIN_EMOJI.get(domain, "✨")
        desc_html = f'<p class="d-desc">"{rec.get("description","")}"</p>' if rec.get("description") else ""
        cards_html += f"""
        <div class="domain-card">
          <div class="d-head">
            <span class="d-emoji">{emoji}</span>
            <span class="d-label">{domain}</span>
          </div>
          <div class="d-item">{rec.get('item','')}</div>
          <div class="d-reason">{rec.get('reason','')}</div>
          {desc_html}
        </div>"""

    share_url = f"https://flavor.arkedia.work/result/{result_id}"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta property="og:title" content="{name}의 취향 유형: {ptype} {pemoji}">
<meta property="og:description" content="{ptagline} — 생년월일 × 27문항 취향 분석">
<meta property="og:url" content="{share_url}">
<title>{name}의 취향 유형: {ptype}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #080810;
  color: #e8e8f0;
  font-family: -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  min-height: 100vh;
}}
.wrap {{ max-width: 480px; margin: 0 auto; padding: 0 0 80px; }}

/* ─── HERO ─── */
.hero {{
  position: relative;
  text-align: center;
  padding: 48px 24px 36px;
  background: linear-gradient(180deg, #13132b 0%, #080810 100%);
  overflow: hidden;
}}
.hero::before {{
  content: '';
  position: absolute;
  top: -60px; left: 50%;
  transform: translateX(-50%);
  width: 320px; height: 320px;
  background: radial-gradient(circle, rgba(255,137,6,0.18) 0%, transparent 70%);
  pointer-events: none;
}}
.hero-badge {{
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #ff8906;
  border: 1px solid rgba(255,137,6,0.3);
  border-radius: 20px;
  padding: 5px 14px;
  margin-bottom: 20px;
  text-transform: uppercase;
}}
.type-emoji {{
  font-size: 4rem;
  line-height: 1;
  margin-bottom: 12px;
  display: block;
  filter: drop-shadow(0 0 24px rgba(255,137,6,0.5));
}}
.type-name {{
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: -0.02em;
  color: #fff;
  margin-bottom: 10px;
  line-height: 1.1;
}}
.type-tagline {{
  font-size: 1rem;
  font-weight: 700;
  color: #ff8906;
  margin-bottom: 14px;
  line-height: 1.4;
}}
.type-detail {{
  font-size: 0.85rem;
  color: #8888aa;
  line-height: 1.7;
  max-width: 320px;
  margin: 0 auto 20px;
}}
.hero-name-line {{
  font-size: 0.8rem;
  color: #555577;
  margin-top: 4px;
}}
.hero-name-line strong {{
  color: #a0a0c8;
  font-weight: 600;
}}

/* ─── DIVIDER ─── */
.section-label {{
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: #555577;
  text-transform: uppercase;
  padding: 24px 20px 12px;
}}

/* ─── DOMAIN CARDS ─── */
.domain-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding: 0 16px;
}}
.domain-card {{
  background: #111124;
  border: 1px solid #1e1e38;
  border-radius: 16px;
  padding: 14px;
  transition: border-color 0.2s;
}}
.domain-card:active {{ border-color: #ff890633; }}
.d-head {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}}
.d-emoji {{ font-size: 1.1rem; }}
.d-label {{
  font-size: 0.68rem;
  font-weight: 700;
  color: #555577;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}}
.d-item {{
  font-size: 0.95rem;
  font-weight: 800;
  color: #e8e8f0;
  margin-bottom: 5px;
  line-height: 1.3;
}}
.d-reason {{
  font-size: 0.75rem;
  color: #7777aa;
  line-height: 1.5;
}}
.d-desc {{
  font-size: 0.72rem;
  color: rgba(255,137,6,0.6);
  line-height: 1.5;
  margin-top: 6px;
  font-style: italic;
}}

/* ─── CTA ─── */
.cta-box {{
  margin: 20px 16px 0;
  background: #111124;
  border: 1px solid #1e1e38;
  border-radius: 20px;
  padding: 24px 20px;
  text-align: center;
}}
.cta-lead {{
  font-size: 1.05rem;
  font-weight: 800;
  color: #e8e8f0;
  margin-bottom: 6px;
  line-height: 1.4;
}}
.cta-sub {{
  font-size: 0.82rem;
  color: #666688;
  margin-bottom: 20px;
  line-height: 1.6;
}}
.btn-primary {{
  display: block;
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #ff8906 0%, #ff5f40 100%);
  color: #fff;
  font-weight: 900;
  font-size: 1rem;
  border-radius: 14px;
  text-decoration: none;
  border: none;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: -0.01em;
  box-shadow: 0 8px 24px rgba(255,137,6,0.3);
}}
.btn-secondary {{
  display: block;
  width: 100%;
  padding: 14px;
  background: transparent;
  color: #666688;
  font-size: 0.88rem;
  font-weight: 600;
  border: 1.5px solid #1e1e38;
  border-radius: 12px;
  cursor: pointer;
  margin-top: 10px;
  font-family: inherit;
  transition: all 0.2s;
}}
.btn-secondary:active {{ border-color: #ff8906; color: #ff8906; }}
.copied {{ color: #4ade80 !important; border-color: #4ade80 !important; }}
</style>
</head>
<body>
<div class="wrap">

  <!-- HERO -->
  <div class="hero">
    <div class="hero-badge">✦ 취향 유형 분석</div>
    <span class="type-emoji">{pemoji}</span>
    <div class="type-name">{ptype}</div>
    <div class="type-tagline">"{ptagline}"</div>
    <div class="type-detail">{pdetail}</div>
    <div class="hero-name-line">생년월일 × 27문항 — <strong>{name}</strong>님의 결과</div>
  </div>

  <!-- DOMAIN CARDS -->
  <div class="section-label">취향 상세 분석</div>
  <div class="domain-grid">
    {cards_html}
  </div>

  <!-- CTA -->
  <div class="cta-box">
    <div class="cta-lead">내 취향 유형은 뭘까? 🤔</div>
    <div class="cta-sub">생년월일 × 27가지 질문<br>커피부터 인테리어까지 분석해드려요</div>
    <a class="btn-primary" href="/survey">👉 나도 취향 분석하기 (무료)</a>
    <button class="btn-secondary" id="btn-share" onclick="copyLink()">🔗 이 결과 공유하기</button>
  </div>

</div>
<script>
function copyLink() {{
  navigator.clipboard.writeText('{share_url}').then(() => {{
    const btn = document.getElementById('btn-share');
    btn.textContent = '✅ 링크 복사됐어요! 친구에게 보내세요';
    btn.classList.add('copied');
    setTimeout(() => {{
      btn.textContent = '🔗 이 결과 공유하기';
      btn.classList.remove('copied');
    }}, 2500);
  }}).catch(() => {{
    prompt('아래 링크를 복사하세요', '{share_url}');
  }});
}}
</script>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
