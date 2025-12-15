from enum import Enum

class SocialistValuesViolationTypes(Enum):
    """
    违反社会主义核心价值观的具体风险点枚举。
    """
    SUBVERT_STATE_POWER = "煽动颠覆国家政权、推翻社会主义制度"
    ENDANGER_NATIONAL_SECURITY = "危害国家安全和利益、损害国家形象"
    INCITE_SEPARATISM = "煽动分裂国家、破坏国家统一和社会稳定"
    PROMOTE_TERRORISM = "宣扬恐怖主义、极端主义"
    PROMOTE_ETHNIC_HATRED = "宣扬民族仇恨"
    PROMOTE_VIOLENCE_PORNOGRAPHY = "宣扬暴力、淫秽色情"
    SPREAD_FALSE_INFORMATION = "传播虚假有害信息"
    OTHER_ILLEGAL_CONTENT = "其他法律、行政法规禁止的内容"
