from enum import Enum

class CommercialViolationTypes(Enum):
    """
    Enum for specific types of commercial violations.
    """
    INTELLECTUAL_PROPERTY_INFRINGEMENT = "侵犯他人知识产权"
    UNETHICAL_BUSINESS_PRACTICES = "违反商业道德"
    TRADE_SECRET_LEAKAGE = "泄露他人商业秘密"
    MONOPOLISTIC_BEHAVIOR = "利用算法、数据、平台等优势实施垄断和不正当竞争行为"
    OTHER_COMMERCIAL_VIOLATIONS = "其他商业违法违规行为"
