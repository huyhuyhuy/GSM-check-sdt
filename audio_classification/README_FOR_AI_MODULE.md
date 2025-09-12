python audio_classification/my_training.py
python audio_classification/my_testing.py

HDSD:
- chạy file my_training.py để tạo ra model(khi chưa có model, hoặc muốn có  model mới với data mới)
- Cách sử dụng demo trong my_testing.py"
+ load_wav để lấy được file audio(cần đảm bảo đúng cấu trúc sampling rate, LR theo chuẩn 1/2)
+ load model để sử dụng
+ List labels cần giống với list khi training
+ predict và kiểm tra kết quả