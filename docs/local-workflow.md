# 本地运行工作流说明

本文档解释这个项目在本地环境中是如何运行的，以及在真正执行之前，哪些目录和文件需要先准备好。

## 1. 本项目不是纯代码即跑

这个项目的本地运行依赖三类资源：

1. 代码
2. 模型工程目录
3. 本地数据与配置目录

也就是说，光有：

- `backend/`
- `cbct-react/`
- `python/`

还不够。

还需要：

- 可用的 Python 环境
- Java 环境
- Node 环境
- 外部模型目录结构
- 原始 DICOM 数据目录
- 原始 raw 或导出目录
- 两个关键 JSON 文件

## 2. 本地运行的几类关键目录

### A. 原始 DICOM 目录

典型字段：

- `DICOM_ROOT`
- 前端页面中的 `sourceRoot`

它的意义是：

- 用来存放原始病人 DICOM 数据
- 方法一 / 方法二在匹配病人、扫描日期和序列时会读取这里

代码里出现的位置包括：

- `python/config.py`
- `python/method1_workflow.py`
- `python/method2_workflow.py`
- 前端 Method1 / Method2 页面

### B. 工作输出目录

典型字段：

- `WORKSPACE_ROOT`
- 前端页面中的 `workspaceRoot`

它的意义是：

- 用于存放中间产物
- 用于存放匹配结果
- 用于存放插值、配准、centered raw、回插验证结果

当前仓库顶层保留了一个 `workspace/` 目录，但真正本地运行时，工作目录可能来自别的盘符路径。

### C. 旧项目根目录 / 模型工程根目录

典型字段：

- `LEGACY_CBCT_ROOT`
- `MODEL_PROJECT_ROOT`
- `DATA_ROOT`

它的意义是：

- 某些推理逻辑和 merge 逻辑仍依赖旧项目结构
- Python 会从这里找到模型工程目录或数据目录

### D. DICOM 输出目录

典型字段：

- `RESULTS_BASE`
- `dicom-results-dir`

它的意义是：

- 用于存放最终导出的 DICOM 结果

### E. TestPatient / 临时处理目录

典型字段：

- `TEST_PATIENT_ROOT`
- `TMP_DIR`

它们的意义是：

- 存放 merge 后的 3D raw
- 存放中间处理 raw
- 存放 pipeline 临时结果

## 3. 本地运行前必须关注的文件

### `backend/src/main/resources/application.yml`

作用：

- 告诉 Spring 去哪里找 Python
- 告诉 Spring 去哪里找工作目录和处理脚本

### `python/config.py`

作用：

- 告诉 Python 去哪里找模型目录、数据目录、结果目录和 JSON

### `python/patient_params.json`

作用：

- 告诉恢复流程每个病人的路径与空间参数

### `python/Patient_rename.json`

作用：

- 告诉 DICOM 导出流程每个病人的 UID 映射关系

## 4. 四个页面分别依赖什么

### 推理与结果整理页

依赖：

- 模型工程目录
- Python 环境
- 后端启动
- 对应数据集范围可被解析

主要相关目录：

- `model_cstgan/`
- `model_attn_vit/`
- `model_mask/`
- 旧项目根目录

### DICOM 导出页

依赖：

- `patient_params.json`
- `Patient_rename.json`
- 原始 DICOM 根目录
- 原始 raw / 中间 raw 路径
- 已有模型处理结果

### 数据集制作（ORB）页

依赖：

- 原始 DICOM 数据目录
- 工作输出目录
- 能从病人目录里匹配到 CBCT / QACT

### 数据集制作（SITK）页

依赖：

- 原始 DICOM 数据目录
- 工作输出目录
- method1 产生的部分中间结果
- SITK 配准相关依赖

## 5. 本地启动顺序

一个典型的本地运行顺序通常是：

1. 准备 Python 环境
2. 确认 `application.yml` 路径
3. 确认 `python/config.py` 路径
4. 确认模型目录存在
5. 确认原始 DICOM 目录存在
6. 确认 JSON 配置存在
7. 启动后端
8. 启动前端
9. 打开网页逐页运行

## 6. 为什么别人拿到当前仓库仍然不能直接复现

因为当前仓库没有包含这些关键内容：

- 原始 DICOM 数据
- 训练好的模型权重
- 运行后的 `results`
- `workspace` 中间产物
- 完整外部环境

换句话说，这个仓库更像：

- 本地研究系统的代码快照

而不是：

- 完整公开复现实验包

## 7. 推荐理解顺序

如果想理解项目怎样在本地跑起来，建议按下面顺序阅读：

1. `README.md`
2. `docs/architecture.md`
3. `docs/directory-guide.md`
4. `docs/hardcoded-configs.md`
5. 再回到代码里看：
   - `backend/src/main/resources/application.yml`
   - `python/config.py`
   - `python/spring_bridge.py`

## 8. 一句话总结

这个项目的运行逻辑是：

前端收集参数，后端转发请求，Python 执行工作流，模型目录提供推理逻辑，`workspace` 保存中间产物，`DICOM_results` 保存最终导出结果。
