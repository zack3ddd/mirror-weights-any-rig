bl_info = {
    "name": "MirrorWeightsAnyRig",
    "author": "Zack3D",
    "version": (0, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > N 面板 > 鏡像權重",
    "description": "在任何命名慣例的骨架上鏡像權重（Mixamo、Character Creator、VRM、Biped、Daz…），不改動任何骨骼或群組名稱",
    "category": "Rigging",
}

import re

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Vector
from mathutils.kdtree import KDTree


# ─────────────────────────────────────────────────────────────
# 命名慣例：把群組名拆成（左右中性的識別碼, 側邊）
#
# 為什麼不用 Blender 原生的 bpy.utils.flip_name：實測（4.5）它只認
# 「字串最開頭或最結尾」的 Left/Right/L/R，中間一律不認。所以
# mixamorig:LeftArm、CC_Base_L_Upperarm、Bip001 L UpperArm、lShin
# 全部翻不動。這裡自己拆。
# ─────────────────────────────────────────────────────────────

_SEP = r"[._\- ]"

# 每個 pattern 必須有 named group: side；pre / post 可有可無。
_PATTERNS = {
    # arm.L / L_arm / DEF-upper_arm.L —— Blender / Rigify / ARP / UE5
    "BLENDER": (
        re.compile(r"^(?P<pre>.*" + _SEP + r")(?P<side>[LlRr])(?P<post>)$"),
        re.compile(r"^(?P<pre>)(?P<side>[LlRr])(?P<post>" + _SEP + r".+)$"),
    ),
    # mixamorig:LeftArm / LeftArm / Character1_LeftArm —— Mixamo / Maya HumanIK
    "LEFTRIGHT": (
        re.compile(r"^(?P<pre>.*?)(?P<side>Left|Right|LEFT|RIGHT|left|right)(?P<post>.+)$"),
        re.compile(r"^(?P<pre>.+?)(?P<side>Left|Right|LEFT|RIGHT|left|right)(?P<post>)$"),
    ),
    # CC_Base_L_Upperarm / J_Bip_L_UpperArm / Bip001 L UpperArm / Hand_L_01
    "MIDDLE": (
        re.compile(r"^(?P<pre>.*" + _SEP + r")(?P<side>[LlRr])(?P<post>" + _SEP + r".+)$"),
    ),
    # lShin / rThighTwist —— Daz Genesis（無分隔符）
    "DAZ": (
        re.compile(r"^(?P<pre>)(?P<side>[lr])(?P<post>[A-Z].+)$"),
    ),
}

_PRESET_ITEMS = [
    ("AUTO", "自動偵測", "掃描頂點群組名稱，自動判斷是哪一種命名慣例"),
    ("BLENDER", "Blender / Rigify / ARP / UE5", "arm.L、DEF-upper_arm.L、thigh_l"),
    ("LEFTRIGHT", "Mixamo / Maya HumanIK", "mixamorig:LeftArm、Character1_LeftArm"),
    ("MIDDLE", "Character Creator / VRM / Biped", "CC_Base_L_Upperarm、J_Bip_L_UpperArm、Bip001 L UpperArm"),
    ("DAZ", "Daz Genesis", "lShin、rForearmBend"),
]

# 偵測順序：越專一的排前面，避免 MIDDLE 把 BLENDER 的名字搶走。
_AUTO_ORDER = ("LEFTRIGHT", "DAZ", "MIDDLE", "BLENDER")


def _side_of(token):
    return "L" if token.lower() in ("left", "l") else "R"


def _flip_token(token):
    low = token.lower()
    other = {"left": "right", "right": "left", "l": "r", "r": "l"}.get(low)
    if other is None:
        return None
    if token.isupper():
        return other.upper()
    if token[0].isupper():
        return other.capitalize()
    return other


def split_name(name, preset):
    """回傳 (key, side, rebuild) 或 None。

    key    左右中性的識別碼，兩邊配對用
    side   'L' / 'R'
    """
    for pat in _PATTERNS.get(preset, ()):
        m = pat.match(name)
        if not m:
            continue
        token = m.group("side")
        other = _flip_token(token)
        if other is None:
            continue
        pre = m.group("pre") or ""
        post = m.group("post") or ""
        key = (preset, pre, post)
        return key, _side_of(token), pre + other + post
    return None


def pair_groups(ob, preset):
    """回傳 (pairs, centers)。

    pairs   [(左群組, 右群組), ...]
    centers [中線群組, ...]（拆不出左右的，如 Hips / Spine）
    """
    sided = {}
    centers = []
    for g in ob.vertex_groups:
        r = split_name(g.name, preset)
        if r is None:
            centers.append(g)
            continue
        key, side, partner_name = r
        sided.setdefault(key, {})[side] = g

    pairs = []
    for key, d in sided.items():
        L, R = d.get("L"), d.get("R")
        if L and R:
            pairs.append((L, R))
        else:
            # 只有單邊 → 對面根本不存在，當中線處理不會有幫助，直接忽略
            centers.extend([g for g in (L, R) if g])
    return pairs, centers


def detect_preset(ob):
    """挑出能配出最多對的慣例。"""
    best, best_n = "BLENDER", 0
    for p in _AUTO_ORDER:
        pairs, _ = pair_groups(ob, p)
        if len(pairs) > best_n:
            best, best_n = p, len(pairs)
    return best, best_n


def resolve_preset(ob, settings):
    if settings.preset == "AUTO":
        return detect_preset(ob)[0]
    return settings.preset


# ─────────────────────────────────────────────────────────────
# 頂點鏡像對應表（沿物體局部空間 X=0 翻面）
# ─────────────────────────────────────────────────────────────

def build_mirror_map(me, tol):
    kd = KDTree(len(me.vertices))
    for v in me.vertices:
        kd.insert(v.co, v.index)
    kd.balance()

    mmap = {}
    for v in me.vertices:
        co, idx, dist = kd.find(Vector((-v.co.x, v.co.y, v.co.z)))
        if dist is not None and dist <= tol:
            mmap[v.index] = idx
    return mmap


def detect_l_sign(ob, pairs):
    """角色的左邊落在 +X 還是 -X？

    不要寫死。Blender 慣例是角色面向 -Y、左手在 +X，但匯入來的模型
    朝向不保證。猜錯的話中線群組會往錯的半邊寫，而且是靜默的。
    這裡直接看 L 側群組的權重實際長在哪一側，回傳 +1 或 -1。
    """
    sign_of = {}
    for L, R in pairs:
        sign_of[L.index] = 1.0
        sign_of[R.index] = -1.0

    acc = 0.0
    for v in ob.data.vertices:
        x = v.co.x
        if x == 0.0:
            continue
        for ge in v.groups:
            s = sign_of.get(ge.group)
            if s is not None:
                acc += s * ge.weight * x
    return 1.0 if acc >= 0.0 else -1.0


# ─────────────────────────────────────────────────────────────
# 權重搬移
# ─────────────────────────────────────────────────────────────

def _weights_of(ob, group, vert_indices):
    gi = group.index
    out = {}
    for i in vert_indices:
        for ge in ob.data.vertices[i].groups:
            if ge.group == gi:
                out[i] = ge.weight
                break
    return out


def copy_mirrored(ob, src, dst, mmap, allowed):
    """把 src 的權重沿 X 鏡像後寫進 dst。

    allowed 為 None 代表目的地不設限；否則只寫入該集合內的**目的地**頂點，
    集合外的維持原樣。dst 在會被寫到的範圍內先清空，這樣來源沒有權重的
    地方才不會留下舊權重的殘影。回傳寫入的頂點數。
    """
    # 一定要先把來源讀出來——src 可能就是 dst（中線群組翻面蓋自己）。
    src_w = _weights_of(ob, src, mmap.keys())

    clear = [di for di in mmap.values()
             if allowed is None or di in allowed]
    if clear:
        dst.remove(clear)

    written = 0
    for si, w in src_w.items():
        di = mmap.get(si)
        if di is None:
            continue
        if allowed is not None and di not in allowed:
            continue
        dst.add([di], w, "REPLACE")
        written += 1
    return written


def _posebone_has_select():
    """骨骼選取狀態放在哪，Blender 5.0 前後剛好相反：

        3.6 / 4.x   Bone.select 有，PoseBone.select 沒有
        5.0 / 5.2   Bone.select 沒有，PoseBone.select 有

    偵測屬性存不存在，不要比對版本號——版本號會再變，屬性偵測不會錯。
    """
    return "select" in bpy.types.PoseBone.bl_rna.properties


def selected_bone_names(arm):
    if not arm.pose:
        return []
    if _posebone_has_select():
        return [pb.name for pb in arm.pose.bones if pb.select]
    return [pb.name for pb in arm.pose.bones if pb.bone.select]


def selected_vert_filter(ob):
    """權重繪製的頂點選取遮罩開著時，只動選到的頂點。"""
    me = ob.data
    if ob.mode == "PAINT_WEIGHT" and me.use_paint_mask_vertex:
        sel = {v.index for v in me.vertices if v.select}
        if sel:
            return sel
    return None


def half_filter(ob, x_sign, base):
    """限制在 X 軸某一側（x_sign 為 +1 或 -1）。中線群組專用——
    左右成對的群組不需要，因為它們寫進的是另一個群組，不會傷到來源。"""
    keep = {v.index for v in ob.data.vertices
            if v.co.x * x_sign > 1e-6}
    return keep if base is None else (keep & base)


# ─────────────────────────────────────────────────────────────
# Operators
# ─────────────────────────────────────────────────────────────

class _MirrorBase:
    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob is not None and ob.type == "MESH" and len(ob.vertex_groups) > 0

    def _prep(self, context):
        ob = context.object
        st = context.scene.mwar
        preset = resolve_preset(ob, st)
        mmap = build_mirror_map(ob.data, st.tolerance)
        if not mmap:
            self.report({"ERROR"}, "找不到任何鏡像頂點對——模型可能不對稱，或容差太小")
            return None
        return ob, st, preset, mmap


class MWAR_OT_mirror_selected(_MirrorBase, Operator):
    bl_idname = "mwar.mirror_selected"
    bl_label = "鏡像所選骨骼的權重"
    bl_description = "以所選骨骼為來源，把權重鏡像到對面的骨骼上"
    bl_options = {"REGISTER", "UNDO"}

    center_direction: EnumProperty(
        name="中線骨骼方向",
        description="選到 Hips、Spine 這種中線骨骼時，要以哪一側為準翻面",
        items=[("N2P", "-X → +X", ""), ("P2N", "+X → -X", "")],
        default="N2P",
    )

    def execute(self, context):
        prep = self._prep(context)
        if prep is None:
            return {"CANCELLED"}
        ob, st, preset, mmap = prep

        arm = next((m.object for m in ob.modifiers
                    if m.type == "ARMATURE" and m.object), None)
        if arm is None:
            self.report({"ERROR"}, "這個物件沒有骨架修改器")
            return {"CANCELLED"}

        sel = selected_bone_names(arm)
        if not sel:
            self.report({"ERROR"}, "沒有選到骨骼——請在權重繪製模式下按住 Ctrl 點選骨骼")
            return {"CANCELLED"}

        vfilter = selected_vert_filter(ob)
        done = 0
        skipped = []
        for bname in sel:
            src = ob.vertex_groups.get(bname)
            if src is None:
                skipped.append(bname)
                continue
            r = split_name(bname, preset)
            if r is None:
                # 中線骨骼：沒有對面可以給，改成沿 X 翻面蓋自己
                dst_x = 1.0 if self.center_direction == "N2P" else -1.0
                allowed = half_filter(ob, dst_x, vfilter)
                copy_mirrored(ob, src, src, mmap, allowed)
                done += 1
                continue
            _, side, partner = r
            dst = ob.vertex_groups.get(partner)
            if dst is None:
                skipped.append(bname)
                continue
            # 寫進的是另一個群組，來源不會被動到，不必限制半邊
            copy_mirrored(ob, src, dst, mmap, vfilter)
            done += 1

        ob.data.update()
        msg = f"已鏡像 {done} 個群組（慣例：{preset}）"
        if skipped:
            msg += f"；找不到對應群組而略過 {len(skipped)} 個"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class MWAR_OT_mirror_all(_MirrorBase, Operator):
    bl_idname = "mwar.mirror_all"
    bl_label = "鏡像全部權重"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        name="方向",
        items=[("N2P", "-X → +X", "以 -X 側的權重為準，蓋掉 +X 側"),
               ("P2N", "+X → -X", "以 +X 側的權重為準，蓋掉 -X 側")],
        default="N2P",
    )

    @classmethod
    def description(cls, context, props):
        # 講軸向，不講「左右」。角色的左邊在前視圖底下會出現在畫面右邊，
        # 「左→右」兩種讀法剛好相反，是最容易搞混的講法。
        if props.direction == "N2P":
            return "以 -X 側的權重為準，鏡像蓋掉 +X 側。前視圖（Numpad 1）下 -X 在畫面左側"
        return "以 +X 側的權重為準，鏡像蓋掉 -X 側。前視圖（Numpad 1）下 +X 在畫面右側"

    def execute(self, context):
        prep = self._prep(context)
        if prep is None:
            return {"CANCELLED"}
        ob, st, preset, mmap = prep

        pairs, centers = pair_groups(ob, preset)
        if not pairs:
            self.report({"ERROR"},
                        f"用「{preset}」慣例配不出任何左右成對的群組——請改選正確的命名模式")
            return {"CANCELLED"}

        vfilter = selected_vert_filter(ob)
        src_x = -1.0 if self.direction == "N2P" else 1.0
        # L 側群組長在 l_sign 那一側；來源要挑「長在 src_x 那一側」的那一個
        l_sign = detect_l_sign(ob, pairs)

        for L, R in pairs:
            src, dst = (L, R) if l_sign == src_x else (R, L)
            # 寫進的是另一個群組，來源不會被動到，不必限制半邊
            copy_mirrored(ob, src, dst, mmap, vfilter)

        n_center = 0
        if st.include_center:
            allowed = half_filter(ob, -src_x, vfilter)
            for g in centers:
                copy_mirrored(ob, g, g, mmap, allowed)
                n_center += 1

        ob.data.update()
        msg = f"已鏡像 {len(pairs)} 對群組（慣例：{preset}）"
        if n_center:
            msg += f"＋{n_center} 個中線群組"
        self.report({"INFO"}, msg)
        return {"FINISHED"}


# ─────────────────────────────────────────────────────────────
# Settings / Panel
# ─────────────────────────────────────────────────────────────

class MWAR_Settings(PropertyGroup):
    preset: EnumProperty(
        name="命名模式",
        description="骨骼與頂點群組的左右命名慣例",
        items=_PRESET_ITEMS,
        default="AUTO",
    )
    tolerance: FloatProperty(
        name="對稱容差",
        description="找鏡像頂點時允許的位置誤差。模型稍微不對稱時可調大",
        default=0.0001, min=0.0, max=1.0, precision=5, step=0.01,
    )
    include_center: BoolProperty(
        name="一併處理中線群組",
        description="Hips、Spine 這種拆不出左右的群組，沿 X 翻面蓋到自己身上",
        default=True,
    )


class MWAR_PT_panel(Panel):
    bl_label = "鏡像權重"
    bl_idname = "MWAR_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "鏡像權重"

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob is not None and ob.type == "MESH"

    def draw(self, context):
        layout = self.layout
        ob = context.object
        st = context.scene.mwar

        col = layout.column()
        col.prop(st, "preset")

        if st.preset == "AUTO" and len(ob.vertex_groups):
            detected, n = detect_preset(ob)
            label = next((i[1] for i in _PRESET_ITEMS if i[0] == detected), detected)
            box = layout.box()
            if n:
                box.label(text=f"偵測到：{label}", icon="CHECKMARK")
                box.label(text=f"配出 {n} 對左右群組")
            else:
                box.label(text="認不出命名慣例", icon="ERROR")
                box.label(text="請手動指定命名模式")

        layout.separator()
        layout.operator("mwar.mirror_selected", icon="BONE_DATA")

        col = layout.column(align=True)
        col.label(text="鏡像全部：")
        row = col.row(align=True)
        row.operator("mwar.mirror_all", text="-X → +X").direction = "N2P"
        row.operator("mwar.mirror_all", text="+X → -X").direction = "P2N"

        layout.separator()
        col = layout.column(align=True)
        col.prop(st, "include_center")
        col.prop(st, "tolerance")


classes = (
    MWAR_Settings,
    MWAR_OT_mirror_selected,
    MWAR_OT_mirror_all,
    MWAR_PT_panel,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.mwar = PointerProperty(type=MWAR_Settings)


def unregister():
    del bpy.types.Scene.mwar
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
