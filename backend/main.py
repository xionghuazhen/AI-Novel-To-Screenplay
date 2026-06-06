"""FastAPI 后端入口"""
from __future__ import annotations
import time
import traceback
import yaml
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, ValidationError as PydanticValidationError
from backend.config import app_config
from agents.workflow import run_workflow
from agents.dialogue_agent import modify_dialogue

app = FastAPI(
    title="AI Novel To Screenplay",
    description="AI 小说转剧本工具",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PydanticValidationError)
async def validation_exception_handler(request: Request, exc: PydanticValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(status_code=422, content={"detail": "数据校验失败", "errors": errors})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
        },
    )


class ParseRequest(BaseModel):
    text: str


class ModifyRequest(BaseModel):
    screenplay_data: dict
    instruction: str


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "AI Novel To Screenplay"}


# 全局统计计数器
_processing_stats = {"total_requests": 0, "total_processing_time_ms": 0, "total_words_processed": 0}


@app.get("/api/stats")
async def get_stats():
    """返回处理统计信息"""
    total = _processing_stats["total_requests"]
    avg_time = _processing_stats["total_processing_time_ms"] / total if total > 0 else 0
    return {
        "total_requests": total,
        "avg_processing_time_ms": round(avg_time),
        "total_words_processed": _processing_stats["total_words_processed"],
        "llm_provider": app_config.llm.provider,
        "llm_model": app_config.llm.model,
    }


@app.post("/api/parse")
async def parse_novel(req: ParseRequest):
    """粘贴小说文本，返回结构化剧本 YAML"""
    if not req.text.strip():
        raise HTTPException(400, "文本不能为空")

    start = time.time()
    result = run_workflow(req.text)
    elapsed = int((time.time() - start) * 1000)

    if not result or not result.get("scenes"):
        raise HTTPException(500, "剧本生成失败，请检查输入文本格式")

    result["metadata"] = {
        "generator": "AI Novel To Screenplay",
        "version": "1.0.0",
        "source_chapters": len(result.get("story_beats", [])),
        "word_count": len(req.text),
        "processing_time_ms": elapsed,
    }

    yaml_output = yaml.dump(result, allow_unicode=True, default_flow_style=False, sort_keys=False)

    # 更新统计
    _processing_stats["total_requests"] += 1
    _processing_stats["total_processing_time_ms"] += elapsed
    _processing_stats["total_words_processed"] += len(req.text)

    return {
        "yaml": yaml_output,
        "data": result,
        "processing_time_ms": elapsed,
    }


@app.post("/api/parse/file")
async def parse_file(file: UploadFile = File(...)):
    """上传小说文件（txt/md），返回剧本 YAML"""
    content = await file.read()
    text = content.decode("utf-8")

    start = time.time()
    result = run_workflow(text)
    elapsed = int((time.time() - start) * 1000)

    if not result or not result.get("scenes"):
        raise HTTPException(500, "剧本生成失败，请检查文件格式")

    result["metadata"] = {
        "generator": "AI Novel To Screenplay",
        "version": "1.0.0",
        "source_chapters": len(result.get("story_beats", [])),
        "word_count": len(text),
        "processing_time_ms": elapsed,
    }

    yaml_output = yaml.dump(result, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return {
        "yaml": yaml_output,
        "data": result,
        "processing_time_ms": elapsed,
        "filename": file.filename,
    }


@app.post("/api/modify")
async def modify_screenplay(req: ModifyRequest):
    """多轮修改：根据用户指令修改剧本"""
    data = req.data
    characters = data.get("characters", [])
    scenes = data.get("scenes", [])

    modified_scenes = modify_dialogue(scenes, req.instruction, characters)
    data["scenes"] = modified_scenes

    yaml_output = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return {
        "yaml": yaml_output,
        "data": data,
    }


@app.get("/api/schema")
async def get_schema():
    """返回 YAML Schema 定义"""
    schema_md_path = Path(__file__).parent.parent / "docs" / "schema.md"
    if schema_md_path.exists():
        return PlainTextResponse(schema_md_path.read_text(encoding="utf-8"), media_type="text/markdown")
    return {"message": "schema.md not found, run /api/schema/generate first"}


@app.post("/api/schema/generate")
async def generate_schema():
    """生成 schema.md"""
    from backend.schema_doc import SCHEMA_DOC
    schema_md_path = Path(__file__).parent.parent / "docs" / "schema.md"
    schema_md_path.parent.mkdir(parents=True, exist_ok=True)
    schema_md_path.write_text(SCHEMA_DOC, encoding="utf-8")
    return {"status": "generated", "path": str(schema_md_path)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
