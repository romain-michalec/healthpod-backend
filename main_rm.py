import os
import warnings
from io import BytesIO
from pprint import pp
from textwrap import dedent
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from PIL import Image
from pydantic import BaseModel, Field

import data

# Silence spurious Pydantic UserWarning  # TODO: Clarify this issue
# See: https://github.com/BerriAI/litellm/issues/11759
warnings.filterwarnings(
    "ignore", message="Pydantic serializer warnings.*", category=UserWarning
)


model = init_chat_model("openai:gpt-4o-mini")  # set temperature?
"""Language model (must support structured output)."""


general_system_prompt = SystemMessage(data.system_prompt)
"""System prompt for the whole conversational graph."""


class State(MessagesState):
    """Overall state for the conversation graph.

    * The conversation as a list of message objects.
    * The user's lifestyle habits.
    * The medical device readings.
    """

    smoking: str
    drinking: str
    exercising: str
    readings: dict


class ConditionalState(State):
    """State for nodes followed by conditional edges.

    Same state as above, with the addition of a boolean to allow routing
    by the conditional edges.

    The flag is True if the patient is ready to proceed, data has been
    received from a sensor, etc (indicating success), and False
    otherwise (indicating failure).
    """

    flag: bool


def idle(state: State) -> State:
    """Node function for the idle node."""
    # Tell user how to start chat
    ai = AIMessage(data.idle)
    ai.pretty_print()
    conversation: list[AnyMessage] = [ai]

    # Wait for user to start chat
    user_reply = ""
    while all([greeting not in user_reply.lower() for greeting in ["hello", "hi"]]):
        user_reply = input("\n> ")

    # User is starting chat
    user = HumanMessage(user_reply)
    user.pretty_print()
    conversation.append(user)

    return {"messages": conversation}  # type: ignore[return-value]


def is_user_ready(state: State, ai_msg: str) -> ConditionalState:
    """Node function for the nodes that ask if the user is ready."""

    # Enforce structured output
    class OutputSchema(BaseModel):
        """Output schema for the language model.

        A reply to the user along with a shorthand description of the
        user's answer to the "Are you ready?" question.
        """

        ai_reply: str = Field(..., description="The reply to the user")
        user_reply: str = Field(
            ...,
            description=f"One of {", ".join(
                data.ready["in general"]["valid options"]
            )}",
        )

    structured_model = model.with_structured_output(OutputSchema, method="json_schema")

    # System prompt for the "Are you ready?" question
    specific_system_prompt = SystemMessage(data.ready["in general"]["context"])

    # Ask user if they are ready to proceed
    ai = AIMessage(ai_msg)
    ai.pretty_print()
    conversation: list[AnyMessage] = [ai]

    # Get user reply
    user_reply = ""
    valid_options = data.ready["in general"]["valid options"]
    while user_reply not in valid_options:  # TODO: This loop might only run once
        user = HumanMessage(input("\n> "))
        user.pretty_print()
        conversation.append(user)

        response = structured_model.invoke(
            [general_system_prompt, specific_system_prompt] + conversation
        )

        ai = AIMessage(response.ai_reply)  # type: ignore[attr-defined]
        ai.pretty_print()
        conversation.append(ai)

        user_reply = response.user_reply  # type: ignore[attr-defined]
        print(f"\n{user_reply=}")

    return {
        "messages": conversation,
        "flag": True if user_reply == "READY" else False,
    }  # type: ignore[return-value]


def welcome(state: State) -> ConditionalState:
    """Node function for the welcome node."""
    return is_user_ready(state, ai_msg=data.welcome)


def welcome_out(state: ConditionalState) -> Literal["idle", "smoking"]:
    """Conditional edge function to route after the welcome node."""
    return "smoking" if state["flag"] else "idle"


def lifestyle(
    state: State, question: Literal["smoking", "drinking", "exercising"]
) -> State:
    """Handle a question from the lifestyle questionnaire."""

    # Enforce structured output
    class OutputSchema(BaseModel):
        """Output schema for the language model.

        A reply to the user along with a shorthand description of the
        user's answer to the lifestyle question.
        """

        ai_reply: str = Field(..., description="The reply to the user")
        user_reply: str = Field(
            ...,
            description=f"One of {", ".join(
                data.lifestyle[question]["invalid options"]
                + data.lifestyle[question]["valid options"]
            )}",
        )

    structured_model = model.with_structured_output(OutputSchema, method="json_schema")

    # System prompt for the lifestyle question
    specific_system_prompt = SystemMessage(data.lifestyle[question]["context"])

    # Ask lifestyle question
    ai = AIMessage(data.lifestyle[question]["question"])
    ai.pretty_print()
    conversation: list[AnyMessage] = [ai]

    # Get user reply
    user_reply = ""
    valid_options = data.lifestyle[question]["valid options"]
    while user_reply not in valid_options:
        user = HumanMessage(input("\n> "))
        user.pretty_print()
        conversation.append(user)

        response = structured_model.invoke(
            [general_system_prompt, specific_system_prompt] + conversation
        )

        ai = AIMessage(response.ai_reply)  # type: ignore[attr-defined]
        ai.pretty_print()
        conversation.append(ai)

        user_reply = response.user_reply  # type: ignore[attr-defined]
        print(f"\n{user_reply=}")

    return {"messages": conversation, question: user_reply}  # type: ignore[return-value]


def smoking(state: State) -> State:
    """Node function for the node about smoking."""
    return lifestyle(state, question="smoking")


def drinking(state: State) -> State:
    """Node function for the node about drinking."""
    return lifestyle(state, question="drinking")


def exercising(state: State) -> State:
    """Node function for the node about exercising."""
    return lifestyle(state, question="exercising")


def first_recap(state: State) -> ConditionalState:
    """Node function for the first recap node."""
    recap = dedent(
        f"""\
        Smoking: {state["smoking"].lower()}
        Drinking: {state["drinking"].lower()}
        Exercising: {state["exercising"].lower()}
        """
    ).strip()
    return is_user_ready(state, ai_msg="\n\n".join([data.first_recap, recap]))


def first_recap_out(state: ConditionalState) -> Literal["idle", "tmp"]:
    """Conditional edge function to route after the first recap node."""
    return "tmp" if state["flag"] else "idle"


def tmp(state: State) -> State:
    """Tmp."""
    return {}  # type: ignore[return-value]


def main():
    """Conversation graph for the self-screening health station."""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):  # TODO: use an exception instead?
        print("Error: OPENAI_API_KEY environment variable not set!")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Define graph
    graph = StateGraph(State)
    graph.add_sequence([idle, welcome])
    graph.add_sequence([smoking, drinking, exercising, first_recap])
    graph.add_node(tmp)
    graph.add_edge(START, "idle")
    graph.add_conditional_edges("welcome", welcome_out)
    graph.add_conditional_edges("first_recap", first_recap_out)
    graph.add_edge("tmp", END)
    graph = graph.compile()

    # Display graph
    img = graph.get_graph().draw_mermaid_png()
    img = Image.open(BytesIO(img))
    img.show()

    # Run graph with empty initial state (no input message)
    result = graph.invoke({"messages": []})  # type: ignore[arg-type]

    # Debug info: final state and all the messages it contains
    # print("=" * 33, "FINAL STATE", "=" * 34)
    # pp(result)
    # print("=" * 27, "MESSAGES IN FINAL STATE", "=" * 28)
    # for message in result["messages"]:
    #    message.pretty_print()


if __name__ == "__main__":
    main()
