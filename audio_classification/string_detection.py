labels = [
    "leave_message",
    "be_blocked",
    "can_not_connect",
    "incorrect",
    "rinback_tone",
    "waiting_tone",
    "mute",
]

keyword_labels = [
    [
        "quý khách vui lòng để lại lời nhắn sau tiếng bíp",
        "cuộc gọi được tính theo cước thoại thông thường",
        "do thuê bao quý khách vừa gọi",
        "cước thoại thông thường",
        "lời nhắn sau tiếng bíp",
        "cuộc gọi được tính",
        "để lại lời nhắn",
        "sau tiếng bíp",
        "hiện đang bận",
        "tiếng bíp",
        "lời nhắn",
        "được tính",
        "cước thoại",
    ],
    [
        "đang tạm khóa",
        "tạm khóa",
        "khóa",
    ],
    [
        "vừa gọi tạm thời không liên lạc được xin quý khách",
        "tạm thời không liên lạc được",
        "không liên lạc được",
        "không liên lạc",
        "tạm thời không",
    ],
    [
        "hoặc liên hệ số một chín tám để được hỗ trợ",
        "số máy quý khách vừa gọi không đúng",
        "vui lòng kiểm tra lại",
        "vừa gọi không đúng",
        "hoặc liên hệ số",
        "để được hỗ trợ",
        "kiểm tra lại",
        "kiểm tra",
        "không đúng",
    ],
]

MAX_WAITING_TONE = 8


def keyword_in_text(input_text: str) -> int:
    input_text = input_text.lower()
    if input_text.strip() == "":
        # return index of "mute"
        return input_text.index("mute")

    if len(input_text) <= MAX_WAITING_TONE:
        # define keyword if needed
        return input_text.index("waiting_tone")

    for i, kws in enumerate(keyword_labels):
        for kw in kws:
            if kw in input_text:
                return i

    # ringback tone
    return input_text.index("rinback_tone")


if __name__ == "__main__":
    test_texts = [
        "đang tạm khóa khuyên quý khách vui lòng tải lại tàu tích hợp lâm thu hoạch cho biết hết câu của quý ông",
        "cất tạm khóa khuyên quý khách vui lòng hợp lấy đâu kích thước lâm thôi du khách ta kích thích tố quyết định",
        "khám khóa khuyên quý khách vui lòng hỏi lại thao tịch hữu lượm thu hợp cho lợi ích hấp pháp của quý sao được",
    ]

    for text in test_texts:
        print(f"Input: {text}")
        print(f"Output: {keyword_in_text(text)}")
        print()
