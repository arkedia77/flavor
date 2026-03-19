#!/usr/bin/env python3
"""
flavor Aurora Glassmorphism 테마 적용 스크립트
2025 트렌드: 움직이는 Aurora 배경 + Glassmorphism 카드 + 네온 포인트
"""

import os, re, glob

# ─── Pretendard 폰트 ─────────────────────────────────────
PRETENDARD_IMPORT = "@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');\n\n"

# ─── Aurora 배경 + keyframes (style 블록 끝에 추가) ──────
AURORA_INJECT = """
/* ═══════════════════════════════════════════
   Aurora Glassmorphism Theme (2025)
   ═══════════════════════════════════════════ */

/* Aurora 그라디언트 배경 레이어 */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(ellipse 90% 60% at -10% 0%,  rgba(120, 40, 200, 0.55) 0%, transparent 55%),
    radial-gradient(ellipse 70% 80% at 110% 0%,  rgba(236, 72, 153, 0.45) 0%, transparent 55%),
    radial-gradient(ellipse 80% 60% at 20%  110%, rgba(34, 211, 238, 0.25) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 85%  85%,  rgba(120, 40, 200, 0.35) 0%, transparent 55%);
  animation: auroraFloat 16s ease-in-out infinite alternate;
  pointer-events: none;
}

@keyframes auroraFloat {
  0%   { transform: scale(1)    translate(0%,   0%)   rotate(0deg); }
  33%  { transform: scale(1.06) translate(-3%,  1.5%) rotate(1deg); }
  66%  { transform: scale(0.97) translate(2%,  -1%)   rotate(-1deg); }
  100% { transform: scale(1.08) translate(-2%,  3%)   rotate(2deg); }
}
"""

# ─── 색상 매핑 ───────────────────────────────────────────
COLOR_MAP = [
    # 배경 (기존 검정 → 더 딥한 인디고 블랙)
    ('#0f0e17',  '#080612'),
    ('#080810',  '#080612'),
    ('#0a0a18',  '#0e0920'),
    ('#1b0f2a',  '#130a24'),
    ('#1a1a2e',  '#110920'),
    ('#1a1a30',  '#110920'),
    ('#13132b',  '#0f0a20'),

    # 카드 → Glassmorphism 반투명
    ('background: #111124;',  'background: rgba(20,10,45,0.55); backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%);'),
    ('background: #16162a;',  'background: rgba(20,10,45,0.55); backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%);'),
    ('background:#111124;',   'background:rgba(20,10,45,0.55);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'),
    ('background:#16162a;',   'background:rgba(20,10,45,0.55);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'),

    # 이미 rgba인 카드 배경 유지 or 강화
    ('rgba(17,17,36,0.7)',  'rgba(20,10,45,0.65)'),
    ('rgba(20,20,40,0.8)',  'rgba(20,10,45,0.7)'),
    ('rgba(255,255,255,0.04)', 'rgba(255,255,255,0.05)'),

    # 보더 → 반투명 퍼플
    ('border: 1px solid #1e1e38;',    'border: 1px solid rgba(192,132,252,0.18);'),
    ('border: 1.5px solid #1e1e38;',  'border: 1.5px solid rgba(192,132,252,0.22);'),
    ('border: 2px solid #1e1e38;',    'border: 2px solid rgba(192,132,252,0.22);'),
    ('border: 1px solid #2a2a45;',    'border: 1px solid rgba(192,132,252,0.18);'),
    ('border: 1.5px solid #2a2a45;',  'border: 1.5px solid rgba(192,132,252,0.22);'),
    ('border: 1.5px solid #2a2a48;',  'border: 1.5px solid rgba(192,132,252,0.22);'),
    ('#1e1e38',  'rgba(192,132,252,0.18)'),
    ('#2a2a45',  'rgba(192,132,252,0.18)'),
    ('#2a2a48',  'rgba(192,132,252,0.18)'),

    # 입력 필드 배경
    ('background: #0a0a18;',  'background: rgba(15,8,32,0.7);'),
    ('background: #0a0a18',   'background: rgba(15,8,32,0.7)'),
    ('#444460',  '#6644aa'),  # placeholder

    # 버튼 그라디언트 → 퍼플-핑크 (더 바이브런트)
    ('linear-gradient(135deg, #c084fc 0%, #a855f7 100%)',  'linear-gradient(135deg, #c084fc 0%, #ec4899 100%)'),
    ('linear-gradient(135deg, #c084fc, #a855f7)',           'linear-gradient(135deg, #c084fc, #ec4899)'),
    ('linear-gradient(90deg, #c084fc, #a855f7)',            'linear-gradient(90deg, #a855f7, #ec4899)'),
    ('linear-gradient(135deg, #ff8906 0%, #ff5f40 100%)',  'linear-gradient(135deg, #c084fc 0%, #ec4899 100%)'),

    # 포인트 주황 → 핑크 (더 트렌디)
    ('#ff8906',  '#d946ef'),
    ('#ff5f40',  '#c026d3'),

    # box-shadow glow 강화
    ('0 8px 32px rgba(192,132,252,0.3)',   '0 8px 32px rgba(192,132,252,0.4), 0 0 60px rgba(192,132,252,0.15)'),
    ('0 6px 20px rgba(192,132,252,0.25)',  '0 6px 20px rgba(192,132,252,0.35), 0 0 40px rgba(192,132,252,0.12)'),
    ('0 8px 24px rgba(255,137,6,0.3)',     '0 8px 24px rgba(217,70,239,0.4),  0 0 40px rgba(217,70,239,0.15)'),
    ('box-shadow: 0 8px 32px rgba(255,137,6,0.3)', 'box-shadow: 0 8px 32px rgba(217,70,239,0.4), 0 0 50px rgba(217,70,239,0.15)'),

    # 카드 내부 glass highlight (::before 라인)
    ('inset 0 1px 0 rgba(255,255,255,0.15)',  'inset 0 1px 0 rgba(255,255,255,0.2)'),

    # 진행바 배경
    ('background: #1e1e38;',  'background: rgba(192,132,252,0.12);'),
    ('background: #1a1a30;',  'background: rgba(192,132,252,0.12);'),
    ('background: #1a1a2e;',  'background: rgba(192,132,252,0.12);'),

    # disabled 버튼
    ('#252540',  'rgba(30,15,60,0.6)'),
    ('#444466',  '#6655aa'),

    # 서브 텍스트 약간 밝게
    ('#8888aa',  '#9988bb'),
    ('#777799',  '#9988bb'),
    ('#555577',  '#7766aa'),
    ('#333355',  '#5544aa'),
]

FONT_REPLACEMENTS = [
    ("-apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
     "'Pretendard Variable', Pretendard, -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"),
    ("'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
     "'Pretendard Variable', Pretendard, 'Noto Sans KR', -apple-system, sans-serif"),
]


def transform_style(css):
    # 1. 폰트
    for old, new in FONT_REPLACEMENTS:
        css = css.replace(old, new)

    # 2. 색상/효과 치환
    for old, new in COLOR_MAP:
        css = css.replace(old, new)

    # 3. Pretendard import 추가 (중복 방지)
    if 'pretendard' not in css.lower():
        css = PRETENDARD_IMPORT + css

    # 4. Aurora 주입 (중복 방지)
    if 'auroraFloat' not in css:
        css = css.rstrip() + '\n' + AURORA_INJECT

    return css


def process_html(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    def replace_style_block(m):
        return '<style>\n' + transform_style(m.group(1).strip()) + '\n</style>'

    new_content = re.sub(r'<style>(.*?)</style>', replace_style_block, content, flags=re.DOTALL)

    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def transform_style_py(css):
    """public.py용: f-string 충돌 방지 — 색상/폰트만 치환, Aurora keyframes 주입 안 함"""
    for old, new in FONT_REPLACEMENTS:
        css = css.replace(old, new)
    for old, new in COLOR_MAP:
        css = css.replace(old, new)
    if 'pretendard' not in css.lower():
        css = PRETENDARD_IMPORT + css
    return css


def process_python_inline(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    def replace_style_block(m):
        return '<style>\n' + transform_style_py(m.group(1).strip()) + '\n</style>'

    new_content = re.sub(r'<style>(.*?)</style>', replace_style_block, content, flags=re.DOTALL)

    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(__file__))

    html_files = glob.glob(os.path.join(base, '**/*.html'), recursive=True)
    changed = []
    for path in sorted(html_files):
        if process_html(path):
            changed.append(os.path.relpath(path, base))

    py_path = os.path.join(base, 'api/public.py')
    if process_python_inline(py_path):
        changed.append('api/public.py')

    print(f"변환 완료: {len(changed)}개 파일")
    for f in changed:
        print(f"  ✓ {f}")
