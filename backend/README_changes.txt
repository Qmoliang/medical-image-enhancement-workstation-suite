新增/修改说明：
1. 前端四个页面都已整理到 cbct-react/src/pages。
2. Method1/Method2 页面已改成可兼容 Spring 包装返回值 {ok,message,data:{...}}。
3. PipelineRunner 不再调用 Flask 的 http://localhost:8000/run_model / merge_data / run_model_stream。
4. DicomGenerator 不再调用 Flask 的 /api/run_pipeline。
5. 新增 Spring 控制器：/api/inference/run、/api/inference/run-stream、/api/inference/merge、/api/pipeline/run。
6. 新增 python/spring_bridge.py，Spring 通过它继续调用你现有 Python 工作流。
