# 🚀 ModelPool - Load Balancing cho 30 GSM Instances

## 🎯 Vấn đề

### Scenario 1: Mỗi instance load model riêng (Trước đây)
```
30 GSM instances × 1 model/instance = 30 models
RAM: ~1GB/model × 30 = ~30GB
```
❌ **Vấn đề**: Tốn RAM khủng khiếp!

### Scenario 2: Tất cả dùng chung 1 model (Cải tiến lần 1)
```
30 GSM instances → 1 shared model
RAM: ~1GB
```
✅ **Ưu điểm**: Tiết kiệm RAM tối đa (97%)
❌ **Vấn đề**: **BOTTLENECK nghiêm trọng!**
- 30 threads cùng chờ 1 model
- Chỉ 1 thread xử lý tại 1 thời điểm
- 29 threads khác phải đợi
- Tốc độ chậm như rùa 🐢

### Scenario 3: Model Pool với 4 models (Giải pháp tối ưu) ⭐
```
30 GSM instances → Pool of 4 models
RAM: ~1GB/model × 4 = ~4GB
Load: 30 threads / 4 models = 7.5 threads/model
```
✅ **Ưu điểm**:
- Tiết kiệm RAM: 87% (4GB vs 30GB)
- Không bottleneck: 4 models xử lý song song
- Tốc độ tăng ~7.5x so với 1 model
- Load balancing tự động

---

## 🏗️ Kiến trúc ModelPool

### 1. Components

```
┌─────────────────────────────────────────────────────────┐
│                     ModelPool                           │
├─────────────────────────────────────────────────────────┤
│  Processor (shared)                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Wav2Vec2Processor (1 instance)                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  Model Pool (4 models)                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Model 1  │ │ Model 2  │ │ Model 3  │ │ Model 4  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                          │
│  Queue (FIFO)                                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Available Models: [M1, M2, M3, M4]             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 2. Flow

```
Thread 1 ──┐
Thread 2 ──┤
Thread 3 ──┤
   ...     ├──→ get_model() ──→ Queue ──→ Model 1 ──→ Use ──→ release_model()
Thread 28 ─┤                            ├→ Model 2                    │
Thread 29 ─┤                            ├→ Model 3                    │
Thread 30 ─┘                            └→ Model 4                    │
                                                                       │
                                         ┌─────────────────────────────┘
                                         │
                                         ▼
                                    Back to Queue
```

---

## 💻 Code Implementation

### 1. ModelPool Class

```python
class ModelPool:
    def __init__(self, pool_size: int = 4):
        self._pool_size = pool_size
        self._processor = None  # Shared processor
        self._model_pool = []   # List of models
        self._model_queue = Queue()  # Available models queue
        
    def get_model(self):
        """Lấy model từ pool (blocking nếu pool đầy)"""
        if not self._loaded:
            self._load_pool()
        
        # Block until a model is available
        model = self._model_queue.get()
        return self._processor, model, self._device
    
    def release_model(self, model):
        """Trả model về pool"""
        self._model_queue.put(model)
```

### 2. Usage trong GSMInstance

```python
def _transcribe_audio(self, wav_file):
    # Lấy model từ pool
    processor, model, device = model_manager.get_model()
    
    try:
        # Use model
        speech, rate = librosa.load(wav_file, sr=16000)
        input_values = processor(speech, ...).to(device)
        
        with torch.no_grad():
            logits = model(input_values).logits
        
        result = processor.batch_decode(...)
        return result[0]
        
    finally:
        # QUAN TRỌNG: Trả model về pool
        model_manager.release_model(model)
```

---

## 📊 Performance Analysis

### Với 30 GSM instances đồng thời:

#### Scenario 1: Mỗi instance load riêng
```
RAM: 30GB
Tốc độ: Nhanh (mỗi instance có model riêng)
Vấn đề: Tốn RAM khủng khiếp
```

#### Scenario 2: 1 model shared
```
RAM: 1GB (tiết kiệm 97%)
Tốc độ: RẤT CHẬM (bottleneck)
Thời gian: 30 × T (tuần tự)
Vấn đề: Bottleneck nghiêm trọng
```

#### Scenario 3: Pool of 4 models ⭐
```
RAM: 4GB (tiết kiệm 87%)
Tốc độ: Nhanh (song song)
Thời gian: ~8 × T (30/4 = 7.5 batches)
Vấn đề: KHÔNG
```

### Tính toán cụ thể:

Giả sử mỗi STT request mất 1 giây:

| Scenario | RAM | Thời gian xử lý 30 requests | Tốc độ |
|----------|-----|----------------------------|--------|
| 30 models riêng | 30GB | 1s (song song) | ⚡⚡⚡⚡⚡ |
| 1 model shared | 1GB | 30s (tuần tự) | 🐢 |
| 4 models pool | 4GB | 8s (4 batches) | ⚡⚡⚡⚡ |

**Kết luận**: Pool of 4 models là **sweet spot** - cân bằng tốt nhất!

---

## 🔧 Configuration

### Chọn pool size phù hợp:

```python
# Công thức: pool_size = num_instances / 7-10

# 20 instances
model_manager = ModelPool(pool_size=3)

# 30 instances (recommended)
model_manager = ModelPool(pool_size=4)

# 40 instances
model_manager = ModelPool(pool_size=5)

# 50+ instances
model_manager = ModelPool(pool_size=6)
```

### Trade-off:

| Pool Size | RAM | Performance | Bottleneck Risk |
|-----------|-----|-------------|-----------------|
| 1 | Thấp nhất | Chậm nhất | Cao nhất |
| 2 | Thấp | Chậm | Cao |
| 3 | Trung bình | Tốt | Trung bình |
| **4** | **Tốt** | **Rất tốt** | **Thấp** ⭐ |
| 5 | Cao | Rất tốt | Rất thấp |
| 10+ | Rất cao | Tốt nhất | Không |

---

## 🧪 Testing

### Test với 30 threads:

```bash
python test_model_manager.py
```

Kết quả mong đợi:
```
=== Test 3: Thread Safety & Load Balancing ===
🚀 Tạo 30 threads đồng thời (giả lập 30 GSM instances)...
   Pool size: 4 models

📊 Kết quả:
   - Tổng thời gian: ~8s
   - Số processor instances: 1 (expected: 1)
   - Số model instances: 4 (expected: 4)
   - Max wait time: 0.XXXs
   - Avg wait time: 0.XXXs

✅ Processor được share (1 instance)
✅ Pool có 4 models như mong đợi
✅ Load balancing hoạt động tốt
✅ Thread-safe hoạt động đúng
```

---

## 📈 Statistics

ModelPool cung cấp statistics real-time:

```python
stats = model_manager.get_statistics()

print(f"Pool size: {stats['pool_size']}")
print(f"Total requests: {stats['total_requests']}")
print(f"Avg wait time: {stats['avg_wait_time']:.3f}s")
print(f"Available models: {stats['available_models']}")
print(f"Busy models: {stats['busy_models']}")
```

---

## 🎯 Best Practices

### 1. Luôn release model
```python
# ❌ BAD - Không release
processor, model, device = model_manager.get_model()
result = transcribe(model, audio)
# Model không được trả về pool → Leak!

# ✅ GOOD - Release trong finally
processor, model, device = model_manager.get_model()
try:
    result = transcribe(model, audio)
finally:
    model_manager.release_model(model)
```

### 2. Sử dụng context manager (tương lai)
```python
# ✅ BEST - Auto release
with get_model_context() as (processor, model, device):
    result = transcribe(model, audio)
# Model tự động được release
```

### 3. Monitor statistics
```python
# Định kỳ check statistics
stats = model_manager.get_statistics()
if stats['avg_wait_time'] > 1.0:
    print("⚠️ Pool có thể cần tăng size!")
```

---

## 🚀 Kết luận

### ModelPool giải quyết được:
✅ Tiết kiệm RAM (87% so với không pool)
✅ Tránh bottleneck (4 models xử lý song song)
✅ Load balancing tự động
✅ Thread-safe
✅ Dễ scale (chỉ cần tăng pool_size)

### Phù hợp cho:
✅ 20-50 GSM instances
✅ Hệ thống cần xử lý đồng thời cao
✅ RAM hạn chế nhưng cần performance tốt

### Không phù hợp cho:
❌ < 10 instances (dùng 1-2 models là đủ)
❌ RAM không giới hạn (có thể dùng model riêng cho mỗi instance)

---

**ModelPool = Smart Cache + Load Balancing + Thread Safety + Performance!** 🚀

