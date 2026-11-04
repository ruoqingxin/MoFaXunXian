# 修仙宗门搜打撤 - 微信小游戏运行缓存资源

## 来源

- 小游戏 AppID：`wx3d70e2eb74daa3d0`
- 运行缓存：`C:\Users\Administrator\AppData\Roaming\Tencent\xwechat\radium\users\b6421f66bc1f054b98db3feb806ce9c8\applet`
- 资源格式：UnityFS / Unity 2022.3.62f1
- 抓取时间：2026-11-04 22:53（Asia/Shanghai）

本目录来自该游戏本次运行期间已写入磁盘的运行包和动态下载缓存，不是项目工程。

## 目录

- `images/sprites`：620 个已经裁切并命名的 Sprite，通常是最适合直接查看或使用的图片。
- `images/textures`：362 个可解码的 Texture2D 图集或原图。
- `audio`：6 个 AudioClip，保留为原始 M4A/MP4 音频数据。
- `fonts`：8 个 TTF 字体文件。
- `meshes`：13 个 OBJ 网格。
- `text`：15 个 TextAsset，包括 13 个游戏配置表。
- `data/json`：从纯文本 TextAsset 整理出的 13 个 JSON 配置。
- `metadata`：每个 Unity 对象的结构化元数据。
- `raw`：每个 Unity 对象的原始序列化数据。
- `manifest.csv`：全部对象的来源、名称、类型、PathID 和导出文件清单。
- `summary.json`：容器和对象类型统计。
- `validation.json`：图片、音频、字体、网格的可打开性校验结果。

## 校验结果

- Unity 对象：8,355 个
- 导出文件：16,304 个
- PNG：982 个，982 个可正常打开
- 音频：6 个，6 个识别为 M4A/MP4
- 字体：8 个，8 个具有有效 TrueType/OpenType 文件头
- 网格：13 个，13 个为有效 OBJ 文本
- 空文件：0 个

清单中有 12 个 `metadata_only` 项，它们是 Unity 内宽高均为 0 的字体占位纹理；其元数据和原始数据已保留，没有可导出的像素图。

## 说明

运行缓存只包含游戏本次运行期间实际下载或加载的资源。以后访问更多界面时，游戏可能继续下载新的 `.ab` 资源包；重新抓取缓存并运行解析流程即可补充。
