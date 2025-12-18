from typing import List, Optional, Union
import json

from deepeval.models import DeepEvalBaseLLM
from deepeval.metrics.utils import initialize_model

from deepteam.attacks.multi_turn.base_multi_turn_attack import BaseMultiTurnAttack
from deepteam.attacks.base_attack import Exploitability
from deepteam.attacks.attack_simulator.utils import generate, a_generate
from deepteam.attacks.multi_turn.echo_chamber_attack.schema import EchoChamberAttackData, AdaptiveAttackData
from deepteam.attacks.multi_turn.echo_chamber_attack.template import EchoChamberAttackTemplate
from deepteam.attacks.multi_turn.types import CallbackType
from deepteam.test_case.test_case import RTTurn
from deepteam.utils import create_progress, add_pbar, update_pbar

class EchoChamberAttack(BaseMultiTurnAttack):
    """
    Implements the Echo Chamber Attack, a multi-turn strategy that manipulates an LLM
    by dynamically generating a conversational script and then executing it.
    """

    name: str = "Echo Chamber Attack"
    description: str = "A multi-turn attack that first generates a script to create a logical echo chamber, then executes it to guide an LLM to produce harmful content."
    exploitability: Exploitability = Exploitability.HIGH
    multi_turn: bool = True

    def __init__(
        self,
        max_rounds: int = 5, # Default max rounds for the generated script
        simulator_model: Optional[Union[DeepEvalBaseLLM, str]] = "gpt-4o-mini",
    ):
        self.max_rounds = max_rounds
        self.simulator_model = simulator_model

    def _generate_attack_script(self, conversation_objective: str) -> EchoChamberAttackData:
        """Dynamically generates the attack script using the simulator model."""
        prompt = EchoChamberAttackTemplate.generate_script_prompt(conversation_objective)
        # By providing the EchoChamberAttackData schema, the `generate` function
        # will handle JSON cleaning, parsing, and validation automatically, returning a single Pydantic object.
        attack_data = generate(
            prompt, schema=EchoChamberAttackData, model=self.simulator_model
        )
        return attack_data

    async def _a_generate_attack_script(self, conversation_objective: str) -> EchoChamberAttackData:
        """Async version of _generate_attack_script."""
        prompt = EchoChamberAttackTemplate.generate_script_prompt(conversation_objective)
        # By providing the EchoChamberAttackData schema, the `a_generate` function
        # will handle JSON cleaning, parsing, and validation automatically, returning a single Pydantic object.
        attack_data = await a_generate(
            prompt, schema=EchoChamberAttackData, model=self.simulator_model
        )
        return attack_data


    def _get_turns(
        self,
        model_callback: CallbackType,
        turns: Optional[List[RTTurn]] = None,
        vulnerability: str = None,
        vulnerability_type: str = None,
    ) -> List[RTTurn]:
        if not turns:
            raise ValueError("Conversation history ('turns') is required for this attack.")

        self.simulator_model, _ = initialize_model(self.simulator_model)
        
        conversation_objective = turns[0].content

        # 1. Dynamically generate the attack script (seeding and execution prompts)
        attack_data = self._generate_attack_script(conversation_objective)

        # 2. Execute the attack
        attack_turns: List[RTTurn] = []
        
        progress = create_progress()
        with progress:
            # Progress bar is now less deterministic, let's count rounds
            task_id = add_pbar(progress, description="...... 🗣️ Echo Chamber Attack", total=self.max_rounds + 2)

            # Seeding Phase
            current_prompt = attack_data.seeding_prompt
            attack_turns.append(RTTurn(role="user", content=current_prompt))
            assistant_response = model_callback(current_prompt, attack_turns)
            attack_turns.append(RTTurn(role="assistant", content=assistant_response))
            update_pbar(progress, task_id)

            # Fully Adaptive Reinforcement Phase
            for _ in range(self.max_rounds):
                # The attacker model decides the next move in real-time
                system_prompt = EchoChamberAttackTemplate.attacker_system_prompt(
                    conversation_objective=conversation_objective,
                    conversation_history=json.dumps([t.model_dump() for t in attack_turns]),
                    target_last_response=assistant_response,
                )
                
                # The attacker model itself decides the strategy and crafts the prompt
                attack_model_messages = [{"role": "system", "content": system_prompt}]

                res: AdaptiveAttackData = generate(
                    json.dumps(attack_model_messages), AdaptiveAttackData, self.simulator_model
                )
                
                # If the attacker model decides it's time to execute, break the loop
                if res.strategy_for_this_turn.lower() == 'execute':
                    break

                current_prompt = res.generated_question
                attack_turns.append(RTTurn(role="user", content=current_prompt))
                assistant_response = model_callback(current_prompt, attack_turns)
                attack_turns.append(RTTurn(role="assistant", content=assistant_response))
                update_pbar(progress, task_id)

            # Execution Phase
            current_prompt = attack_data.execution_prompt
            attack_turns.append(RTTurn(role="user", content=current_prompt))
            assistant_response = model_callback(current_prompt, attack_turns)
            attack_turns.append(RTTurn(role="assistant", content=assistant_response))
            update_pbar(progress, task_id)
        
        return attack_turns

    async def _a_get_turns(
        self,
        model_callback: CallbackType,
        turns: Optional[List[RTTurn]] = None,
        vulnerability: str = None,
        vulnerability_type: str = None,
    ) -> List[RTTurn]:
        if not turns:
            raise ValueError("Conversation history ('turns') is required for this attack.")

        self.simulator_model, _ = initialize_model(self.simulator_model)
        
        conversation_objective = turns[0].content

        # 1. Dynamically generate the attack script (seeding and execution prompts)
        attack_data = await self._a_generate_attack_script(conversation_objective)

        # 2. Execute the attack
        attack_turns: List[RTTurn] = []
        
        progress = create_progress()
        with progress:
            # Progress bar is now less deterministic, let's count rounds
            task_id = add_pbar(progress, description="...... 🗣️ Echo Chamber Attack", total=self.max_rounds + 2)

            # Seeding Phase
            current_prompt = attack_data.seeding_prompt
            attack_turns.append(RTTurn(role="user", content=current_prompt))
            assistant_response = await model_callback(current_prompt, attack_turns)
            attack_turns.append(RTTurn(role="assistant", content=assistant_response))
            update_pbar(progress, task_id)

            # Fully Adaptive Reinforcement Phase
            for _ in range(self.max_rounds):
                # The attacker model decides the next move in real-time
                system_prompt = EchoChamberAttackTemplate.attacker_system_prompt(
                    conversation_objective=conversation_objective,
                    conversation_history=json.dumps([t.model_dump() for t in attack_turns]),
                    target_last_response=assistant_response,
                )
                
                # The attacker model itself decides the strategy and crafts the prompt
                attack_model_messages = [{"role": "system", "content": system_prompt}]

                res: AdaptiveAttackData = await a_generate(
                    json.dumps(attack_model_messages), AdaptiveAttackData, self.simulator_model
                )
                
                # If the attacker model decides it's time to execute, break the loop
                if res.strategy_for_this_turn.lower() == 'execute':
                    break
                
                current_prompt = res.generated_question
                attack_turns.append(RTTurn(role="user", content=current_prompt))
                assistant_response = await model_callback(current_prompt, attack_turns)
                attack_turns.append(RTTurn(role="assistant", content=assistant_response))
                update_pbar(progress, task_id)

            # Execution Phase
            current_prompt = attack_data.execution_prompt
            attack_turns.append(RTTurn(role="user", content=current_prompt))
            assistant_response = await model_callback(current_prompt, attack_turns)
            attack_turns.append(RTTurn(role="assistant", content=assistant_response))
            update_pbar(progress, task_id)
            
        return attack_turns

    def get_name(self) -> str:
        return self.name
