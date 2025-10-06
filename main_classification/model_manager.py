"""
ModelPool - Quản lý pool of STT models với thread-safe và load balancing
Model Pooling (3-4 copies) → Balance memory vs performance → Tránh bottleneck
"""

import threading
import logging
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from typing import Optional, Tuple, List
import time
from queue import Queue

logger = logging.getLogger(__name__)

class ModelPool:
    """
    Singleton class để quản lý pool of STT models

    Với 30 GSM instances:
    - 1 model: Bottleneck nghiêm trọng
    - 4 models: Cân bằng tốt (30/4 = 7.5 threads/model)
    - Tiết kiệm: 86% RAM (4 vs 30 models)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Khởi tạo singleton instance"""
        if self._initialized:
            return

        self._initialized = True
        self._pool_size = 4  # Default pool size
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model_id = "nguyenvulebinh/wav2vec2-base-vietnamese-250h"

        # Pool of models
        self._processor: Optional[Wav2Vec2Processor] = None  # Shared processor (nhẹ)
        self._model_pool: List[Wav2Vec2ForCTC] = []  # Pool of models
        self._model_queue: Queue = Queue()  # Queue để quản lý available models
        self._pool_lock = threading.Lock()
        self._loading = False
        self._loaded = False

        # Statistics
        self._total_requests = 0
        self._total_wait_time = 0.0

        logger.info(f"🤖 ModelPool initialized:")
        logger.info(f"   - Pool size: {self._pool_size} models")
        logger.info(f"   - Device: {self._device}")
        logger.info(f"   - Model: {self._model_id}")
    
    def set_pool_size(self, pool_size: int):
        """Set pool size (chỉ được gọi trước khi load models)"""
        if self._model_pool:
            raise RuntimeError("Không thể thay đổi pool_size sau khi đã load models")
        self._pool_size = pool_size
        logger.info(f"📊 Pool size set to: {pool_size}")
    
    def _load_pool(self):
        """Load pool of models (lazy loading, thread-safe)"""
        with self._pool_lock:
            # Double-check locking
            if self._loaded:
                return

            if self._loading:
                # Đợi thread khác load xong
                logger.info("⏳ Waiting for model pool to be loaded...")
                while self._loading:
                    time.sleep(0.1)
                return

            # Bắt đầu load pool
            self._loading = True
            try:
                logger.info(f"🤖 Loading model pool ({self._pool_size} models)...")

                # Load processor (shared, chỉ 1 lần)
                logger.info("📥 Loading processor...")
                self._processor = Wav2Vec2Processor.from_pretrained(self._model_id)
                logger.info("✅ Processor loaded")

                # Load pool of models
                for i in range(self._pool_size):
                    logger.info(f"📥 Loading model {i+1}/{self._pool_size}...")
                    model = Wav2Vec2ForCTC.from_pretrained(self._model_id).to(self._device)
                    self._model_pool.append(model)
                    self._model_queue.put(model)  # Add to available queue
                    logger.info(f"✅ Model {i+1}/{self._pool_size} loaded")

                self._loaded = True
                logger.info(f"🎉 Model pool loaded successfully!")
                logger.info(f"   - {self._pool_size} models on {self._device}")
                logger.info(f"   - Ready to serve {self._pool_size * 7} concurrent requests efficiently")

            except Exception as e:
                logger.error(f"❌ Failed to load model pool: {e}")
                raise
            finally:
                self._loading = False

    def get_model(self) -> Tuple[Wav2Vec2Processor, Wav2Vec2ForCTC, str]:
        """
        Lấy model từ pool (blocking nếu pool đầy)

        Returns:
            Tuple[processor, model, device]

        Note:
            - Phải gọi release_model() sau khi dùng xong
            - Sử dụng context manager để tự động release
        """
        # Lazy load pool nếu chưa load
        if not self._loaded:
            self._load_pool()

        # Lấy model từ queue (blocking nếu không có model available)
        start_wait = time.time()
        model = self._model_queue.get()  # Block until a model is available
        wait_time = time.time() - start_wait

        # Update statistics
        self._total_requests += 1
        self._total_wait_time += wait_time

        if wait_time > 0.1:  # Log nếu phải đợi lâu
            logger.debug(f"⏳ Waited {wait_time:.3f}s for model (queue was full)")

        return self._processor, model, self._device

    def release_model(self, model: Wav2Vec2ForCTC):
        """
        Trả model về pool sau khi dùng xong

        Args:
            model: Model cần trả về pool
        """
        self._model_queue.put(model)
    
    def is_loaded(self) -> bool:
        """Kiểm tra xem pool đã được load chưa"""
        return self._loaded

    def get_device(self) -> str:
        """Lấy device đang sử dụng"""
        return self._device

    def get_pool_size(self) -> int:
        """Lấy kích thước pool"""
        return self._pool_size

    def get_statistics(self) -> dict:
        """Lấy thống kê sử dụng pool"""
        avg_wait = self._total_wait_time / self._total_requests if self._total_requests > 0 else 0
        return {
            "pool_size": self._pool_size,
            "total_requests": self._total_requests,
            "total_wait_time": self._total_wait_time,
            "avg_wait_time": avg_wait,
            "available_models": self._model_queue.qsize(),
            "busy_models": self._pool_size - self._model_queue.qsize()
        }

    def unload_pool(self):
        """Giải phóng toàn bộ pool khỏi memory (nếu cần)"""
        with self._pool_lock:
            # Clear models
            for model in self._model_pool:
                del model
            self._model_pool.clear()

            # Clear queue
            while not self._model_queue.empty():
                try:
                    self._model_queue.get_nowait()
                except:
                    break

            # Clear processor
            if self._processor is not None:
                del self._processor
                self._processor = None

            # Clear CUDA cache nếu đang dùng GPU
            if self._device == "cuda":
                torch.cuda.empty_cache()

            self._loaded = False
            logger.info("🗑️ Model pool unloaded from memory")


class ModelContext:
    """
    Context manager để tự động release model sau khi dùng

    Usage:
        with ModelContext() as (processor, model, device):
            # Use model here
            ...
        # Model tự động được release
    """

    def __init__(self, pool: ModelPool):
        self.pool = pool
        self.model = None
        self.processor = None
        self.device = None

    def __enter__(self):
        self.processor, self.model, self.device = self.pool.get_model()
        return self.processor, self.model, self.device

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model is not None:
            self.pool.release_model(self.model)
        return False


# Singleton instance
model_manager = ModelPool()
model_manager.set_pool_size(4)  # 4 models cho 30 instances

def get_model_context():
    """Helper function để lấy context manager"""
    return ModelContext(model_manager)

