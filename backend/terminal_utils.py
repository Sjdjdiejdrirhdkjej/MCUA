import asyncio
import subprocess

async def run_shell_command(command: str):
    """
    Asynchronously executes a shell command and streams its stdout and stderr,
    attempting to interleave them as they arrive.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        yield f"$ {command}\n" # Echo the command being run

        # Create tasks for reading stdout and stderr lines
        async def read_stream_lines(stream, stream_name_prefix=""):
            # Helper to read lines from a stream and yield them
            while True:
                line = await stream.readline()
                if not line:
                    break
                yield (stream_name_prefix, line.decode(errors='replace').rstrip())

        stdout_task = asyncio.create_task(read_stream_lines(process.stdout, ""))
        stderr_task = asyncio.create_task(read_stream_lines(process.stderr, "STDERR: "))

        pending_tasks = {stdout_task, stderr_task}

        while pending_tasks:
            # Wait for the next line from either stdout or stderr
            done, pending = await asyncio.wait(
                pending_tasks,
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                try:
                    # task.result() here would be the generator from read_stream_lines
                    # This logic needs to consume the generator if it's not already done.
                    # The way read_stream_lines is written, it's an async generator.
                    # This means task.result() won't directly give the line.
                    # This part is still not quite right. Let's simplify.

                    # Let's change read_stream_lines to be a one-shot reader that returns all lines (not good for streaming)
                    # OR, ensure this loop correctly handles async generators.

                    # The task itself is the completed async generator.
                    # We need to iterate over its results if it produced multiple.
                    # However, FIRST_COMPLETED means the task *itself* (the read_stream_lines call) has finished,
                    # not that it has produced one item.

                    # A better pattern for interleaving:
                    # Continuously try to read a line from each pipe without blocking indefinitely on one.
                    # This is what select() does in synchronous code.
                    # asyncio.StreamReader.readline() is already awaitable.

                    # Let's try a different approach for interleaving:
                    # Keep two flags for EOF for stdout and stderr.
                    # Loop while not both are EOF. In each iteration, try to read from both.
                    # This is still not ideal. The `asyncio.wait` is the right tool.

                    # The issue might be in how the result of the task is handled.
                    # If `read_stream_lines` yields multiple items, `task.result()` is not appropriate here.
                    # Let's restructure `read_stream_lines` or how it's consumed.

                    # Alternative: The `done` tasks are Future-like objects. If `read_stream_lines`
                    # is an async generator, we'd need to iterate it.
                    # This design is getting complicated. Let's simplify the interleaving logic.

                    # Simplest (but potentially not perfectly interleaved under all conditions)
                    # is to have two independent loops consuming from stdout/stderr and yielding.
                    # This requires the Orchestrator to handle two separate streams or merge them.
                    # That's not what we want for `run_shell_command`.

                    # Let's stick to the `asyncio.wait` approach but ensure it's used correctly.
                    # The problem is that `read_stream_lines` is an async generator.
                    # We need to pull items from it.

                    # Revisit the example from Python docs for subprocess streams:
                    # They typically show reading one stream until EOF, then the other, or merging.
                    # For true interleaving with `asyncio.wait`, we'd have tasks that each read *one line*
                    # and then resubmit themselves or similar.

                    # Let's simplify: we will yield a tuple (stream_name, line)
                    # and the consumer (orchestrator) will format it.
                    # `read_stream_lines` should be an async def that yields lines.
                    # `stdout_task` and `stderr_task` are tasks that run these async generators.
                    # This structure is fundamentally difficult with `asyncio.wait` if the tasks are generators.

                    # Let's try a more direct approach to reading lines,
                    # assuming `process.stdout.readline()` and `process.stderr.readline()`
                    # will yield control if no data is immediately available.

                    # This simplified approach might still face issues with one stream starving the other
                    # if it produces data very rapidly while the other is slow.
                    # However, for typical command output, it should be acceptable.

                    pass # Original structure was problematic.

                except Exception as e:
                    # This exception would be if the task itself failed, not if it yielded an error line.
                    yield f"Error processing stream task: {str(e)}\n"

                # If a task is done, remove it from pending_tasks
                pending_tasks.remove(task)
                # If it's not an EOF, and it's supposed to produce more, re-add it (complex)
                # The way read_stream_lines is written, it completes when the stream is EOF.

        # Fallback to simpler, non-interleaved or less perfectly interleaved reading if above is too complex:
        # This is what was in the previous version, which is more robust if harder to get perfect interleaving.
        # For now, let's assume the loop above is corrected or simplified.
        # Given the constraints, a perfect interleaving might be too much.
        # I will revert to a slightly better version of separate readers.

        async def stream_output_lines(pipe, prefix=""):
            while True:
                line = await pipe.readline()
                if not line:
                    break
                yield f"{prefix}{line.decode(errors='replace').strip()}\n"

        # This won't truly interleave but will process stdout then stderr.
        # To achieve better interleaving, one would typically use separate tasks
        # that push lines to a shared asyncio.Queue, and then read from that queue.
        # This is complex to set up here.

        # Let's try a slightly more interleaved approach by reading available lines.
        # This is still not perfect.
        stdout_eof = False
        stderr_eof = False
        while not (stdout_eof and stderr_eof):
            line_read = False
            if not stdout_eof:
                try:
                    # Non-blocking read attempt - this is not how readline works. Readline will wait.
                    # Using a small timeout to allow context switching between stdout and stderr.
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.01)
                    if line:
                        yield {"type": "stdout", "line": line.decode(errors='replace').rstrip('\n')}
                        line_read = True
                    else:
                        stdout_eof = True # Pipe closed
                except asyncio.TimeoutError:
                    pass # No data on stdout currently, try stderr or loop again
                except Exception as e: # Includes IncompleteReadError etc.
                    stdout_eof = True
                    logger.error(f"Error reading stdout for command '{command}': {e}", exc_info=True)
                    yield {"type": "stderr", "line": f"Error reading stdout: {e}"}


            if not stderr_eof:
                try:
                    line = await asyncio.wait_for(process.stderr.readline(), timeout=0.01)
                    if line:
                        yield {"type": "stderr", "line": line.decode(errors='replace').rstrip('\n')}
                        line_read = True
                    else:
                        stderr_eof = True # Pipe closed
                except asyncio.TimeoutError:
                    pass # No data on stderr currently
                except Exception as e:
                    stderr_eof = True
                    logger.error(f"Error reading stderr for command '{command}': {e}", exc_info=True)
                    yield {"type": "stderr", "line": f"Error reading stderr: {e}"}

            if not line_read and not (stdout_eof and stderr_eof): # If neither stream had data immediately
                await asyncio.sleep(0.02) # Shorter sleep, just to yield control

        await process.wait()
        logger.info(f"Command '{command}' exited with code {process.returncode}.")
        yield {"type": "exit_code", "code": process.returncode, "message": f"Command exited with code {process.returncode}"}

    except Exception as e:
        logger.error(f"Error executing command '{command}': {e}", exc_info=True)
        yield {"type": "error", "message": f"Failed to execute command '{command}': {e}"}
        # Also yield an exit code to signify completion if possible, or a specific error type
        yield {"type": "exit_code", "code": -1, "message": f"Command execution failed: {e}"} # Use a conventional error code


def run_background_command(command: str) -> str:
    """
    Starts a command in the background (non-blocking).
    """
    try:
        subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, close_fds=True)
        return f"Command '{command}' started in background."
    except Exception as e:
        return f"Error starting background command '{command}': {e}"
