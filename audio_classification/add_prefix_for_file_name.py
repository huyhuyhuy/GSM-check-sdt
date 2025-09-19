from pathlib import Path

BASE_PATH = Path(__file__).parent
TEST_PATH = BASE_PATH / "dataset/vietel/incorrect"

prefix = "incorrect_"

for file in TEST_PATH.iterdir():
    if file.is_file():
        new_name = prefix + file.name
        new_path = file.with_name(new_name)
        file.rename(new_path)
