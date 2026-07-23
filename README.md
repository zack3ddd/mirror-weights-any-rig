<!-- 封面圖：在 GitHub 網頁編輯此檔，把封面圖拖到這一行上方，會自動上傳並產生 <img> 連結 -->

# MirrorWeightsAnyRig

**English** · [繁體中文](#繁體中文)

Models you download from elsewhere (Mixamo, Character Creator, VRM, 3ds Max, Daz…) often won't mirror vertex weights in Blender. This add-on mirrors them in one click, without renaming a single bone or vertex group.

> Made by Zack3D (with AI assistance).

## Why does native mirroring fail?

Blender's mirror only recognizes `Left`/`Right`/`L`/`R` when it sits at the very start or very end of a name. Many rigs aren't named that way:

| Rig | Example bone | Native mirror |
|---|---|---|
| Mixamo | `mixamorig:LeftArm` | ❌ blocked by the `mixamorig:` prefix |
| Character Creator | `CC_Base_L_Upperarm` | ❌ L sits in the middle |
| VRoid / VRM | `J_Bip_L_UpperArm` | ❌ L sits in the middle |
| 3ds Max Biped | `Bip001 L UpperArm` | ❌ L sits in the middle |
| Daz Genesis | `lShin` | ❌ no separator |
| Rigify / Auto-Rig Pro / UE5 | `upper_arm.L`, `thigh_l` | ✅ already mirrorable |

As long as L/R isn't at the head or tail of the name, native mirroring can't see it. The problem is the name, not the weights. This add-on understands these naming conventions and works around that limit.

## Features

- **Auto-detects the naming convention:** Mixamo, Rigify, Auto-Rig Pro, UE5 / MetaHuman, Character Creator, VRM / VRoid, 3ds Max Biped, Daz Genesis, Maya HumanIK. Usually no need to pick manually
- **Mirror the selected bones' weights:** in weight-paint mode, mirror exactly the bones you selected
- **Mirror all weights:** copy one whole side to the other in one click, choose `-X → +X` or `+X → -X`
- **Never touches names:** everything happens only at the moment of the operation; bone and vertex-group names stay exactly as they were, so re-applying official animations later (for example with Mixamo tools) is completely unaffected
- **Handles center bones:** Hips, Spine and other center-line bones are mirrored across the center
- **Adjustable symmetry tolerance:** real character models are slightly asymmetric, so raise the tolerance when no matching point is found

## Installation

1. Download the latest `.zip` from **Releases** on the right (no need to unzip)
2. Open Blender → top menu **Edit › Preferences**
3. Click **Add-ons** on the left → **Install from Disk…** (top-right)
4. Select the `.zip` you downloaded → install
5. Tick the checkbox next to "MirrorWeightsAnyRig" to enable it

## Usage

1. Select the rigged mesh → N-panel "Mirror Weights" tab
2. Leave the naming mode on "Auto-detect"; the panel shows the rig it recognized and how many pairs it matched
3. To mirror everything at once, press **`-X → +X`** or **`+X → -X`** (axis-based rather than "left/right", so the viewing angle can't confuse you)
4. To mirror only a few bones: enter weight-paint mode, select the bones, then press "Mirror the selected bones' weights"

> It uses the object's local X axis. In front view (Numpad 1), `-X` is on the left of your screen and `+X` is on the right.

## Compatibility

- Blender 3.6 / 4.5 / 5.0 / 5.2 LTS (all tested)

## License

Released under the **GNU GPL**. Author: Zack3D.

---

## 繁體中文

[English ↑](#mirrorweightsanyrig)

# MirrorWeightsAnyRig（跨命名骨架的鏡像權重）

Mixamo、Character Creator、VRM、3ds Max、Daz⋯⋯ 這些從外面下載回來的模型，在 Blender 裡按「鏡像頂點群組」常常沒反應。這個外掛讓它們一鍵鏡像權重，而且完全不改動任何骨骼或頂點群組的名字。

> 由 Zack3D 製作（AI 協助）。

## 為什麼原生鏡像會失敗？

Blender 的鏡像功能只認得放在名字最開頭或最結尾的 `Left`／`Right`／`L`／`R`。可是很多骨架不是這樣命名：

| 骨架 | 骨骼名範例 | Blender 原生 |
|---|---|---|
| Mixamo | `mixamorig:LeftArm` | ❌ 卡在 `mixamorig:` 前綴 |
| Character Creator | `CC_Base_L_Upperarm` | ❌ L 夾在中間 |
| VRoid / VRM | `J_Bip_L_UpperArm` | ❌ L 夾在中間 |
| 3ds Max Biped | `Bip001 L UpperArm` | ❌ L 夾在中間 |
| Daz Genesis | `lShin` | ❌ 沒有分隔符 |
| Rigify / Auto-Rig Pro / UE5 | `upper_arm.L`、`thigh_l` | ✅ 本來就能鏡像 |

只要 L/R 不在名字的頭或尾，原生鏡像就認不得。問題出在名字，不在權重。這個外掛自己看懂這些命名，繞過這道限制。

## 功能

- **自動偵測命名慣例**：Mixamo、Rigify、Auto-Rig Pro、UE5 / MetaHuman、Character Creator、VRM / VRoid、3ds Max Biped、Daz Genesis、Maya HumanIK 都認得，通常不用手動選
- **鏡像所選骨骼的權重**：在權重繪製模式下選哪幾根骨骼，就鏡像那幾根
- **鏡像全部權重**：一鍵把一整側複製到另一側，可選 `-X → +X` 或 `+X → -X`
- **名字一個字都不動**：全程只在運算當下處理，骨骼與頂點群組名稱維持原樣。之後要用 Mixamo 等外掛重新套用官方動作，也完全不受影響
- **中線骨骼一併處理**：Hips、Spine 這種沒有左右之分的骨骼，沿中線翻面對稱
- **對稱容差可調**：真人模型多少有點不對稱，找不到對應點時把容差調大即可

## 安裝教學

1. 到本頁右側 **Releases** 下載最新的 `.zip`（不用解壓縮）
2. 打開 Blender → 上方選單 **編輯 (Edit) › 偏好設定 (Preferences)**
3. 左側點 **附加元件 (Add-ons)** → 右上角 **從磁碟安裝 (Install from Disk…)**
4. 選剛剛下載的 `.zip` → 安裝
5. 在清單中把「MirrorWeightsAnyRig」前面的**核取方塊打勾**啟用

## 使用

1. 選到有骨架的網格 → N 面板「鏡像權重」分頁
2. 命名模式保持「自動偵測」即可，面板會顯示認出的骨架與配對數
3. 想全部一次鏡像，就按 **`-X → +X`** 或 **`+X → -X`**（用軸向而非「左右」，才不會被視角搞混）
4. 只想鏡像某幾根：進權重繪製模式選好骨骼 → 按「鏡像所選骨骼的權重」

> 用的是物體局部空間的 X 軸。前視圖（Numpad 1）底下，`-X` 在畫面左側、`+X` 在畫面右側。

## 教學

[![YouTube 影片](https://img.youtube.com/vi/nzocxnqoJeA/maxresdefault.jpg)](https://www.youtube.com/watch?v=nzocxnqoJeA)

## 對應版本

- Blender 3.6 / 4.5 / 5.0 / 5.2 LTS（皆通過測試）

## 授權

以 **GNU GPL** 釋出。作者：Zack3D。
