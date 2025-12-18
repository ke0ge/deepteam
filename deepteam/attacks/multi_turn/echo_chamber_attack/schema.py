from pydantic import BaseModel, Field

class EchoChamberAttackData(BaseModel):
    """
    Data model for the Echo Chamber Attack.
    This model outlines the pre-defined conversational path for the attack.
    """
    seeding_prompt: str = Field(
        ...,
        description="The initial, innocuous prompt to start the conversation and plant the 'seed'."
    )
    execution_prompt: str = Field(
        ...,
        description="The final prompt designed to trigger the harmful content, capitalizing on the established context."
    )

class AdaptiveAttackData(BaseModel):
    """
    Data model for the real-time, adaptive response from the attacker model.
    """
    strategy_for_this_turn: str = Field(
        ...,
        description="A brief description of the chosen strategy for the current turn (e.g., 'reinforce', 'steer', 'execute')."
    )
    generated_question: str = Field(
        ...,
        description="The next question to be sent to the target model, crafted based on the chosen strategy."
    )
