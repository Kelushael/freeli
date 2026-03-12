import os
import sys
import json
import readline  # optional for nicer input
from llm_client import LlamaClient
from context_manager import ContextManager
from tools import TOOL_REGISTRY, get_tool
import tools.self as self_tools

CONFIG_PATH = "config.json"

def load_config(path):
    if not os.path.exists(path):
        return {"agent": {"name": "Sovereign"}, "tools": {}, "system_instructions": "", "execution_rules": {}}
    with open(path, 'r') as f:
        return json.load(f)

def build_system_prompt(config):
    instr = config.get('system_instructions', '')
    tools_desc = []
    for cat, tl in config.get('tools', {}).items():
        for t in tl:
            tools_desc.append(f"- {t['name']}: {t['description']}")
    
    rules = config.get('execution_rules', {})
    rules_str = f"Autonomous tool use: {rules.get('autonomous_tool_use')}\nManual override: {rules.get('user_manual_override')}\nSelf‑modification allowed: {rules.get('allow_self_modification')}"
    
    prompt = f"""{instr}

You have the following tools available:
{chr(10).join(tools_desc)}

Execution rules:
{rules_str}

Always respond in a JSON format with two fields: "thought" (your reasoning) and "action" (a tool call or final answer).
"""
    return prompt

def execute_tool(tool_name, params):
    tool_func = get_tool(tool_name)
    if tool_func:
        try:
            return tool_func(**params)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"
    else:
        return f"Error: Tool '{tool_name}' not found."

def main():
    config = load_config(CONFIG_PATH)
    # Set config path for self tools
    self_tools.set_config_path(CONFIG_PATH)

    # Initialize LLM (adjust model path as needed)
    llm = LlamaClient()
    ctx = ContextManager(max_tokens=3500)

    # Initial System Prompt
    ctx.add_message("system", build_system_prompt(config))

    print(f"\n🚀 {config['agent'].get('name', 'Sovereign-CLI')} v{config['agent'].get('version', '1.0')} – ready")
    print("Type your request, or /exit to quit.\n")

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() == "/exit":
            break

        ctx.add_message("user", user_input)

        # Get LLM response (grammar enforced)
        messages_for_llm = ctx.get_messages_for_llm()
        response_json = llm.generate(messages_for_llm)  

        # Parse Response (it's already a dict thanks to grammar)
        thought = response_json.get("thought", "")
        if thought:
            print(f"\n🤔 {thought}\n")

        action = response_json.get("action")
        
        if isinstance(action, dict):
            # Tool Call
            tool_name = action.get("tool")
            params = action.get("params", {})
            print(f"🛠️  Using tool: {tool_name} with params {params}")
            
            result = execute_tool(tool_name, params)
            print(f"📦 Result: {result}")
            
            # Append tool result to context
            ctx.add_message("assistant", json.dumps(response_json))
            ctx.add_message("system", f"Tool result for {tool_name}: {result}")
            
        elif action == "final":
            # Final Answer
            content = response_json.get('content', '')
            print(f"💬 {content}")
            ctx.add_message("assistant", json.dumps(response_json))
            
        else:
            print(f"❓ Unexpected action format: {action}")

    print("\n👋 Session ended.")

if __name__ == "__main__":
    main()
