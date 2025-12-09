
import asyncio
import aiohttp
import json
import os
from typing import List, Optional
from deepeval.models import LocalModel
from deepteam.test_case import RTTurn
from deepteam.red_teamer import RedTeamer
from deepteam.vulnerabilities import PromptLeakage
from deepteam.attacks.multi_turn import CrescendoJailbreaking

# Import our new logger
from deepteam.logger_setup import logger

# --- Monkey-Patching Section ---
# Store the original methods that call the LLMs
original_a_generate = LocalModel.a_generate
original_generate = LocalModel.generate

# Define our new async method with logging
async def logged_a_generate(self, *args, **kwargs):
    model_name = self.model or self.__class__.__name__
    prompt = kwargs.get('prompt', args[0] if args else 'N/A')
    
    logger.debug(f"--- ASYNC LLM CALL [{model_name}] ---")
    logger.debug(f"PROMPT:\n{prompt}")
    
    try:
        # Call the original method
        result = await original_a_generate(self, *args, **kwargs)
        logger.debug(f"RESPONSE:\n{result}")
        return result
    except Exception as e:
        logger.error(f"LLM call to [{model_name}] failed: {e}")
        raise
    finally:
        logger.debug(f"--- END ASYNC LLM CALL [{model_name}] ---")


# Define our new sync method with logging (for completeness)
def logged_generate(self, *args, **kwargs):
    model_name = self.model or self.__class__.__name__
    prompt = kwargs.get('prompt', args[0] if args else 'N/A')
    
    logger.debug(f"--- SYNC LLM CALL [{model_name}] ---")
    logger.debug(f"PROMPT:\n{prompt}")
    
    try:
        # Call the original method
        result = original_generate(self, *args, **kwargs)
        logger.debug(f"RESPONSE:\n{result}")
        return result
    except Exception as e:
        logger.error(f"LLM call to [{model_name}] failed: {e}")
        raise
    finally:
        logger.debug(f"--- END SYNC LLM CALL [{model_name}] ---")


# Apply the patches
LocalModel.a_generate = logged_a_generate
LocalModel.generate = logged_generate
# --- End of Monkey-Patching Section ---


# Part 1: Define the model callback function, adapted from callback.py, now with logging
async def model_callback(input_str: str, turns: Optional[List[RTTurn]] = None) -> str:
    """
    Callback function to adapt to the target API.
    Handles both single-turn and multi-turn scenarios.
    """
    logger.info("--- TARGET MODEL CALL ---")
    logger.info(f"INPUT: {input_str}")
    if turns:
        logger.debug(f"Received {len(turns)} turns in conversation history.")

    url = "https://llm-fy-legal.fuyuncc.com/aodesai-pulomixiusi-heidee/plux"
    token = os.getenv("API_TOKEN", "1246g2i2365b4cbc9u40a9fa5ctwa471")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Construct the dialogue from turns if available, otherwise use input_str
    if turns:
        dialogue = [{"role": turn.role, "content": turn.content} for turn in turns]
    else:
        dialogue = [{"role": "user", "content": input_str}]

    payload = {
        "dialogue": dialogue,
        "model": "legal_llm",
        "stream": False
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                if response.status == 200:
                    logger.info(f"OUTPUT (status {response.status}):\n{response_text}")
                    # IMPORTANT: The original code returned the full JSON.
                    # If the target model returns JSON, we should extract the text.
                    # Assuming the actual content is in result['choices'][0]['message']['content']
                    try:
                        result_json = json.loads(response_text)
                        # Modify this line based on the actual API response structure
                        # return result_json['choices'][0]['message']['content']
                        return response_text # For now, return the full text to match original behavior
                    except json.JSONDecodeError:
                         return response_text # Return as plain text if not JSON
                else:
                    error_message = f"Error: API returned status code {response.status}, message: {response_text}"
                    logger.error(error_message)
                    return error_message
        except Exception as e:
            error_message = f"Error: Request failed - {str(e)}"
            logger.error(error_message)
            return error_message

# Part 2: Main execution logic, adapted from my.yaml
async def main():
    logger.info("--- Starting Red Teaming Process ---")

    # Configure the models to use OpenRouter (API compatible with OpenAI)
    # openrouter_api_key = "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"
    # model = "tngtech/deepseek-r1t2-chimera:free"
    # url = "https://openrouter.ai/api/v1"
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
        target_purpose="A helpful AI legal assistant",
        async_mode=True,
        max_concurrent=3  # from system_config.max_concurrent
    )

    # Define the vulnerabilities to test
    vulnerabilities = [
        PromptLeakage(types=["instructions"])
    ]

    # Define the attack methods to use
    attacks = [
        CrescendoJailbreaking(simulator_model=simulator_model, weight=1.0)
    ]

    # Execute the red teaming process
    risk_assessment = await red_teamer.a_red_team(
        model_callback=model_callback,
        vulnerabilities=vulnerabilities,
        attacks=attacks,
        attacks_per_vulnerability_type=10,  # from system_config.attacks_per_vulnerability_type
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
