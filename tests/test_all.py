"""MirrorWeightsAnyRig 全套回歸測試（headless）。

跑法（每個要支援的 Blender 版本都要跑）：
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" \
      --background --factory-startup --python tests/test_all.py

改動 __init__.py 後一定重跑。教訓：只在一個版本測過就交出去，
Blender 5.0 拿掉 Bone.select 這種事會直接炸在使用者臉上。
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

RESULTS = []


def check(label, got, exp):
    if isinstance(got, float) and isinstance(exp, float):
        ok = abs(got - exp) < 1e-5
    else:
        ok = got == exp
    RESULTS.append(ok)
    print(f"    {'PASS' if ok else 'FAIL'}  {label:34s} got={got!r} exp={exp!r}")


def w(ob, gname, i):
    g = ob.vertex_groups[gname]
    return next((ge.weight for ge in ob.data.vertices[i].groups
                 if ge.group == g.index), None)


# ─────────────────────────────────────────────────────────────
# 1. 命名慣例自動偵測
# ─────────────────────────────────────────────────────────────
RIGS = {
    "Mixamo":   (["mixamorig:Hips", "mixamorig:Spine", "mixamorig:LeftArm", "mixamorig:RightArm",
                  "mixamorig:LeftHandIndex3", "mixamorig:RightHandIndex3",
                  "mixamorig:LeftUpLeg", "mixamorig:RightUpLeg"], "LEFTRIGHT", 3),
    "Rigify":   (["spine", "DEF-upper_arm.L", "DEF-upper_arm.R", "thumb.01.L", "thumb.01.R"],
                 "BLENDER", 2),
    "ARP":      (["c_root_master.x", "thigh.l", "thigh.r", "c_hand_ik.l", "c_hand_ik.r"],
                 "BLENDER", 2),
    "UE5":      (["pelvis", "spine_01", "thigh_l", "thigh_r", "upperarm_l", "upperarm_r"],
                 "BLENDER", 2),
    "CC":       (["CC_Base_Hip", "CC_Base_L_Upperarm", "CC_Base_R_Upperarm",
                  "CC_Base_L_Thigh", "CC_Base_R_Thigh"], "MIDDLE", 2),
    "VRM":      (["J_Bip_C_Hips", "J_Bip_L_UpperArm", "J_Bip_R_UpperArm",
                  "J_Bip_L_UpperLeg", "J_Bip_R_UpperLeg"], "MIDDLE", 2),
    "Biped":    (["Bip001 Pelvis", "Bip001 L UpperArm", "Bip001 R UpperArm",
                  "Bip001 L Thigh", "Bip001 R Thigh"], "MIDDLE", 2),
    "Daz":      (["hip", "abdomen", "lShin", "rShin", "lForearmBend", "rForearmBend"],
                 "DAZ", 2),
    "HumanIK":  (["Character1_Hips", "Character1_LeftArm", "Character1_RightArm"],
                 "LEFTRIGHT", 1),
}

print("\n[1] 命名慣例自動偵測")
for rig, (names, exp_preset, exp_pairs) in RIGS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("M")
    me.from_pydata([(0, 0, 0)], [], [])
    me.update()
    ob = bpy.data.objects.new("O", me)
    bpy.context.collection.objects.link(ob)
    for n in names:
        ob.vertex_groups.new(name=n)
    det, _ = mwar.detect_preset(ob)
    pairs, _ = mwar.pair_groups(ob, det)
    check(f"{rig} 偵測", det, exp_preset)
    check(f"{rig} 配對數", len(pairs), exp_pairs)


# ─────────────────────────────────────────────────────────────
# 2. 權重搬移（兩種朝向都要）
# ─────────────────────────────────────────────────────────────
XS = [-3., -2., -1., 0., 1., 2., 3.]


NEG_V = [0, 1, 2]        # x = -3, -2, -1
POS_V = [6, 5, 4]        # x = +3, +2, +1（與 NEG_V 逐項互為鏡像）


def build_mesh(l_at_plus):
    """按鈕講的是軸向（-X / +X），所以測試也一律以軸向描述，不講「左右」。

    l_at_plus 控制角色朝向：True＝角色左邊在 +X（Blender 慣例），
    False＝相反。好權重固定放 -X 側，垃圾固定放 +X 側。
    回傳 (ob, -X 側的群組名, +X 側的群組名)。
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    me = bpy.data.meshes.new("M")
    me.from_pydata([(x, 0., 0.) for x in XS],
                   [(i, i + 1) for i in range(len(XS) - 1)], [])
    me.update()
    ob = bpy.data.objects.new("O", me)
    bpy.context.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.vertex_groups.new(name="mixamorig:LeftArm")
    ob.vertex_groups.new(name="mixamorig:RightArm")
    S = ob.vertex_groups.new(name="mixamorig:Spine")

    neg_g = "mixamorig:RightArm" if l_at_plus else "mixamorig:LeftArm"
    pos_g = "mixamorig:LeftArm" if l_at_plus else "mixamorig:RightArm"

    ob.vertex_groups[neg_g].add([NEG_V[0]], 0.20, 'REPLACE')
    ob.vertex_groups[neg_g].add([NEG_V[1]], 0.60, 'REPLACE')
    ob.vertex_groups[neg_g].add([NEG_V[2]], 1.00, 'REPLACE')
    ob.vertex_groups[pos_g].add([POS_V[1]], 0.99, 'REPLACE')   # 垃圾，驗證會被清掉
    ob.vertex_groups[pos_g].add([POS_V[0]], 0.11, 'REPLACE')
    S.add([NEG_V[1]], 0.50, 'REPLACE')
    S.add([3], 1.00, 'REPLACE')
    return ob, neg_g, pos_g


print("\n[2] 權重搬移（軸向）")
for l_at_plus in (True, False):
    tag = "左在+X" if l_at_plus else "左在-X"
    ob, neg_g, pos_g = build_mesh(l_at_plus)
    check(f"{tag} 側向偵測",
          mwar.detect_l_sign(ob, mwar.pair_groups(ob, 'LEFTRIGHT')[0]),
          1.0 if l_at_plus else -1.0)
    bpy.context.scene.mwar.preset = 'AUTO'
    bpy.ops.mwar.mirror_all(direction='N2P')
    check(f"{tag} -X 來源完好", w(ob, neg_g, NEG_V[0]), 0.20)
    check(f"{tag} +X 鏡像對位", w(ob, pos_g, POS_V[0]), 0.20)
    check(f"{tag} +X 垃圾清除", w(ob, pos_g, POS_V[1]), 0.60)
    check(f"{tag} -X 來源沒被污染", w(ob, neg_g, POS_V[0]), None)
    check(f"{tag} 中線翻到 +X", w(ob, "mixamorig:Spine", POS_V[1]), 0.50)
    check(f"{tag} 中線 -X 保留", w(ob, "mixamorig:Spine", NEG_V[1]), 0.50)
    check(f"{tag} 中線正中保留", w(ob, "mixamorig:Spine", 3), 1.00)

# 反方向：+X → -X，應該把 +X 的垃圾蓋到 -X 上
for l_at_plus in (True, False):
    tag = "左在+X" if l_at_plus else "左在-X"
    ob, neg_g, pos_g = build_mesh(l_at_plus)
    bpy.context.scene.mwar.preset = 'AUTO'
    bpy.ops.mwar.mirror_all(direction='P2N')
    check(f"{tag} P2N +X 垃圾蓋到 -X", w(ob, neg_g, NEG_V[1]), 0.99)
    check(f"{tag} P2N +X 來源完好", w(ob, pos_g, POS_V[1]), 0.99)
    check(f"{tag} P2N -X 舊權重被清掉", w(ob, neg_g, NEG_V[2]), None)


# ─────────────────────────────────────────────────────────────
# 3. 鏡像所選骨骼 ＋ 名稱零改動
# ─────────────────────────────────────────────────────────────
print("\n[3] 鏡像所選骨骼（需要真骨架）＋ 名稱零改動")
BONES = ["mixamorig:Hips", "mixamorig:LeftArm", "mixamorig:RightArm"]
bpy.ops.wm.read_factory_settings(use_empty=True)
ad = bpy.data.armatures.new("A")
arm = bpy.data.objects.new("Arm", ad)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for i, n in enumerate(BONES):
    b = ad.edit_bones.new(n)
    b.head = (i, 0, 0)
    b.tail = (i, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')

me = bpy.data.meshes.new("M")
me.from_pydata([(x, 0., 0.) for x in XS], [(i, i + 1) for i in range(len(XS) - 1)], [])
me.update()
ob = bpy.data.objects.new("O", me)
bpy.context.collection.objects.link(ob)
ob.modifiers.new("Armature", "ARMATURE").object = arm
for n in BONES:
    ob.vertex_groups.new(name=n)
ob.vertex_groups["mixamorig:LeftArm"].add([4], 1.0, 'REPLACE')
ob.vertex_groups["mixamorig:LeftArm"].add([5], 0.5, 'REPLACE')
ob.vertex_groups["mixamorig:RightArm"].add([1], 0.77, 'REPLACE')

vg_before = [g.name for g in ob.vertex_groups]
bone_before = [b.name for b in ad.bones]

# 選取狀態的位置在 5.0 前後相反，測試本身也得兩邊都會設
for pb in arm.pose.bones:
    want = (pb.name == "mixamorig:LeftArm")
    if mwar._posebone_has_select():
        pb.select = want
    else:
        pb.bone.select = want
check("selected_bone_names 讀得到", mwar.selected_bone_names(arm), ["mixamorig:LeftArm"])

bpy.context.view_layer.objects.active = ob
bpy.context.scene.mwar.preset = 'AUTO'
r = bpy.ops.mwar.mirror_selected()
check("operator 回報", r, {'FINISHED'})
check("右臂 x=-1 得到 1.0", w(ob, "mixamorig:RightArm", 2), 1.0)
check("右臂 x=-2 得到 0.5", w(ob, "mixamorig:RightArm", 1), 0.5)
check("左臂來源沒動", w(ob, "mixamorig:LeftArm", 4), 1.0)
check("★ 頂點群組名稱零改動", [g.name for g in ob.vertex_groups], vg_before)
check("★ 骨骼名稱零改動", [b.name for b in ad.bones], bone_before)

mwar.unregister()

n_pass = sum(RESULTS)
n_all = len(RESULTS)
print(f"\n{'=' * 46}")
print(f"Blender {bpy.app.version_string}：{n_pass}/{n_all} 通過")
print("RESULT: ALLPASS" if n_pass == n_all else "RESULT: SOMEFAIL")
