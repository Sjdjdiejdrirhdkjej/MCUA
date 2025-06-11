# from .mock_models import mock_action_model, mock_vision_model # No longer used
from .terminal_utils import run_shell_command, run_background_command
from .file_utils import write_cua_file, read_cua_file
from .browser_utils import browser_manager_instance as browser_manager
from .llm_utils import get_mistral_action, get_mistral_vision_analysis # Import Mistral functions
import asyncio
import json
import base64
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.chat_history_for_llm = [] # Stores {role: "user/assistant", content: "..."}
        self.MAX_HISTORY_LEN = 10 # Max number of user/assistant pairs for context

    async def _yield_browser_screenshot(self, bm_manager_instance):
        """Helper to take and yield a browser screenshot."""
        try:
            screenshot_bytes, ss_message = await bm_manager_instance.take_screenshot()
            if screenshot_bytes:
                b64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                yield json.dumps({"type": "clear_desktop"}) + "\n"
                yield json.dumps({"type": "desktop_mode_switch", "mode": "browser"}) + "\n"
                yield json.dumps({
                    "type": "desktop_content_set",
                    "content_type": "image_base64",
                    "data": b64_image,
                    "filename": f"browser_tab_{bm_manager_instance.current_page_index}_view.png"
                }) + "\n"
            else:
                yield json.dumps({"type": "message", "content": f"Screenshot failed: {ss_message}"}) + "\n"
        except Exception as e:
            logger.error(f"Error during screenshot yielding: {e}", exc_info=True)
            yield json.dumps({"type": "error", "content": f"Failed to capture or process screenshot: {str(e)}"}) + "\n"

    async def process_user_message(self, user_message: str):
        """
        Processes the user message using Mistral LLM for action determination,
        and yields the results as an asynchronous generator of JSON strings.
        """
        self.chat_history_for_llm.append({"role": "user", "content": user_message})

        # Get action from Mistral LLM
        # Pass only the last MAX_HISTORY_LEN turns (each turn is user + assistant message)
        # So, if MAX_HISTORY_LEN is 10, we pass last 20 messages.
        history_to_send = self.chat_history_for_llm[-(self.MAX_HISTORY_LEN * 2):]
        action_dict = await get_mistral_action(user_message, chat_history=history_to_send)

        action_type = action_dict.get("action_type")
        parameters = action_dict.get("parameters", {})

        # Log assistant's response or action to history
        llm_response_for_history = ""
        if action_type == "message" or action_type == "error":
            llm_response_for_history = parameters.get("content", "No content in LLM response.")
        else:
            llm_response_for_history = f"Performing action: {action_type} with params: {json.dumps(parameters)}"
        self.chat_history_for_llm.append({"role": "assistant", "content": llm_response_for_history})

        # Trim history if it gets too long
        if len(self.chat_history_for_llm) > self.MAX_HISTORY_LEN * 2: # Keep last N pairs
            self.chat_history_for_llm = self.chat_history_for_llm[-(self.MAX_HISTORY_LEN * 2):]

        # Handle the action
        if action_type == "message":
            yield json.dumps({"type": "message", "content": parameters.get('content', '')}) + "\n"

        elif action_type == "terminal_command_foreground":
            command_to_run = parameters.get('command')
            if not command_to_run:
                yield json.dumps({"type": "error", "content": "LLM chose 'terminal_command_foreground' but provided no command."}) + "\n"
                # No return here, allow flow to potential generic error handler if added later, or just end.
            else:
                try:
                    yield json.dumps({"type": "clear_desktop"}) + "\n"
                    yield json.dumps({"type": "desktop_mode_switch", "mode": "terminal"}) + "\n"
                    yield json.dumps({"type": "desktop_content_stream_start"}) + "\n"

                    full_terminal_log = []
                    async for term_output_obj in run_shell_command(command_to_run):
                        # term_output_obj is now a dict like {"type": "stdout/stderr/exit_code", ...}
                        line_content = term_output_obj.get("line", "")
                        if term_output_obj.get("type") == "stdout":
                            full_terminal_log.append(line_content)
                            yield json.dumps({"type": "desktop_content_stream", "stream_type": "stdout", "content": line_content}) + "\n"
                        elif term_output_obj.get("type") == "stderr":
                            full_terminal_log.append(f"STDERR: {line_content}")
                            yield json.dumps({"type": "desktop_content_stream", "stream_type": "stderr", "content": line_content}) + "\n"
                        elif term_output_obj.get("type") == "exit_code":
                            full_terminal_log.append(term_output_obj.get("message", f"Exited with code {term_output_obj.get('code')}"))
                            yield json.dumps({"type": "desktop_content_stream", "stream_type": "exit_code", "content": term_output_obj.get("message", "") , "exit_code": term_output_obj.get("code")}) + "\n"
                        elif term_output_obj.get("type") == "error": # Error from within run_shell_command itself
                            full_terminal_log.append(f"EXECUTION ERROR: {term_output_obj.get('message')}")
                            yield json.dumps({"type": "desktop_content_stream", "stream_type": "execution_error", "content": term_output_obj.get("message")}) + "\n"

                    yield json.dumps({"type": "desktop_content_stream_end"}) + "\n"
                    # self.chat_history_for_llm.append({"role": "assistant", "content": f"Terminal command '{command_to_run}' executed. Output:\n```\n{'\n'.join(full_terminal_log)}\n```"})

                except Exception as e:
                    logger.error(f"Error during terminal command '{command_to_run}' execution: {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"An unexpected error occurred running command '{command_to_run}': {str(e)}"}) + "\n"
                    # Optionally add to LLM history about the failure
                    # self.chat_history_for_llm.append({"role": "assistant", "content": f"Failed to execute terminal command '{command_to_run}': {str(e)}"})


        elif action_type == "terminal_command_background":
            command_to_run = parameters.get('command')
            if not command_to_run:
                yield json.dumps({"type": "error", "content": "LLM chose 'terminal_command_background' but provided no command."}) + "\n"
            else:
                try:
                    status_message = run_background_command(command_to_run)
                    yield json.dumps({"type": "message", "content": status_message}) + "\n"
                except Exception as e:
                    logger.error(f"Error during background command '{command_to_run}': {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"Failed to start background command '{command_to_run}': {str(e)}"}) + "\n"


        elif action_type == "file_write":
            filename = parameters.get('filename')
            content = parameters.get('content')
            if not filename or content is None: # Content being an empty string is valid
                yield json.dumps({"type": "error", "content": "LLM chose 'file_write' but missing filename or content."}) + "\n"
            else:
                try:
                    success, message = write_cua_file(filename, content)
                    yield json.dumps({"type": "message", "content": message}) + "\n"
                    if success:
                        file_content, read_message = read_cua_file(filename)
                        if file_content is not None:
                            yield json.dumps({"type": "clear_desktop"}) + "\n"
                            yield json.dumps({"type": "desktop_mode_switch", "mode": "file_editor"}) + "\n"
                            language = filename.split('.')[-1] if '.' in filename else 'plaintext'
                            language = ''.join(filter(str.isalnum, language))
                            if not language: language = 'plaintext'
                            yield json.dumps({
                                "type": "desktop_content_set", "filename": filename,
                                "content": file_content, "language": language
                            }) + "\n"
                        else:
                            yield json.dumps({"type": "message", "content": read_message}) + "\n"
                except Exception as e:
                    logger.error(f"Error during file_write operation for '{filename}': {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"An unexpected error occurred writing file '{filename}': {str(e)}"}) + "\n"


        elif action_type == "vision_query":
            try:
                # Ensure browser is available for vision queries
                if not browser_manager.get_current_page(): # A simple check; launch_browser might be better
                    await browser_manager.launch_browser() # Attempt to launch if not already
                    if not browser_manager.get_current_page(): # Check again
                        yield json.dumps({"type": "error", "content": "Browser not available for vision query."}) + "\n"
                        return # Early exit for this action if browser fails

                page_text = await browser_manager.get_page_content_for_llm()
                if page_text.startswith("Error:"): # Check if get_page_content_for_llm itself returned an error string
                     yield json.dumps({"type": "error", "content": f"Could not get page content for vision query: {page_text}"}) + "\n"
                     return

                vision_prompt = parameters.get("query", user_message)
                yield json.dumps({"type": "message", "content": f"Asking vision model: \"{vision_prompt}\" based on current page..."}) + "\n"
                analysis = await get_mistral_vision_analysis(page_text, vision_prompt)
                formatted_analysis_message = f"Vision: {analysis}"
                yield json.dumps({"type": "message", "content": formatted_analysis_message}) + "\n"
                self.chat_history_for_llm.append({"role": "assistant", "content": formatted_analysis_message})
            except ConnectionError as e: # From launch_browser if it's called and fails
                logger.error(f"Orchestrator: Browser connection error during vision_query: {e}", exc_info=True)
                yield json.dumps({"type": "error", "content": f"Browser connection error for vision query: {str(e)}"}) + "\n"
            except Exception as e:
                logger.error(f"Orchestrator: Error during vision_query: {e}", exc_info=True)
                yield json.dumps({"type": "error", "content": f"An unexpected error occurred during vision query: {str(e)}"}) + "\n"


        elif action_type == "browser_go_to":
            url_to_go = parameters.get("url")
            if not url_to_go:
                yield json.dumps({"type": "error", "content": "LLM chose 'browser_go_to' but provided no URL."}) + "\n"
            else:
                try:
                    # Ensure browser is launched before attempting to navigate
                    await browser_manager.launch_browser()
                    if not browser_manager.get_current_page():
                        yield json.dumps({"type": "error", "content": "Browser could not be started for navigation."}) + "\n"
                        return

                    success, message = await browser_manager.go_to_url(url_to_go)
                    yield json.dumps({"type": "message", "content": message}) + "\n"
                    if success:
                        async for item in self._yield_browser_screenshot(browser_manager): yield item
                except ConnectionError as e: # Specifically if launch_browser fails within go_to_url
                    logger.error(f"Orchestrator: Browser connection error in browser_go_to: {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"Browser connection error: {str(e)}"}) + "\n"
                except Exception as e:
                    logger.error(f"Orchestrator: Error in browser_go_to: {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"Error during browser navigation to '{url_to_go}': {str(e)}"}) + "\n"

        elif action_type == "browser_new_tab":
            url_to_open = parameters.get("url", "about:blank")
            try:
                await browser_manager.launch_browser() # Ensure browser is running
                if not browser_manager.browser or not browser_manager.browser.isConnected(): # Stricter check
                     yield json.dumps({"type": "error", "content": "Browser not available or disconnected."}) + "\n"
                     return

                await browser_manager.new_tab(url=url_to_open)
                yield json.dumps({"type": "message", "content": f"Opened new tab ({browser_manager.current_page_index}). Navigated to: {url_to_open}"}) + "\n"
                async for item in self._yield_browser_screenshot(browser_manager): yield item
            except ConnectionError as e:
                logger.error(f"Orchestrator: Browser connection error in browser_new_tab: {e}", exc_info=True)
                yield json.dumps({"type": "error", "content": f"Browser connection error: {str(e)}"}) + "\n"
            except Exception as e:
                logger.error(f"Orchestrator: Error in browser_new_tab: {e}", exc_info=True)
                yield json.dumps({"type": "error", "content": f"Error opening new tab: {str(e)}"}) + "\n"

        elif action_type == "browser_switch_tab":
            tab_index = parameters.get("index")
            if tab_index is None or not isinstance(tab_index, int): # Check type
                yield json.dumps({"type": "error", "content": "LLM chose 'browser_switch_tab' but provided an invalid/missing tab index."}) + "\n"
            else:
                try:
                    await browser_manager.launch_browser() # Ensure browser is running
                    if not browser_manager.browser or not browser_manager.browser.isConnected():
                         yield json.dumps({"type": "error", "content": "Browser not available or disconnected."}) + "\n"
                         return

                    success, message = await browser_manager.switch_tab(tab_index)
                    yield json.dumps({"type": "message", "content": message}) + "\n"
                    if success:
                        async for item in self._yield_browser_screenshot(browser_manager): yield item
                except ConnectionError as e: # From launch_browser
                    logger.error(f"Orchestrator: Browser connection error in browser_switch_tab: {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"Browser connection error: {str(e)}"}) + "\n"
                except Exception as e: # Other errors from switch_tab
                    logger.error(f"Orchestrator: Error in browser_switch_tab: {e}", exc_info=True)
                    yield json.dumps({"type": "error", "content": f"Error switching tab: {str(e)}"}) + "\n"

        elif action_type == "error":
            error_content = parameters.get('content', "LLM returned an unspecified error.")
            logger.info(f"Orchestrator handling LLM-designated error: {error_content}") # Log it as info as it's an LLM decision
            yield json.dumps({"type": "error", "content": error_content}) + "\n"

        else:
            unknown_action_message = f"Orchestrator: Received unknown or unhandled action type '{action_type}' from LLM. Parameters: {json.dumps(parameters)}"
            logger.warning(unknown_action_message)
            yield json.dumps({"type": "error", "content": unknown_action_message}) + "\n"
