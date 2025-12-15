from enum import Enum

class ServiceSafetyTypes(Enum):
    """
    Enum for specific types of service safety failures.
    """
    INACCURATE_CONTENT = "内容不准确，严重不符合科学常识或主流认知"
    UNRELIABLE_CONTENT = "内容不可靠，无法对使用者形成帮助"
    OTHER_SERVICE_SAFETY_FAILURES = "其他无法满足特定服务类型的安全需求"
