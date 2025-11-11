import llm
import time
import toolbag
import pprint
import dataclasses

SYSTEM_PROMPT = "You are a helpful, expert. You have a doctorate in philosophy and software engineering. You develop programming solutions that balance ease of maintenance and robustness. You favor clarity over performance outside of performance critical sections. You use short well-named functions. Avoid large class hierachies. Avoid unnecessary comments in favor of clear self-explained code. Always begin by creating the list of tasks required and then complete each step in order."

def before_tool_call(tool, tool_call: llm.ToolCall):
    print(f"About to call tool {tool.name if tool else 'None'} with arguments {tool_call.arguments}")

def after_tool_call(tool: llm.Tool, tool_call: llm.ToolCall, tool_result: llm.ToolResult):
    print(f"Tool {tool.name} called with arguments {tool_call.arguments} returned {tool_result.output}")


def main():
    m = llm.get_model("qwen3:latest")
    r = m.chain("Write a python function that fetches the html for a given url using the requests library. Include a concise clear docstring. Save it in an appropriately named file.", system=SYSTEM_PROMPT, options={'temperature': 0.25, 'num_ctx':16384},
    tools=toolbag.bag.unpack(),
    after_call=after_tool_call,
    before_call=before_tool_call)
    start = time.time()
    for response in r.responses():
        print(pprint.pprint(dataclasses.asdict(response.prompt)))
        for chunk in response:
            print(chunk, end="", flush=True)
        print()
        print(response.usage())
        print()
    duration = time.time() - start
    human_duration = f"{duration:.0f}s"
    if duration > 60:
        human_duration = f"{duration / 60:.0f}m"
    print()
    print(f"Response required {human_duration}")


if __name__ == "__main__":
    main()
