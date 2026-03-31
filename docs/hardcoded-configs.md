# 硬编码路径与配置说明

这个项目当前是一个典型的“可用本地研究环境”仓库，而不是完全参数化、可即插即用的通用模板。因此，项目里存在不少硬编码路径和环境耦合点。

本文档的目的就是把这些地方集中解释清楚。

## 1. 最重要的配置中心

### `backend/src/main/resources/application.yml`

这是 Spring Boot 侧的路径配置中心。

当前里面直接写了很多绝对路径，例如：

- Python 可执行文件路径
- Python 工作目录
- Python bridge 脚本路径
- 项目根目录
- `workspace` 路径
- 旧项目根目录
- 数据目录
- 测试病人目录
- DICOM 结果目录
- 原始 raw / DICOM 根目录
- 两个 JSON 配置文件路径
- `process_pipeline.py` 路径
- `extract_and_merge.py` 路径

这些字段在后端的意义是：

- 后端需要知道 Python 在哪里
- 后端需要知道调用哪个脚本
- 后端需要知道工作目录和结果目录在哪里
- 后端需要把这些路径传给服务类和健康检查接口

在更换机器、盘符或目录结构时，这个文件通常是最先需要检查的配置文件之一。

### `python/config.py`

这是 Python 侧的路径配置中心。

它定义了这些关键变量：

- `LEGACY_CBCT_ROOT`
- `MODEL_PROJECT_ROOT`
- `DATA_ROOT`
- `RAW_ROOT`
- `WORKSPACE_ROOT`
- `TEST_PATIENT_ROOT`
- `TMP_DIR`
- `DICOM_ROOT`
- `RESULTS_BASE`
- `PIPELINE_PATH`
- `EXTRACT_MERGE_SCRIPT`
- `PARAM_PATH`
- `UID_PATH`

这个文件的思路是：

- 先尝试从环境变量读取
- 如果没有，再回退到代码里写死的默认绝对路径

这意味着项目**已经开始向可配置化过渡**，但仍保留了大量本地默认值。

## 2. 默认值硬编码位置

### `python/method1_workflow.py`

里面直接定义了：

- `DEFAULT_SOURCE_ROOT = F:\\mimi0209\\HeadNeck-selected`
- `DEFAULT_WORKSPACE_ROOT = F:\\mimi0209\\output-test`

这两个默认值会在：

- Spring 通过 `spring_bridge.py --action defaults` 调用时返回给前端
- 前端初始展示时作为默认目录显示

### `python/method2_workflow.py`

里面直接定义了：

- `DEFAULT_SOURCE_ROOT = G:\\mimi0209\\HeadNeck-selected`
- `DEFAULT_WORKSPACE_ROOT = G:\\mimi0209\\output-test`

这意味着方法一和方法二使用的默认目录并不完全一致。

### 前端页面中的默认值

前端页面中也存在默认目录文本，例如：

- `cbct-react/src/pages/Method1DatasetBuilder.tsx`
- `cbct-react/src/pages/Method2DatasetBuilder.tsx`

虽然前端通常会再从后端 `/defaults` 接口读取默认值，但页面本身仍保留了本地路径作为初始值或兜底显示。

## 3. 与运行强耦合的 JSON 文件

### `python/patient_params.json`

这是 DICOM 恢复和结果导出阶段非常关键的配置文件。

它保存的内容包括：

- 病人 ID
- `offset_x`
- `offset_y`
- `old_spacing`
- `old_thickness`
- `new_spacing`
- `new_thickness`
- `target_slices`
- `raw_relpath`
- `dicom_relpath`

它的作用可以理解为：

- 告诉系统每个病人的原始 raw 在哪里
- 告诉系统原始 DICOM 在哪里
- 告诉系统恢复时应该采用哪些空间参数和偏移量

如果这个文件内容不正确，`process_pipeline.py` 无法正确恢复最终输出。

### `python/Patient_rename.json`

这个文件主要保存 DICOM UID 相关信息。

它通常包含：

- 原始 Study / Series / SOP UID
- 不同模型名对应的 generated UID

它的作用是：

- 在生成新的 DICOM 序列时，给不同模型结果分配新的 UID
- 避免新导出的 DICOM 与原始 DICOM UID 冲突

如果没有它，或者内容不正确，DICOM 导出的身份标识可能会混乱。

## 4. 测试与示例请求中的硬编码

### `backend/test-api.http`

这个文件里写了大量接口测试样例，请求体中包含：

- `F:/mimi0209/HeadNeck-selected`
- `G:/mimi0209/HeadNeck-selected`
- `F:/mimi0209/output-test`
- `G:/mimi0209/output-test`

它的作用是：

- 方便开发期直接测试接口

它的问题是：

- 路径完全和当前开发环境耦合
- 对外公开时容易让人误以为这是项目通用默认路径

## 5. 模型与目录名称耦合

项目里很多地方直接使用这些固定名称：

- `model_cstgan`
- `model_attn_vit`
- `model_mask`
- `cstgan_c`
- `mb_taylor`
- `vit-unet`
- `attn`
- `0106`

这些名称出现在：

- 前端模型下拉框
- `python/inference_core.py`
- `python/process_pipeline.py`

这意味着：

- 前端选项不是动态扫描目录，而是代码里明确枚举
- Python 推理逻辑也依赖这些固定命名约定

## 6. 哪些配置最值得先看

为说明项目依赖关系，建议按以下顺序阅读：

1. `backend/src/main/resources/application.yml`
2. `python/config.py`
3. `python/patient_params.json`
4. `python/Patient_rename.json`
5. `python/method1_workflow.py`
6. `python/method2_workflow.py`
7. `backend/test-api.http`

## 7. 总结

这个项目目前的状态不是“没有配置设计”，而是“已经开始做配置抽象，但仍强依赖当前本地环境”。

总体上可以概括为：

- Spring 侧已经把路径集中在 `application.yml`
- Python 侧已经把路径集中在 `config.py`
- 但默认值仍然是本地绝对路径
- 方法一 / 方法二仍各自带着环境默认目录
- JSON 文件仍承担了很重要的本地运行配置职责

这也是为什么这个仓库适合被理解为：

- 一个能在特定研究环境中工作的完整系统

而不是：

- 一个零配置、公开即跑的模板项目
