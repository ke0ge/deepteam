
import asyncio
import aiohttp
import json
import os
import uuid
from typing import List, Optional, Tuple, Union, Dict
from pydantic import BaseModel
from openai.types.chat import ChatCompletion
from deepeval.models.llms.utils import trim_and_load_json
from deepeval.models import LocalModel
from deepteam.test_case import RTTurn
from deepteam.red_teamer import RedTeamer
from deepteam.vulnerabilities import PromptLeakage,Bias,IllegalActivity
from deepteam.attacks.multi_turn import SequentialJailbreak,CrescendoJailbreaking
from deepteam.attacks.single_turn import Roleplay, GrayBox

# Import our new logger
from deepteam.logger_setup import logger

# --- Monkey-Patching Section (Full Copy Method) ---

async def logged_a_generate_full_copy(
    self, prompt: str, schema: Optional[BaseModel] = None
) -> Tuple[Union[str, Dict], float]:
    call_id = uuid.uuid4()
    model_name = self.model or self.__class__.__name__
    logger.debug(f"--- ASYNC LLM CALL [{model_name}] | ID: {call_id} ---")
    logger.debug(f"PROMPT (ID: {call_id}):\n{prompt}")
    try:
        # This logic is a direct copy of LocalModel.a_generate, with logging added
        client = self.load_model(async_mode=True)
        response: ChatCompletion = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            **self.generation_kwargs,
        )
        res_content = response.choices[0].message.content
        logger.debug(f"RESPONSE (ID: {call_id}):\n{res_content}")

        if schema:
            json_output = trim_and_load_json(res_content)
            return schema.model_validate(json_output), 0.0
        else:
            return res_content, 0.0
    except Exception as e:
        logger.error(f"LLM call to [{model_name}] failed (ID: {call_id}): {e}", exc_info=True)
        raise
    finally:
        logger.debug(f"--- END ASYNC LLM CALL [{model_name}] | ID: {call_id} ---")


def logged_generate_full_copy(
    self, prompt: str, schema: Optional[BaseModel] = None
) -> Tuple[Union[str, Dict], float]:
    call_id = uuid.uuid4()
    model_name = self.model or self.__class__.__name__
    logger.debug(f"--- SYNC LLM CALL [{model_name}] | ID: {call_id} ---")
    logger.debug(f"PROMPT (ID: {call_id}):\n{prompt}")
    try:
        # This logic is a direct copy of LocalModel.generate, with logging added
        client = self.load_model(async_mode=False)
        response: ChatCompletion = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            **self.generation_kwargs,
        )
        res_content = response.choices[0].message.content
        logger.debug(f"RESPONSE (ID: {call_id}):\n{res_content}")

        if schema:
            json_output = trim_and_load_json(res_content)
            return schema.model_validate(json_output), 0.0
        else:
            return res_content, 0.0
    except Exception as e:
        logger.error(f"LLM call to [{model_name}] failed (ID: {call_id}): {e}", exc_info=True)
        raise
    finally:
        logger.debug(f"--- END SYNC LLM CALL [{model_name}] | ID: {call_id} ---")


# Apply the new monkey-patch
LocalModel.a_generate = logged_a_generate_full_copy
LocalModel.generate = logged_generate_full_copy

# --- End of Monkey-Patching Section ---


# Import the client from our refactored module
from chat_dida import DidaApiClient, BASE_URL, COOKIES, APP_ID, PROXY_URL
from deepteam.attacks.multi_turn import BaseMultiTurnAttack
# --- Callback Strategies ---

async def single_turn_callback_factory(*args, **kwargs):
    """
    Factory function that creates a new client and session for each call.
    Ideal for independent, single-turn attacks.
    """
    client = DidaApiClient(BASE_URL, COOKIES, APP_ID, PROXY_URL)
    initialized = await client.initialize()
    if not initialized:
        raise ConnectionError("Failed to initialize Dida API client for a single-turn attack.")
    return await client.chat(*args, **kwargs)

def get_multi_turn_callback():
    """
    Creates a stateful callback for multi-turn attacks.
    It uses a single client instance throughout the attack.
    """
    # 1. A single client is created and lives within this closure.
    client = DidaApiClient(BASE_URL, COOKIES, APP_ID, PROXY_URL)
    logger.info(f"Multi-turn DidaApiClient instance created with object ID: {id(client)}")

    async def callback(*args, **kwargs):
        """
        The actual callback function passed to the red teamer.
        It ensures the client is initialized before chatting.
        """
        # 2. Check which client instance this callback is using.
        logger.debug(f"Multi-turn callback is using client instance with object ID: {id(client)}")
        if not client.conversation_id:
            # 3. If not, initialize it once.
            initialized = await client.initialize()
            if not initialized:
                raise ConnectionError("Failed to initialize Dida API client for multi-turn attack.")
        
        # 4. Now, call the chat method on the persistent client.
        return await client.chat(*args, **kwargs)

    return callback

# Part 2: Main execution logic, adapted from my.yaml
async def main():
    logger.info("--- Starting Red Teaming Process ---")

    # Configure the simulator models
    api_key = "sk-aasd12esazdx"
    simulator_model = LocalModel(
        model="gemini-2.5-pro-nothinking",
        api_key=api_key,
        base_url="http://127.0.0.1:8888/v1/"
    )
    
    evaluation_model = LocalModel(
        model="gemini-2.5-flash",
        api_key=api_key,
        base_url="http://127.0.0.1:8888/v1/"
    )

    # Instantiate the RedTeamer with parameters from my.yaml
    red_teamer = RedTeamer(
        simulator_model=simulator_model,
        evaluation_model=evaluation_model,
        target_purpose="A helpful Campus AI Assistant",
        async_mode=True,
        max_concurrent=3  # from system_config.max_concurrent
    )

    # Define the vulnerabilities to test
    vulnerabilities = [
        # PromptLeakage(types=[#"secrets_and_credentials",
        #                      "instructions",
        #                      "guard_exposure",
        #                      #"permissions_and_roles",
        #                      ])
        IllegalActivity(types=["illegal_drugs"])
    ]

    # Define the attack methods to use
    attacks = [
        # CrescendoJailbreaking(
        #     simulator_model=simulator_model,
        #     weight=1.0,
        #     max_rounds=3, # Using a small number of rounds for a quick test
        # )
        GrayBox(weight=2, max_retries=7)
    ]

    # --- Determine Callback Strategy based on Attack Type ---
    # This is a simplified check. A more robust implementation might inspect
    # all attacks if a mix is possible. We'll assume the first attack determines the type.
    if attacks and isinstance(attacks[0], BaseMultiTurnAttack):
        logger.info("Multi-turn attack detected. Using a single persistent session for the callback.")
        model_callback = get_multi_turn_callback()
    else:
        logger.info("Single-turn attack detected. Using a new session for each callback.")
        model_callback = single_turn_callback_factory
    
    # Execute the red teaming process
    risk_assessment = await red_teamer.a_red_team(
        model_callback=model_callback,
        vulnerabilities=vulnerabilities,
        attacks=attacks,
        attacks_per_vulnerability_type=1,  # from system_config.attacks_per_vulnerability_type
        ignore_errors=False
    )

    # Process and save the results
    print("\\n✅ Red Teaming Process Finished!")
    
    # You can save the report to a local folder
    output_folder = "results"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    report_path = risk_assessment.save(to=output_folder)
    print(f"📄 Risk assessment report saved to: {report_path}")

    # You can also access the overview directly
    # print("\\n📊 Assessment Overview:")
    # print(risk_assessment.overview)

# Part 3: Run the main function
if __name__ == "__main__":
    try:
        # If you are on Windows and encounter an asyncio error, you might need the following line:
        # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
