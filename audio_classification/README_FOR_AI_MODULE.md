python audio_classification/my_training.py
python audio_classification/my_training_v2.py
python audio_classification/my_testing.py
python audio_classification/my_training_fine_turning.py
python audio_classification/my_testing_fine_turning.py

python audio_classification/add_prefix_for_file_name.py
python audio_classification/get_phone_number.py
python audio_classification/speech_to_text_vosk.py
python audio_classification/speech_to_text_whisper_api.py
python audio_classification/speech_to_text_whisper_local.py


python audio_classification/counting_data.py



GPU env
```bash
powershell -NoExit -Command "& { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; & 'C:\Users\ADMIN\anaconda3\Scripts\conda.exe' shell.powershell hook | Out-String | Invoke-Expression; conda activate myenv }"

HDSD:
- chạy file my_training.py để tạo ra model(khi chưa có model, hoặc muốn có  model mới với data mới)
- Cách sử dụng demo trong my_testing.py"
+ load_wav để lấy được file audio(cần đảm bảo đúng cấu trúc sampling rate, LR theo chuẩn 1/2)
+ load model để sử dụng
+ List labels cần giống với list khi training
+ predict và kiểm tra kết quả