"""Gọi API GPT để dịch, tự phát hiện ngôn ngữ + xử lý cờ en/zh."""
import logging
import re

from openai import AsyncOpenAI

import config

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)

# Regex nhận diện chữ Hán
_CJK = re.compile(r"[\u4e00-\u9fff]")
# Regex nhận diện chữ tiếng Việt có dấu
_VN = re.compile(r"[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệ"
                 r"ìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
                 r"ùúủũụưứừửữựỳýỷỹỵđ]", re.IGNORECASE)


def detect_and_route(text: str) -> tuple[str, str, str]:
    """
    Trả về (source_lang, target_lang, clean_text).
    Quy tắc:
      - Có chữ Hán            -> zh -> vi
      - Có ký hiệu cờ 'en'    -> vi -> en
      - Có ký hiệu cờ 'zh'    -> vi -> zh
      - Tiếng Việt (mặc định) -> vi -> en
      - Còn lại (Anh)         -> en -> vi
    """
    stripped = text.strip()

    # 1) Ưu tiên chữ Hán
    if _CJK.search(stripped):
        return "zh", "vi", stripped

    # 2) Kiểm tra cờ en/zh ở đầu hoặc cuối câu (vd: "en xin chào", "xin chào /zh")
    flag_match = re.match(r"^\s*[/]?(en|zh)\b[:\s]*(.+)$", stripped, re.IGNORECASE | re.DOTALL)
    if not flag_match:
        flag_match = re.match(r"^(.+?)\s+[/]?(en|zh)\s*$", stripped, re.IGNORECASE | re.DOTALL)
        if flag_match:
            body, flag = flag_match.group(1), flag_match.group(2)
            return "vi", flag.lower(), body.strip()
    else:
        flag, body = flag_match.group(1), flag_match.group(2)
        return "vi", flag.lower(), body.strip()

    # 3) Tiếng Việt có dấu -> mặc định dịch sang tiếng Anh
    if _VN.search(stripped):
        return "vi", "en", stripped

    # 4) Còn lại coi là tiếng Anh -> dịch sang tiếng Việt
    return "en", "vi", stripped


_LANG_NAME = {"vi": "Tiếng Việt", "en": "Tiếng Anh (English)", "zh": "Tiếng Trung (中文)"}


def _build_prompt(source: str, target: str) -> str:
    base = (
        "Bạn là trợ lý dịch thuật chuyên nghiệp. "
        "Dịch tự nhiên, rõ ràng, ngắn gọn, mạch lạc, dễ hiểu. "
        "Chỉ trả về bản dịch, KHÔNG giải thích thừa, KHÔNG lời dẫn.\n"
    )
    if target == "zh":
        base += (
            f"Dịch từ {_LANG_NAME[source]} sang {_LANG_NAME[target]}.\n"
            "Dùng từ vựng và ngữ pháp mức HSK4–HSK5 (phổ thông, dễ hiểu).\n"
            "Định dạng bắt buộc, mỗi phần trên một dòng:\n"
            "🇨🇳 <câu tiếng Trung, bọc trong dấu ` để bấm copy>\n"
            "🔤 <pinyin có dấu thanh>\n"
            "🇻🇳 <nghĩa tiếng Việt>\n"
        )
    elif source == "zh":
        base += (
            f"Dịch từ {_LANG_NAME[source]} sang {_LANG_NAME[target]}.\n"
            "Định dạng bắt buộc, mỗi phần trên một dòng:\n"
            "🇻🇳 <nghĩa tiếng Việt, bọc trong dấu ` để bấm copy>\n"
            "🔤 <pinyin của câu gốc, có dấu thanh>\n"
            "🇨🇳 <nhắc lại câu tiếng Trung gốc>\n"
        )
    else:
        base += (
            f"Dịch từ {_LANG_NAME[source]} sang {_LANG_NAME[target]}.\n"
            "Trả về đúng một dòng: bản dịch bọc trong dấu ` để bấm copy được.\n"
        )
    return base


async def translate(text: str) -> str:
    source, target, clean = detect_and_route(text)
    system_prompt = _build_prompt(source, target)

    resp = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": clean},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
