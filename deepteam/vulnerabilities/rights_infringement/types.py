from enum import Enum

class RightsInfringementTypes(Enum):
    """
    Enum for specific types of infringements on legitimate rights and interests.
    """
    HEALTH_HAZARD = "危害他人身心健康"
    PORTRAIT_RIGHTS_VIOLATION = "侵害他人肖像权"
    REPUTATION_DAMAGE = "侵害他人名誉权"
    HONOR_RIGHTS_VIOLATION = "侵害他人荣誉权"
    PRIVACY_VIOLATION = "侵害他人隐私权"
    PERSONAL_INFORMATION_VIOLATION = "侵害他人个人信息权益"
    OTHER_LEGAL_RIGHTS_VIOLATION = "侵犯他人其他合法权益"
