from enum import Enum

class DiscriminatoryContentTypes(Enum):
    """
    Enum for specific types of discriminatory content.
    """
    ETHNIC_DISCRIMINATION = "民族歧视内容"
    FAITH_DISCRIMINATION = "信仰歧视内容"
    NATIONAL_DISCRIMINATION = "国别歧视内容"
    REGIONAL_DISCRIMINATION = "地域歧视内容"
    GENDER_DISCRIMINATION = "性别歧视内容"
    AGE_DISCRIMINATION = "年龄歧视内容"
    OCCUPATIONAL_DISCRIMINATION = "职业歧视内容"
    HEALTH_DISCRIMINATION = "健康歧视内容"
    OTHER_DISCRIMINATION = "其他方面歧视内容"
