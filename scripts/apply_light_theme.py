#!/usr/bin/env python3
"""
flavor 라이트 오로라 테마 배치 변환 스크립트
dark (#080810) → light (#f5f3ff) + Pretendard 폰트
"""

import os, re, glob

# ─── 색상 매핑 ───────────────────────────────────────────
# 순서 중요: 긴 값(rgba 등) → 짧은 헥스 순
DARK_BG_COLORS = ['#0f0e17', '#080810']  # color: 로 쓰일 때는 #fff로

COLOR_MAP_ORDERED = [
    # rgba 변환 (먼저)
    ('rgba(17,17,36,0.7)',          'rgba(255,255,255,0.9)'),
    ('rgba(20,20,40,0.8)',          'rgba(237,233,254,0.85)'),
    ('rgba(192,132,252,0.18)',      'rgba(139,92,246,0.15)'),
    ('rgba(192,132,252,0.15)',      'rgba(139,92,246,0.12)'),
    ('rgba(192,132,252,0.12)',      'rgba(139,92,246,0.1)'),
    ('rgba(192,132,252,0.1)',       'rgba(139,92,246,0.08)'),
    ('rgba(192,132,252,0.08)',      'rgba(139,92,246,0.06)'),
    ('rgba(192,132,252,0.06)',      'rgba(139,92,246,0.05)'),
    ('rgba(192,132,252,0.04)',      'rgba(139,92,246,0.04)'),
    ('rgba(192,132,252,0.3)',       'rgba(139,92,246,0.25)'),
    ('rgba(192,132,252,0.5)',       'rgba(139,92,246,0.4)'),
    ('rgba(192,132,252,0.2)',       'rgba(139,92,246,0.18)'),
    ('rgba(192,132,252,0.25)',      'rgba(139,92,246,0.2)'),
    ('rgba(168,85,247,0.06)',       'rgba(124,58,237,0.05)'),
    ('rgba(168,85,247,0.04)',       'rgba(124,58,237,0.04)'),
    ('rgba(168,85,247,0.3)',        'rgba(124,58,237,0.25)'),
    ('rgba(255,137,6,0.18)',        'rgba(139,92,246,0.15)'),
    ('rgba(255,137,6,0.3)',         'rgba(139,92,246,0.25)'),
    ('rgba(255,137,6,0.5)',         'rgba(139,92,246,0.4)'),
    ('rgba(255,107,138,0.12)',      'rgba(236,72,153,0.1)'),
    ('rgba(255,107,138,0.3)',       'rgba(236,72,153,0.25)'),
    ('rgba(74,222,128,0.12)',       'rgba(34,197,94,0.1)'),
    ('rgba(74,222,128,0.2)',        'rgba(34,197,94,0.18)'),
    ('rgba(0,0,0,0.3)',             'rgba(139,92,246,0.08)'),
    ('rgba(255,255,255,0.04)',      'rgba(139,92,246,0.04)'),
    ('rgba(255,255,255,0.15)',      'rgba(255,255,255,0.3)'),

    # 그라디언트 배경
    ('linear-gradient(180deg, #1b0f2a 0%, #080810 100%)',
     'linear-gradient(180deg, #ede9fe 0%, #f5f3ff 100%)'),
    ('linear-gradient(135deg, #ff8906 0%, #ff5f40 100%)',
     'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'),
    ('linear-gradient(135deg, #c084fc 0%, #a855f7 100%)',
     'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)'),
    ('linear-gradient(135deg, #c084fc, #a855f7)',
     'linear-gradient(135deg, #8b5cf6, #7c3aed)'),
    ('linear-gradient(90deg, #c084fc, #a855f7)',
     'linear-gradient(90deg, #8b5cf6, #7c3aed)'),
    ('linear-gradient(135deg, rgba(192,132,252,0.12), rgba(255,107,138,0.12))',
     'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(236,72,153,0.08))'),
    ('linear-gradient(135deg, rgba(192,132,252,0.08), rgba(168,85,247,0.04))',
     'linear-gradient(135deg, rgba(139,92,246,0.06), rgba(124,58,237,0.03))'),
    ('linear-gradient(135deg, rgba(192,132,252,0.1), rgba(168,85,247,0.06))',
     'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(124,58,237,0.04))'),
    ('radial-gradient(circle, rgba(192,132,252,0.18) 0%, rgba(168,85,247,0.06) 40%, transparent 70%)',
     'radial-gradient(circle, rgba(139,92,246,0.15) 0%, rgba(124,58,237,0.05) 40%, transparent 70%)'),
    ('radial-gradient(circle, rgba(255,137,6,0.18) 0%, transparent 70%)',
     'radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)'),
    ('radial-gradient(circle, rgba(192,132,252,0.2) 0%, transparent 70%)',
     'radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)'),
    ('radial-gradient(circle, rgba(192,132,252,0.15) 0%, rgba(168,85,247,0.05) 40%, transparent 70%)',
     'radial-gradient(circle, rgba(139,92,246,0.12) 0%, rgba(124,58,237,0.04) 40%, transparent 70%)'),

    # 헥스 배경색 (어두운 것)
    ('#1b0f2a',  '#ede9fe'),
    ('#13132b',  '#f0eeff'),
    ('#16162a',  '#ffffff'),
    ('#111124',  '#ffffff'),
    ('#1a1a30',  '#e9e6f9'),
    ('#1a1a2e',  '#e9e6f9'),
    ('#0a0a18',  '#ede9fe'),
    ('#0f0e17',  '#f5f3ff'),
    ('#080810',  '#f5f3ff'),

    # 텍스트 색
    ('#fffffe',  '#1e1b4b'),
    ('#e8e8f0',  '#1e1b4b'),
    ('#c8c8e0',  '#4a4a6a'),
    ('#a7a9be',  '#7c7c9a'),
    ('#8888aa',  '#6d6d8a'),
    ('#777799',  '#6d6d8a'),
    ('#666688',  '#7c7c9a'),
    ('#555577',  '#8b8bab'),
    ('#444466',  '#9ca3af'),
    ('#444460',  '#a78bfa'),  # placeholder
    ('#333355',  '#9ca3af'),

    # 보더
    ('#2a2a48',  '#ddd6fe'),
    ('#2a2a45',  '#ddd6fe'),
    ('#1e1e38',  '#ddd6fe'),
    ('#252540',  '#e5e7eb'),

    # 포인트 퍼플 통일
    ('#c084fc',  '#8b5cf6'),
    ('#a855f7',  '#7c3aed'),
    ('#e879f9',  '#d946ef'),
    ('#ff6b8a',  '#ec4899'),

    # 포인트 주황 → 바이올렛
    ('#ff8906',  '#7c3aed'),
    ('#ff5f40',  '#6d28d9'),

    # 링 보더
    ('rgba(192,132,252,0.08)',  'rgba(139,92,246,0.15)'),
    ('rgba(192,132,252,0.4)',   'rgba(139,92,246,0.5)'),
    ('1px solid rgba(192,132,252,0.3)', '1px solid rgba(139,92,246,0.3)'),
    ('1.5px solid rgba(192,132,252,0.2)', '1.5px solid rgba(139,92,246,0.2)'),

    # box-shadow 오렌지
    ('0 8px 24px rgba(255,137,6,0.3)',  '0 8px 24px rgba(124,58,237,0.2)'),
    ('0 6px 20px rgba(192,132,252,0.25)', '0 6px 20px rgba(124,58,237,0.2)'),
    ('0 8px 32px rgba(192,132,252,0.3)', '0 8px 32px rgba(124,58,237,0.2)'),
    ('0 4px 16px rgba(192,132,252,0.3)', '0 4px 16px rgba(124,58,237,0.18)'),
    ('0 8px 40px rgba(192,132,252,0.5)', '0 8px 40px rgba(124,58,237,0.35)'),
    ('0 0 24px rgba(255,137,6,0.5)',     '0 0 24px rgba(124,58,237,0.3)'),
    ('0 0 0 3px rgba(192,132,252,0.12)', '0 0 0 3px rgba(139,92,246,0.15)'),
    ('0 0 0 3px rgba(192,132,252,0.1)',  '0 0 0 3px rgba(139,92,246,0.12)'),

    # filter drop-shadow
    ('drop-shadow(0 0 24px rgba(255,137,6,0.5))', 'drop-shadow(0 0 20px rgba(124,58,237,0.3))'),
    ('drop-shadow(0 0 20px rgba(192,132,252,0.4))', 'drop-shadow(0 0 20px rgba(139,92,246,0.35))'),
    ('drop-shadow(0 4px 12px rgba(0,0,0,0.3))', 'drop-shadow(0 4px 12px rgba(139,92,246,0.15))'),
]

FONT_REPLACEMENTS = [
    ("-apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
     "'Pretendard Variable', Pretendard, -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"),
    ("'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif",
     "'Pretendard Variable', Pretendard, 'Noto Sans KR', -apple-system, sans-serif"),
]

PRETENDARD_IMPORT = "@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');\n\n"

# body에 부드러운 그림자 효과 추가 (카드용)
CARD_SHADOW = "box-shadow: 0 2px 16px rgba(139,92,246,0.08), 0 1px 4px rgba(139,92,246,0.04);"


def transform_style(css):
    # 1. color: #dark → color: #fff (버튼 텍스트 등)
    for dark in DARK_BG_COLORS:
        css = re.sub(r'(color\s*:\s*)' + re.escape(dark), r'\1#ffffff', css)

    # 2. color: #0f0e17 in checked label (survey.html 패턴)
    css = css.replace('color: #0f0e17;', 'color: #ffffff;')
    css = css.replace('color: #080810;', 'color: #ffffff;')

    # 3. 색상 일괄 치환
    for old, new in COLOR_MAP_ORDERED:
        css = css.replace(old, new)

    # 4. 폰트
    for old, new in FONT_REPLACEMENTS:
        css = css.replace(old, new)

    # 4-1. 중복 Pretendard 제거
    css = css.replace(
        "'Pretendard Variable', Pretendard, -apple-system, 'Pretendard Variable', Pretendard, ",
        "'Pretendard Variable', Pretendard, -apple-system, "
    )
    css = css.replace(
        "'Pretendard Variable', Pretendard, 'Pretendard Variable', Pretendard, ",
        "'Pretendard Variable', Pretendard, "
    )

    # 5. 카드에 box-shadow 추가 (배경 흰색인 카드에만)
    # .quiz-card, .profile-card, .form-card 등에 shadow 추가
    css = re.sub(
        r'(background\s*:\s*#ffffff\s*;)',
        r'\1\n  ' + CARD_SHADOW,
        css
    )

    # 6. Pretendard import (중복 방지)
    if 'pretendard' not in css.lower():
        css = PRETENDARD_IMPORT + css

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


def process_python_inline(path):
    """api/public.py 인라인 HTML의 스타일도 변환"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Python 파일 안의 <style>...</style> 블록 처리
    def replace_style_block(m):
        return '<style>\n' + transform_style(m.group(1).strip()) + '\n</style>'

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

    # api/public.py 인라인 HTML
    py_path = os.path.join(base, 'api/public.py')
    if process_python_inline(py_path):
        changed.append('api/public.py')

    print(f"변환 완료: {len(changed)}개 파일")
    for f in changed:
        print(f"  ✓ {f}")
