from typing import List
from deepteam.frameworks.frameworks import AISafetyFramework
from deepteam.vulnerabilities import (
    SocialistValuesViolation,
    SocialistValuesViolationTypes,
    DiscriminatoryContent,
    DiscriminatoryContentTypes,
    CommercialViolation,
    CommercialViolationTypes,
    RightsInfringement,
    RightsInfringementTypes,
    ServiceSafety,
    ServiceSafetyTypes,
)

class ChinaGAISec(AISafetyFramework):
    """
    Framework based on China's "Generative Artificial Intelligence Service Security Basic Requirements".

    This framework consolidates vulnerabilities related to content security as outlined
    in the Chinese national standard for generative AI. It covers key areas such as:
    - Adherence to Socialist core values
    - Prevention of discriminatory content
    - Avoidance of commercial violations
    - Protection of individual rights
    - Ensuring service safety and reliability
    """
    name: str = "China Gen-AI Security"
    description: str = "A framework to test for vulnerabilities based on China's 'Generative AI Service Security Basic Requirements'."

    def __init__(self):
        self.vulnerabilities = [
            SocialistValuesViolation(types=[t for t in SocialistValuesViolationTypes]),
            DiscriminatoryContent(types=[t for t in DiscriminatoryContentTypes]),
            CommercialViolation(types=[t for t in CommercialViolationTypes]),
            RightsInfringement(types=[t for t in RightsInfringementTypes]),
            ServiceSafety(types=[t for t in ServiceSafetyTypes]),
        ]
        self.attacks = []  # Attacks can be added later if needed
        self.risk_categories = []
        super().__init__(
            name=self.name,
            description=self.description,
            vulnerabilities=self.vulnerabilities,
            attacks=self.attacks,
            risk_categories=self.risk_categories,
        )

    def get_name(self):
        return self.name
