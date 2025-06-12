import os
import json
import logging
from dotenv import load_dotenv # <--- Add this import
from mistralai import Mistral # Changed client import
# Removed ChatMessage import

load_dotenv() # <--- Call this function to load .env

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure logs are visible

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    logger.warning("MISTRAL_API_KEY environment variable not set. LLM calls will likely fail.")
    # You could raise an error here, or let it fail when used. For now, just warn.

mistral_client = Mistral(api_key=MISTRAL_API_KEY) # Changed client instantiation

ACTION_MODEL_NAME = os.getenv("MISTRAL_ACTION_MODEL_NAME", "mistral-small-latest")
VISION_MODEL_NAME = os.getenv("MISTRAL_VISION_MODEL_NAME", "mistral-small-latest") # Using a text-based model for "vision"

def get_action_prompt_system_message() -> str:
    """
    Returns the detailed system prompt for the Mistral Action LLM.
    Specifies available actions and the required JSON output format.
    """
    # Note: JSON examples within the prompt must be valid JSON.
    # Using single quotes for Python strings and double quotes for JSON keys/strings inside.
    prompt = """
You are an AI assistant that translates natural language user requests into specific structured JSON commands.
Based on the user's message, choose one of the following actions and provide the necessary parameters in JSON format.

Available Actions:
1.  `terminal_command_foreground`: Executes a shell command in the foreground and streams its output.
    - Parameters: `{"command": "shell_command_string"}`
    - Example: `{"action_type": "terminal_command_foreground", "parameters": {"command": "ls -la"}}`
2.  `terminal_command_background`: Executes a shell command in the background.
    - Parameters: `{"command": "shell_command_string"}`
    - Example: `{"action_type": "terminal_command_background", "parameters": {"command": "sleep 30 &"}}`
3.  `file_write`: Writes content to a specified file in the 'CUA' directory.
    - Parameters: `{"filename": "name_of_file.ext", "content": "content_to_write"}`
    - Example: `{"action_type": "file_write", "parameters": {"filename": "example.txt", "content": "Hello from Orbitron!"}}`
4.  `browser_go_to`: Navigates the current browser tab to a URL.
    - Parameters: `{"url": "full_url_string"}`
    - Example: `{"action_type": "browser_go_to", "parameters": {"url": "https://www.google.com"}}`
5.  `browser_new_tab`: Opens a new browser tab.
    - Parameters: `{"url": "optional_url_to_open_in_new_tab"}` (If no URL, opens 'about:blank')
    - Example: `{"action_type": "browser_new_tab", "parameters": {"url": "https://www.bing.com"}}` or `{"action_type": "browser_new_tab", "parameters": {}}`
6.  `browser_switch_tab`: Switches to a specific browser tab by its 0-based index.
    - Parameters: `{"index": tab_index_integer}`
    - Example: `{"action_type": "browser_switch_tab", "parameters": {"index": 0}}`
7.  `browser_scroll`: Scrolls the current browser page. (Future capability, not yet fully implemented)
    - Parameters: `{"direction": "up" | "down" | "top" | "bottom", "amount_pixels": optional_pixel_amount_integer}`
    - Example: `{"action_type": "browser_scroll", "parameters": {"direction": "down", "amount_pixels": 500}}`
8.  `browser_press_key`: Simulates a key press in the browser. (Future capability)
    - Parameters: `{"key_name": "Enter" | "Escape" | "Tab" | "Space" | "PageUp" | "PageDown" ...}`
    - Example: `{"action_type": "browser_press_key", "parameters": {"key_name": "Escape"}}`
9.  `browser_click_element`: Clicks on a specific element identified by a selector or ID. (Future capability)
    - Parameters: `{"selector_or_id": "css_selector_or_element_id_string", "description": "brief_description_of_element"}`
    - Example: `{"action_type": "browser_click_element", "parameters": {"selector_or_id": "#submitButton", "description": "the login button"}}`
10. `vision_query`: Asks a question about the current browser page's text content.
    - Parameters: `{"query": "user_question_about_page_content"}`
    - Example: `{"action_type": "vision_query", "parameters": {"query": "What is the main headline of this page?"}}`
11. `message`: If no other action is appropriate, or to provide a general text response.
    - Parameters: `{"content": "text_response_to_user"}`
    - Example: `{"action_type": "message", "parameters": {"content": "Hello! How can I help you today?"}}`

Output ONLY the JSON command. Do not include any other text, explanations, or markdown formatting.
The JSON should be a single object with "action_type" and "parameters" (which is another object).
If the user's request is unclear or lacks necessary information for a command, use the "message" action_type to ask for clarification.
If a command is trivial e.g. "say hello", use the "message" action_type.
If the user's input is a general question (e.g., 'What is the capital of France?', 'How does photosynthesis work?'), a greeting, or a simple request for information you possess, and it does not fit any of the other defined actions, use the 'message' action_type to provide a direct textual response.
"""
    return prompt.strip()

async def get_mistral_action(user_message: str, chat_history: list[dict] | None = None) -> dict:
    """
    Gets an action dictionary from Mistral AI based on user message and chat history.
    """
    if not MISTRAL_API_KEY:
        return {"action_type": "error", "parameters": {"content": "Mistral API key not configured."}}

    messages = [{"role": "system", "content": get_action_prompt_system_message()}]
    if chat_history:
        for entry in chat_history:
            # Ensure role and content are present
            if "role" in entry and "content" in entry:
                 messages.append({"role": entry["role"], "content": str(entry["content"])}) # Ensure content is string

    messages.append({"role": "user", "content": user_message})

    logger.debug(f"Sending to Mistral Action Model ({ACTION_MODEL_NAME}): {messages}")

    try:
        response = mistral_client.chat(model=ACTION_MODEL_NAME, messages=messages, temperature=0.1) # Lower temp for more deterministic JSON
        llm_output_text = response.choices[0].message.content
        logger.info(f"Raw LLM action output: {llm_output_text}") # Added more specific logging here

        # Attempt to extract JSON from the response
        # LLMs can sometimes wrap the JSON in markdown or add other text.
        json_start = llm_output_text.find('{')
        json_end = llm_output_text.rfind('}') + 1

        if json_start != -1 and json_end > json_start:
            json_str = llm_output_text[json_start:json_end]
            try:
                json_object = json.loads(json_str)

                # Validate basic structure
                action_type = json_object.get("action_type")
                parameters = json_object.get("parameters")

                if not action_type:
                    logger.error(f"LLM response missing 'action_type': {json_object}")
                    return {"action_type": "error", "parameters": {"content": "LLM response incomplete (missing action_type)."}}

                # Define actions that strictly require a parameters dictionary.
                # 'message' might have content in parameters, 'browser_new_tab' might not.
                actions_requiring_params_dict = [
                    "terminal_command_foreground", "terminal_command_background",
                    "file_write", "browser_go_to", "browser_switch_tab",
                    "vision_query", "browser_scroll", "browser_press_key", "browser_click_element"
                    # 'message' action's 'content' is also in parameters, so it implicitly requires it.
                    # 'browser_new_tab' is flexible; parameters might be empty or contain a URL.
                ]
                # A more nuanced check: if parameters is expected to exist (even if empty for some action_types)
                if action_type not in ["browser_new_tab"] and parameters is None : # browser_new_tab can have empty parameters
                     logger.error(f"LLM response for {action_type} missing 'parameters' field entirely: {json_object}")
                     return {"action_type": "error", "parameters": {"content": f"LLM response for {action_type} incomplete (missing parameters field)."}}

                # If parameters field exists, for certain actions it must be a dictionary.
                if action_type in actions_requiring_params_dict and not isinstance(parameters, dict):
                    logger.error(f"LLM response for {action_type} has invalid 'parameters' (not a dictionary): {json_object}")
                    return {"action_type": "error", "parameters": {"content": f"LLM response for {action_type} incomplete (invalid parameters type)."}}

                return json_object

            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError parsing LLM output: {e}. Text was: {json_str}")
                return {"action_type": "error", "parameters": {"content": "Error: LLM returned malformed JSON."}}
        else:
            logger.error(f"No JSON object found in LLM response: {llm_output_text}")
            # If no JSON, treat the whole output as a message to the user.
            return {"action_type": "message", "parameters": {"content": f"LLM response (no JSON found): {llm_output_text}"}}

    except Exception as e:
        logger.error(f"Error calling Mistral API or processing response: {e}", exc_info=True)
        return {"action_type": "error", "parameters": {"content": f"Error communicating with LLM: {str(e)}"}}


async def get_mistral_vision_analysis(page_text_content: str, user_vision_prompt: str) -> str:
    """
    Analyzes text content from a webpage using Mistral AI to answer a user's question.
    This is a text-based "vision" model.
    """
    if not MISTRAL_API_KEY:
        return "Error: Mistral API key not configured."

    system_prompt = (
        "You are an intelligent assistant. Based on the following text content extracted from a webpage, "
        "answer the user's question. Be concise and focus on the provided text. "
        "If the information is not present in the text, say so."
    )

    # Limit context size for the prompt to avoid overly long inputs
    max_text_len = 8000 # Adjust as needed based on model context window and typical page sizes
    truncated_page_content = page_text_content[:max_text_len]
    if len(page_text_content) > max_text_len:
        truncated_page_content += "\n[Content truncated due to length]"

    combined_prompt = f"Webpage Text Content:\n---\n{truncated_page_content}\n---\nUser's Question: {user_vision_prompt}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": combined_prompt}
    ]
    logger.debug(f"Sending to Mistral Vision Model ({VISION_MODEL_NAME}): {messages}")

    try:
        response = mistral_client.chat(model=VISION_MODEL_NAME, messages=messages)
        analysis = response.choices[0].message.content
        logger.info(f"Mistral Vision Model response: {analysis}")
        return analysis
    except Exception as e:
        logger.error(f"Error calling Mistral API for vision analysis: {e}", exc_info=True)
        return f"Error performing vision analysis: {str(e)}"
