import numpy as np

def detect_fuzzy_rectangles(filename, threshold=2700, sample_rate=1000, min_ms=300, max_gap=12):
    with open(filename, "r") as f:
        data = [int(line.strip()) for line in f if line.strip().isdigit()]
    
    adc = np.array(data)
    min_samples = int((min_ms / 1000) * sample_rate)
    segments = []

    start = None
    below_count = 0

    for i, val in enumerate(adc):
        if val >= threshold:
            if start is None:
                start = i
            below_count = 0
        else:
            if start is not None:
                below_count += 1
                if below_count > max_gap:
                    end = i - below_count
                    if end - start >= min_samples:
                        segments.append((start, end))
                    start = None
                    below_count = 0

    # Đoạn kết thúc cuối file
    if start is not None:
        end = len(adc)
        if end - start >= min_samples:
            segments.append((start, end))

    # In kết quả
    print(f"Số lượng khối hình chữ nhật: {len(segments)}")
    for idx, (s, e) in enumerate(segments, 1):
        start_time = s / sample_rate
        end_time = e / sample_rate
        duration = (e - s) / sample_rate
        print(f"Hình #{idx}: Bắt đầu = {start_time:.3f}s, Kết thúc = {end_time:.3f}s, Thời lượng = {duration*1000:.1f}ms")

    return segments

if __name__ == "__main__":
    detect_fuzzy_rectangles("check.txt")
