from llama_cpp import Llama
import os
from typing_extensions import TypedDict, Literal
from typing import List, Optional

Role = Literal["system", "user", "assistant"]


class Message(TypedDict):
    role: Role
    content: str


B_INST, E_INST = "[INST]", "[/INST]"
B_SYS, E_SYS = "<<SYS>>\n", "\n<</SYS>>\n\n"
DEFAULT_SYSTEM_PROMPT = """"""

def make_chat_prompt(llm, user_input: str) -> List[int]:
    # Format user input as the prompt
    dialog_tokens = llm.tokenize(
        bytes(f"{B_INST} {user_input.strip()} {E_INST}", "utf-8"),
        add_bos=True,
    )

    return dialog_tokens



