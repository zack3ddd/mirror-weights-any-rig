"""介面翻譯（i18n）測試。

驗證 UI 字串會跟著 Blender 介面語言走：
  英文 → 英文原文
  繁中 / 簡中 → 都顯示繁體中文（阿哲不要簡體）

pgettext_iface 正是 Blender 畫面板 text= 標籤時實際呼叫的函式，
所以用它比對就等同驗證畫面上會顯示什麼。

跑法（每個版本都要）：
  "…/blender.exe" --background --factory-startup --python tests/test_i18n.py
"""

import importlib.util
import os
import sys

import bpy

ADDON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "MirrorWeightsAnyRig", "__init__.py")
spec = importlib.util.spec_from_file_location("mwar", ADDON)
mwar = importlib.util.module_from_spec(spec)
sys.modules["mwar"] = mwar
spec.loader.exec_module(mwar)
mwar.register()

CTX = mwar.I18N_CTX  # 翻譯掛在自訂 context 底下，查詢要帶它


def iface(msgid):
    return bpy.app.translations.pgettext_iface(msgid, CTX)

prefs = bpy.context.preferences
prefs.view.use_translate_interface = True
try:
    prefs.view.use_translate_tooltips = True
except Exception:
    pass

# 代表性字串：英文原文 → 期望繁中
SAMPLES = {
    "Mirror Weights": "鏡像權重",
    "Mirror All Weights": "鏡像全部權重",
    "Mirror Selected Bones' Weights": "鏡像所選骨骼的權重",
    "Naming Convention": "命名模式",
    "Mirror all:": "鏡像全部：",
    "Detected: %s": "偵測到：%s",
    "Symmetry Tolerance": "對稱容差",
}

# background 模式下 language 的 enum_items 可能是空的（3.6/4.5），
# 但仍可直接指派代碼——所以用 try 設定，能設成功的才測。
def try_set(code):
    try:
        prefs.view.language = code
        return prefs.view.language == code
    except Exception:
        return False


results = []
avail = [c for c in ("zh_HANT", "zh_TW", "zh_HANS", "zh_CN") if try_set(c)]
print(f"\nBlender {bpy.app.version_string}｜可設定的中文代碼：{avail}")

# 至少要有一個繁中、一個簡中代碼可用，否則這版本沒被真正測到中文
has_trad = any(c in avail for c in ("zh_HANT", "zh_TW"))
has_simp = any(c in avail for c in ("zh_HANS", "zh_CN"))
results.append(has_trad and has_simp)
if not (has_trad and has_simp):
    print(f"  FAIL 這版本沒有可用的繁中或簡中代碼，中文未被驗證")

CASES = [("en_US", "EN")] + [(c, "ZH") for c in avail]
for lang, kind in CASES:
    try_set(lang) if kind == "ZH" else prefs.view.__setattr__("language", lang)
    for en, zh in SAMPLES.items():
        got = iface(en)
        exp = en if kind == "EN" else zh
        ok = got == exp
        results.append(ok)
        if not ok:
            print(f"  FAIL [{lang}] {en!r} → {got!r}（期望 {exp!r}）")

# 特別點名：選「簡體」時必須顯示繁體（連通用字「Mirror Weights」也不能被內建簡體蓋掉）
simp = next((c for c in ("zh_HANS", "zh_CN") if c in avail), None)
if simp:
    prefs.view.language = simp
    got = iface("Mirror Weights")
    star = got == "鏡像權重"
    results.append(star)
    print(f"  {'PASS' if star else 'FAIL'} ★ 選簡體({simp}) → 'Mirror Weights' 顯示為：{got}（要繁體，不能是简体）")

mwar.unregister()
n_pass, n_all = sum(results), len(results)
print(f"i18n：{n_pass}/{n_all} 通過")
print("RESULT: ALLPASS" if n_pass == n_all else "RESULT: SOMEFAIL")
