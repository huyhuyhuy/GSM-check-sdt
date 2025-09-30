labels = [
    "leave_message",
    "be_blocked",
    "can_not_connect",
    "incorrect",
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


def keyword_in_text(input_text: str, keywords: list[str]) -> bool:
    input_text = input_text.lower()
    for kw in keywords:
        if kw in input_text:
            return True
    return False


if __name__ == "__main__":
    test_texts = [
        "đang tạm khóa khuyên quý khách vui lòng tải lại tàu tích hợp lâm thu hoạch cho biết hết câu của quý ông",
        "cất tạm khóa khuyên quý khách vui lòng hợp lấy đâu kích thước lâm thôi du khách ta kích thích tố quyết định",
        "khám khóa khuyên quý khách vui lòng hỏi lại thao tịch hữu lượm thu hợp cho lợi ích hấp pháp của quý sao được",
    ]

    for text in test_texts:
        print(f"Input: {text}")
        for i, kws in enumerate(keyword_labels):
            if keyword_in_text(text, kws):
                print(f"  => Matched label: {labels[i]}")
        print()
