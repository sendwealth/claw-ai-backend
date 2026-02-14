"""
任务状态查询 API
提供 Celery 任务状态查询、取消、重试等接口
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.tasks.celery_app import celery_app
from app.core.config import settings


# 创建路由
router = APIRouter()


# ==================== Pydantic 模型 ====================

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    date_done: Optional[str] = None
    runtime: Optional[float] = None


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[Dict[str, Any]]
    total: int


class TaskCancelResponse(BaseModel):
    """任务取消响应模型"""
    task_id: str
    success: bool
    message: str


class TaskStatsResponse(BaseModel):
    """任务统计响应模型"""
    total_tasks: int
    pending: int
    started: int
    success: int
    failure: int
    retry: int
    workers: int


class AsyncTaskRequest(BaseModel):
    """异步任务请求模型"""
    conversation_id: str
    user_message: str
    conversation_history: Optional[List[Dict[str, str]]] = None
    system_prompt: Optional[str] = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    user_id: Optional[str] = None


class AsyncTaskResponse(BaseModel):
    """异步任务响应模型"""
    task_id: str
    status: str
    message: str


# ==================== API 路由 ====================

@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    查询任务状态

    Args:
        task_id: 任务 ID

    Returns:
        TaskStatusResponse: 任务状态信息
    """
    try:
        # 获取任务结果
        result = celery_app.AsyncResult(task_id)

        # 计算运行时间
        runtime = None
        if result.date_done and result.info:
            # 尝试从 result.info 获取运行时间
            if isinstance(result.info, dict) and "response_time" in result.info:
                runtime = result.info["response_time"]
            else:
                # 如果没有直接的运行时间，可以计算
                if hasattr(result, "date_started") and result.date_started:
                    runtime = (result.date_done - result.date_started).total_seconds()

        response = TaskStatusResponse(
            task_id=task_id,
            status=result.status,
            result=result.result if result.successful() else None,
            error=str(result.result) if result.failed() else None,
            traceback=result.traceback if result.failed() else None,
            date_done=result.date_done.isoformat() if result.date_done else None,
            runtime=runtime,
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务状态失败: {str(e)}")


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
) -> TaskListResponse:
    """
    列出所有任务（从 Redis 获取）

    注意：这会返回 Redis 中存储的所有任务结果，可能包含过期任务

    Args:
        status: 任务状态过滤（PENDING, STARTED, SUCCESS, FAILURE, RETRY）
        limit: 返回数量限制

    Returns:
        TaskListResponse: 任务列表
    """
    try:
        # 获取 Celery 的 backend（Redis）
        backend = celery_app.backend

        # 获取所有任务 ID
        # 注意：这依赖于具体的 backend 实现
        # 对于 Redis，可以通过 keys 获取所有任务
        task_ids = []

        if hasattr(backend, "keys"):
            # Redis backend
            pattern = "celery-task-meta-*"
            keys = backend.keys(pattern)

            for key in keys:
                # 提取 task_id
                task_id = key.decode("utf-8").replace("celery-task-meta-", "")
                task_ids.append(task_id)

        # 获取任务详情
        tasks = []
        filtered_count = 0

        for task_id in task_ids[:limit * 2]:  # 多取一些，用于过滤
            result = celery_app.AsyncResult(task_id)

            # 如果有状态过滤
            if status and result.status != status:
                continue

            # 添加到列表
            task_info = {
                "task_id": task_id,
                "status": result.status,
                "date_done": result.date_done.isoformat() if result.date_done else None,
            }

            if result.successful():
                task_info["result"] = result.result
            elif result.failed():
                task_info["error"] = str(result.result)

            tasks.append(task_info)
            filtered_count += 1

            # 达到限制数量
            if len(tasks) >= limit:
                break

        return TaskListResponse(
            tasks=tasks,
            total=len(tasks),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出任务失败: {str(e)}")


@router.post("/cancel/{task_id}", response_model=TaskCancelResponse)
async def cancel_task(task_id: str) -> TaskCancelResponse:
    """
    取消任务

    Args:
        task_id: 任务 ID

    Returns:
        TaskCancelResponse: 取消结果
    """
    try:
        # 撤销任务
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        return TaskCancelResponse(
            task_id=task_id,
            success=True,
            message="任务已取消",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.post("/retry/{task_id}")
async def retry_task(task_id: str) -> Dict[str, Any]:
    """
    重试任务

    注意：这仅适用于支持重试的任务

    Args:
        task_id: 任务 ID

    Returns:
        dict: 重试结果
    """
    try:
        # 获取原始任务
        result = celery_app.AsyncResult(task_id)

        if not result.failed():
            raise HTTPException(
                status_code=400,
                detail="只能重试失败的任务"
            )

        # 重试任务（需要重新提交任务，参数从原始任务中获取）
        # 这里需要根据具体任务类型处理
        # 简单实现：仅返回提示信息

        return {
            "task_id": task_id,
            "message": "请重新提交任务以重试",
            "original_status": result.status,
            "original_error": str(result.result) if result.failed() else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats() -> TaskStatsResponse:
    """
    获取任务统计信息

    Returns:
        TaskStatsResponse: 任务统计信息
    """
    try:
        # 获取 Celery worker 统计信息
        inspect = celery_app.control.inspect()

        # 获取活跃任务
        active_tasks = inspect.active()
        # 获取预定任务
        scheduled_tasks = inspect.scheduled()
        # 获取注册任务
        registered_tasks = inspect.registered()
        # 获取 worker 统计
        stats = inspect.stats()

        # 计算统计信息
        pending_count = 0
        started_count = 0
        success_count = 0
        failure_count = 0
        retry_count = 0
        total_count = 0
        worker_count = 0

        # 统计活跃任务
        if active_tasks:
            for worker, tasks in active_tasks.items():
                worker_count += 1
                for task in tasks:
                    total_count += 1
                    if task.get("state") == "PENDING":
                        pending_count += 1
                    elif task.get("state") == "STARTED":
                        started_count += 1

        # 统计预定任务
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    total_count += 1
                    pending_count += 1

        # 注意：SUCCESS 和 FAILURE 的统计需要从结果后端获取
        # 这里简化处理，仅统计活跃任务

        return TaskStatsResponse(
            total_tasks=total_count,
            pending=pending_count,
            started=started_count,
            success=success_count,
            failure=failure_count,
            retry=retry_count,
            workers=worker_count,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")


@router.post("/ai/generate", response_model=AsyncTaskResponse)
async def generate_ai_response_async(request: AsyncTaskRequest) -> AsyncTaskResponse:
    """
    异步生成 AI 响应

    Args:
        request: 异步任务请求

    Returns:
        AsyncTaskResponse: 任务信息，包含 task_id
    """
    try:
        from app.tasks.ai_tasks import generate_ai_response

        # 提交异步任务
        task = generate_ai_response.apply_async(
            kwargs={
                "conversation_id": request.conversation_id,
                "user_message": request.user_message,
                "conversation_history": request.conversation_history,
                "system_prompt": request.system_prompt,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "user_id": request.user_id,
            },
            queue="ai_high_priority",
            priority=8,  # 高优先级
        )

        return AsyncTaskResponse(
            task_id=task.id,
            status=task.status,
            message="AI 响应生成任务已提交",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.get("/workers")
async def get_workers() -> Dict[str, Any]:
    """
    获取所有 worker 信息

    Returns:
        dict: Worker 信息
    """
    try:
        inspect = celery_app.control.inspect()

        # 获取 worker 统计
        stats = inspect.stats()
        # 获取活跃任务
        active_tasks = inspect.active()
        # 获取注册任务
        registered_tasks = inspect.registered()

        workers = {}
        if stats:
            for worker_name, worker_stats in stats.items():
                workers[worker_name] = {
                    "stats": worker_stats,
                    "active_tasks": len(active_tasks.get(worker_name, [])),
                    "registered_tasks": registered_tasks.get(worker_name, []) if registered_tasks else [],
                }

        return {
            "workers": workers,
            "count": len(workers),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 worker 信息失败: {str(e)}")


@router.post("/workers/pool/restart")
async def restart_worker_pool(
    worker_name: Optional[str] = Query(None, description="Worker 名称，不指定则重启所有")
) -> Dict[str, Any]:
    """
    重启 worker 的进程池

    Args:
        worker_name: Worker 名称

    Returns:
        dict: 操作结果
    """
    try:
        # 发送重启池命令
        result = celery_app.control.pool_restart(
            destination=worker_name if worker_name else None,
            reply=True,
        )

        return {
            "success": True,
            "message": f"Worker 进程池重启命令已发送: {worker_name or '所有 workers'}",
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启 worker 失败: {str(e)}")


@router.post("/workers/shutdown")
async def shutdown_worker(
    worker_name: Optional[str] = Query(None, description="Worker 名称，不指定则关闭所有")
) -> Dict[str, Any]:
    """
    关闭 worker

    Args:
        worker_name: Worker 名称

    Returns:
        dict: 操作结果
    """
    try:
        # 发送关闭命令
        result = celery_app.control.shutdown(
            destination=worker_name if worker_name else None,
        )

        return {
            "success": True,
            "message": f"Worker 关闭命令已发送: {worker_name or '所有 workers'}",
            "result": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"关闭 worker 失败: {str(e)}")
