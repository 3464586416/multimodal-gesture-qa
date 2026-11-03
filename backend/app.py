"""FastAPI 主入口：WebSocket 实时检测 + REST API。

关键改进：
- 坐标系：推理在"处理帧"（宽度上限 MAX_INFER_WIDTH 降采样）上进行，
  但所有返回坐标统一换算回前端发送的原始帧坐标，前后端不再错位；
- 背压：WebSocket 采用 latest-frame-only 单槽策略，后端处理不过来时
  自动丢弃中间积压帧，消除结果延迟堆积；
- 生命周期：模型/数据库在 lifespan 中初始化与释放，初始化失败明确降级；
- 历史记录：/qa 回答完成后截图落盘 uploads/、问答写库（旧实现从未调用 db）；
- /qa 流式桥接：线程 -> asyncio.Queue 事件驱动（无忙轮询），客户端断开时
  取消上游 LLM 读取；
- 校验与限制：问题长度、图片大小上限；CORS 不再与 credentials 混用；
- logging 统一，替换 print 调试。
"""
import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

from gesture import GestureDetector          # noqa: E402
from detector import ObjectDetector          # noqa: E402
from llm_client import LLMClient             # noqa: E402
from db import Database                      # noqa: E402
from geometry import (                       # noqa: E402
    scale_bbox, scale_landmarks, scale_objects, scale_point,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))
MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
MAX_QUESTION_LEN = 500
MAX_INFER_WIDTH = int(os.getenv("MAX_INFER_WIDTH", "1280"))
CONFIRM_THRESHOLD = int(os.getenv("POINT_CONFIRM_FRAMES", "3"))

UPLOAD_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_origins = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时加载模型/连接数据库，退出时释放。"""
    app.state.db = Database()
    try:
        app.state.db.connect()
    except Exception as e:
        logger.warning("数据库连接失败，历史记录功能不可用（请检查 MySQL 与 .env）: %s", e)

    app.state.gesture = None
    try:
        app.state.gesture = GestureDetector()
        logger.info("手势模型就绪")
    except Exception:
        logger.exception("手势模型初始化失败，将以「未检测到手部」降级运行")

    app.state.detector = ObjectDetector(
        confidence=float(os.getenv("YOLO_CONFIDENCE", "0.45"))
    )
    app.state.llm = LLMClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model=os.getenv("DASHSCOPE_MODEL", "qwen3.5-omni-plus"),
        base_url=os.getenv("DASHSCOPE_BASE_URL"),
    )
    yield
    if app.state.gesture is not None:
        app.state.gesture.release()
    app.state.db.close()


app = FastAPI(title="手势指示多模态问答系统", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


def decode_frame(data: bytes):
    """将 JPEG bytes 解码为 OpenCV 帧"""
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _process_frame_sync(frame, gesture_det, object_det):
    """
    CPU 密集型帧处理（线程池中执行）：
    降采样 -> 手势检测 -> (有手才) 物体检测 -> 指向匹配 -> 坐标换算回原始帧。
    返回的 dict 中所有坐标均为原始帧像素坐标。
    """
    h, w = frame.shape[:2]
    scale = min(1.0, MAX_INFER_WIDTH / max(w, 1))
    if scale < 1.0:
        infer = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))),
                           interpolation=cv2.INTER_AREA)
    else:
        infer = frame
    inv = 1.0 / scale

    empty = {
        "hand_detected": False, "pointing": False,
        "finger_tip": None, "finger_mcp": None, "landmarks": [],
        "objects": [], "frame_size": [w, h],
        "confirm_threshold": CONFIRM_THRESHOLD,
    }

    if gesture_det is None:
        return {**empty, "status": "gesture_unavailable"}

    gesture_result = gesture_det.detect(infer)
    objects = []
    pointed = None
    if gesture_result["hand_detected"]:
        det = object_det.detect(infer)
        objects = det["objects"]
        if gesture_result["pointing"] and objects:
            pointed = object_det.find_pointed_object(
                objects, gesture_result["finger_tip"],
                gesture_result["finger_mcp"])

    response = {
        **empty,
        "hand_detected": gesture_result["hand_detected"],
        "pointing": gesture_result["pointing"],
        "finger_tip": scale_point(gesture_result["finger_tip"], inv),
        "finger_mcp": scale_point(gesture_result["finger_mcp"], inv),
        "landmarks": scale_landmarks(gesture_result["landmarks"], inv),
        "objects": scale_objects(objects, inv),
        "status": "ok",
    }
    if pointed is not None:
        pointed = dict(pointed)
        pointed["bbox"] = scale_bbox(pointed["bbox"], inv)
        response["_pointed_object"] = pointed
    return response


def _persist_qa_record(object_name: str, object_class: str, confidence: float,
                       bbox_raw: str, question: str, answer: str,
                       img_array) -> int:
    """截图落盘 + 问答写库。失败仅记日志，不影响回答输出。"""
    db = app.state.db
    try:
        image_rel = None
        if img_array is not None:
            fname = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jpg"
            if cv2.imwrite(os.path.join(UPLOAD_DIR, fname), img_array):
                image_rel = f"uploads/{fname}"
        try:
            bbox = json.loads(bbox_raw) if bbox_raw else []
        except json.JSONDecodeError:
            bbox = bbox_raw
        record_id = db.save_detection(
            object_name, object_class, float(confidence),
            bbox, question, answer, image_rel)
        if record_id != -1:
            db.update_object_stats(object_name, object_class)
            return record_id
    except Exception:
        logger.exception("保存历史记录失败")
    return -1


@app.get("/")
async def root():
    return {"message": "手势指示多模态问答系统 API", "status": "running"}


@app.get("/health")
async def health():
    db_ok = False
    try:
        db_ok = app.state.db.is_connected()
    except Exception:
        pass
    return {
        "status": "ok",
        "db": db_ok,
        "gesture_ready": getattr(app.state, "gesture", None) is not None,
        "detector_ready": getattr(app.state, "detector", None) is not None,
    }


@app.websocket("/ws/process")
async def process_frame(websocket: WebSocket):
    """
    实时视频帧处理：前端发送 JPEG bytes，后端返回 JSON 检测结果。
    latest-frame-only 背压：接收任务只保留最新一帧，处理慢时旧帧自动丢弃。
    文本消息为 JSON 控制指令（如 {"type": "reset"}）。
    """
    await websocket.accept()
    gesture_det = app.state.gesture
    object_det = app.state.detector
    loop = asyncio.get_running_loop()

    pending = {"data": None}      # 单槽：最新待处理帧
    new_frame = asyncio.Event()
    closed = asyncio.Event()
    control = []

    async def receive_loop():
        try:
            while True:
                msg = await websocket.receive()
                if msg["type"] != "websocket.receive":
                    break
                if msg.get("bytes") is not None:
                    pending["data"] = msg["bytes"]   # 覆盖即丢弃旧帧
                    new_frame.set()
                elif msg.get("text") is not None:
                    try:
                        data = json.loads(msg["text"])
                        if data.get("type") == "reset":
                            control.append("reset")
                            new_frame.set()
                    except json.JSONDecodeError:
                        pass
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            closed.set()
            new_frame.set()

    async def process_loop():
        confirmed_object = None
        confirm_count = 0
        while True:
            await new_frame.wait()
            new_frame.clear()

            while control:
                if control.pop(0) == "reset":
                    confirmed_object, confirm_count = None, 0
                    await websocket.send_json({"type": "reset_confirmed"})

            data, pending["data"] = pending["data"], None
            if data is None:
                if closed.is_set():
                    return
                continue

            frame = decode_frame(data)
            if frame is None:
                await websocket.send_json({"error": "帧解码失败"})
                if closed.is_set():
                    return
                continue

            try:
                response = await loop.run_in_executor(
                    None, _process_frame_sync, frame, gesture_det, object_det)
            except Exception as e:
                logger.exception("帧处理异常")
                try:
                    await websocket.send_json({"error": str(e)})
                except Exception:
                    return
                if closed.is_set():
                    return
                continue

            # 指向确认（滑动窗口计数）
            pointed_obj = response.pop("_pointed_object", None)
            if pointed_obj:
                name = pointed_obj["class_name"]
                if confirmed_object == name:
                    confirm_count += 1
                else:
                    confirmed_object, confirm_count = name, 1
            elif confirm_count > 0:
                confirm_count -= 1

            if confirm_count >= CONFIRM_THRESHOLD and pointed_obj is not None:
                pointed_obj["confirmed"] = True
                response["pointed_object"] = pointed_obj
            else:
                response["pointed_object"] = None
            response["confirm_count"] = confirm_count

            if confirm_count > 0:
                logger.debug("[确认] %s: %s/%s | objects=%s",
                             confirmed_object, confirm_count, CONFIRM_THRESHOLD,
                             [o["class_name"] for o in response.get("objects", [])])

            try:
                await websocket.send_json(response)
            except (RuntimeError, WebSocketDisconnect):
                return

    receiver = asyncio.create_task(receive_loop())
    try:
        await process_loop()
    finally:
        receiver.cancel()
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/qa")
async def ask_question(
    question: str = Form(...),
    image: UploadFile = File(None),
    object_name: str = Form(""),
    object_class: str = Form(""),
    confidence: float = Form(0.0),
    bbox: str = Form(""),
):
    """
    多模态问答（SSE 流式）。
    成功回答后自动保存物品截图与问答记录到数据库（需提供 object_name）。
    事件：{"chunk": str} | {"error": true, "message": str} | {"done": true, "answer": str, "record_id": int}
    """
    question = question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    if len(question) > MAX_QUESTION_LEN:
        raise HTTPException(status_code=400, detail=f"问题过长（最多 {MAX_QUESTION_LEN} 字）")

    llm = getattr(app.state, "llm", None)
    if llm is None:
        raise HTTPException(status_code=503, detail="问答服务未就绪")

    img_array = None
    if image:
        contents = await image.read()
        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413, detail=f"图片超过大小限制 {MAX_IMAGE_BYTES // 1024 // 1024}MB")
        if contents:
            img_array = decode_frame(contents)
            if img_array is None:
                raise HTTPException(status_code=400, detail="图片解码失败，请发送 JPG/PNG")

    async def generate():
        aq: asyncio.Queue = asyncio.Queue()
        stop_event = threading.Event()

        def worker():
            try:
                for chunk in llm.ask_stream(question, img_array):
                    if stop_event.is_set():
                        break
                    loop_.call_soon_threadsafe(aq.put_nowait, ("chunk", chunk))
            except Exception as e:
                loop_.call_soon_threadsafe(aq.put_nowait, ("error", str(e)))
            finally:
                loop_.call_soon_threadsafe(aq.put_nowait, ("end", None))

        loop_ = asyncio.get_running_loop()
        threading.Thread(target=worker, daemon=True).start()

        full_answer = ""
        error_msg = None
        try:
            while True:
                kind, payload = await aq.get()
                if kind == "chunk":
                    full_answer += payload
                    yield f"data: {json.dumps({'chunk': payload}, ensure_ascii=False)}\n\n"
                elif kind == "error":
                    error_msg = payload
                    break
                else:  # end
                    break

            if error_msg:
                yield f"data: {json.dumps({'error': True, 'message': error_msg}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
                return

            record_id = -1
            if object_name:
                record_id = await asyncio.to_thread(
                    _persist_qa_record, object_name, object_class,
                    confidence, bbox, question, full_answer, img_array)
            yield f"data: {json.dumps({'done': True, 'answer': full_answer, 'record_id': record_id if record_id > 0 else None}, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            stop_event.set()   # 客户端断开 -> 取消上游读取
            raise

    # 显式 charset：SSE 中 ensure_ascii=False 的中文需保证客户端按 UTF-8 解码
    return StreamingResponse(generate(), media_type="text/event-stream; charset=utf-8")


@app.post("/asr")
async def speech_to_text(file: UploadFile = File(...)):
    """
    语音转文字：前端上传麦克风录制的 WAV（或 MP3/M4A），
    用 Qwen-omni 的音频理解能力转写，返回 {"text": "..."}。
    """
    llm = getattr(app.state, "llm", None)
    if llm is None:
        raise HTTPException(status_code=503, detail="问答服务未就绪")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="音频为空")
    if len(contents) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"音频超过大小限制 {MAX_AUDIO_BYTES // 1024 // 1024}MB")
    name = (file.filename or "").lower()
    audio_format = "wav"
    for ext in ("mp3", "m4a", "aac", "ogg", "opus", "flac", "wav"):
        if name.endswith(f".{ext}"):
            audio_format = ext
            break
    try:
        text = await asyncio.to_thread(llm.transcribe_audio, contents, audio_format)
    except Exception as e:
        logger.warning("ASR 失败: %s", e)
        raise HTTPException(status_code=502, detail=f"识别失败: {e}")
    return {"text": text}


@app.get("/history")
async def get_history(limit: int = 50, offset: int = 0):
    """获取检测/问答历史记录（total 为全库计数）"""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    records = await asyncio.to_thread(app.state.db.get_history, limit, offset)
    total = await asyncio.to_thread(app.state.db.count_history)
    return {"records": records, "total": total}


@app.get("/latest")
async def get_latest():
    """获取最新检测记录"""
    record = await asyncio.to_thread(app.state.db.get_latest_detection)
    return {"record": record}


def _enable_windows_ansi() -> bool:
    """
    激活 cmd 控制台的虚拟终端处理，让 uvicorn 的 ANSI 彩色日志正常渲染
    （Win10 conhost 默认不解析，会把 [32m 原样打印）。返回是否成功。
    """
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        ok = False
        for std_handle in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            h = kernel32.GetStdHandle(std_handle)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                ok |= bool(kernel32.SetConsoleMode(h, mode.value | 0x0004))
        return ok
    except Exception:
        return False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        # 无法渲染 ANSI 的终端（老 cmd/重定向）直接关闭彩色，避免 [32m 原样输出
        use_colors=_enable_windows_ansi(),
    )
