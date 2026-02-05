"""
LangGraph POC for Human-Robot Conversation
Uses graph-based state management with LangGraph
"""

import os
import random
from multiprocessing.connection import Listener
from typing import TypedDict, Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from time import sleep

delay = 1


class ConversationState(TypedDict):
    """State object that tracks the conversation"""
    current_stage: str
    user_input: str
    robot_response: str
    readings: dict
    should_continue: bool


class HealthRobotGraph:
    """LangGraph-based state machine for sensor readings"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
        self.graph = self.build_graph()

    def get_sensor_reading(self, sensor_type):
        """Simulate sensor readings with realistic random values"""
        if sensor_type == "heart_rate":
            return random.randint(60, 100)  # bpm
        elif sensor_type == "weight":
            return round(random.uniform(50, 100), 1)  # kg
        elif sensor_type == "blood_pressure":
            systolic = random.randint(110, 140)
            diastolic = random.randint(70, 90)
            return f"{systolic}/{diastolic}"  # mmHg
        elif sensor_type == "temperature":
            return round(random.uniform(36.5, 37.5), 1)  # Celsius

    def should_proceed(self, user_input: str) -> bool:
        """Use LLM to determine if user wants to proceed"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""You are analyzing user input in a health sensor conversation.
            Determine if the user is indicating they want to proceed to the next step.
            They might say things like: 'yes', 'ready', 'let's go', 'ok', 'done', 'next', 'sure', 'continue', etc.

            Respond with ONLY 'YES' if they want to proceed, or 'NO' if they're asking a question or making conversation.
            """),
            HumanMessage(content=f"User said: {user_input}\n\nShould we proceed? (YES/NO)")
        ])

        response = self.llm.invoke(prompt.messages)
        return "YES" in response.content.upper()

    def handle_general_question(self, user_input: str, context: str) -> str:
        """Handle off-topic questions"""
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"""You are a friendly health monitoring robot assistant.
            The user asked a question that's not directly about proceeding to the next step.
            Context: {context}

            Answer their question helpfully and briefly, then gently remind them about the current task.
            Keep your response concise (2-3 sentences max).
            """),
            HumanMessage(content=user_input)
        ])

        response = self.llm.invoke(prompt.messages)
        return response.content

    # Node functions for each state
    def greeting_node(self, state: ConversationState) -> ConversationState:
        """Initial greeting node"""
        state["robot_response"] = "Hello! I'm here to help you take some health readings today. We'll measure your heart rate, weight, blood pressure, and temperature. Are you ready to begin?"
        state["current_stage"] = "greeting"
        return state

    def heart_rate_node(self, state: ConversationState) -> ConversationState:
        """Heart rate measurement node"""
        state["robot_response"] = "Great! Let's start with your heart rate. Please place your finger on the sensor."
        state["current_stage"] = "heart_rate"

        # Take reading
        print("  [Sensor is reading...]")
        sleep(delay)
        reading = self.get_sensor_reading("heart_rate")
        state["readings"]["heart_rate"] = reading
        print(f"  [Reading complete: {reading}]")
        print()

        return state

    def weight_node(self, state: ConversationState) -> ConversationState:
        """Weight measurement node"""
        state["robot_response"] = "Excellent! Next, let's measure your weight. Please step onto the scale."
        state["current_stage"] = "weight"

        # Take reading
        print("  [Sensor is reading...]")
        sleep(delay)
        reading = self.get_sensor_reading("weight")
        state["readings"]["weight"] = reading
        print(f"  [Reading complete: {reading}]")
        print()

        return state

    def blood_pressure_node(self, state: ConversationState) -> ConversationState:
        """Blood pressure measurement node"""
        state["robot_response"] = "Good! Now let's check your blood pressure. Please sit comfortably and extend your arm."
        state["current_stage"] = "blood_pressure"

        # Take reading
        print("  [Sensor is reading...]")
        sleep(delay)
        reading = self.get_sensor_reading("blood_pressure")
        state["readings"]["blood_pressure"] = reading
        print(f"  [Reading complete: {reading}]")
        print()

        return state

    def temperature_node(self, state: ConversationState) -> ConversationState:
        """Temperature measurement node"""
        state["robot_response"] = "Almost done! Finally, let's take your temperature. Please place the thermometer on your forehead."
        state["current_stage"] = "temperature"

        # Take reading
        print("  [Sensor is reading...]")
        sleep(delay)
        reading = self.get_sensor_reading("temperature")
        state["readings"]["temperature"] = reading
        print(f"  [Reading complete: {reading}]")
        print()

        return state

    def complete_node(self, state: ConversationState) -> ConversationState:
        """Completion node"""
        readings_text = "\n".join([f"  - {k.replace('_', ' ').title()}: {v}" for k, v in state["readings"].items()])
        state["robot_response"] = f"All done! Here are your readings:\n{readings_text}\n\nThank you for completing your health check!"
        state["current_stage"] = "complete"
        return state

    def build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("greeting", self.greeting_node)
        workflow.add_node("heart_rate", self.heart_rate_node)
        workflow.add_node("weight", self.weight_node)
        workflow.add_node("blood_pressure", self.blood_pressure_node)
        workflow.add_node("temperature", self.temperature_node)
        workflow.add_node("complete", self.complete_node)

        # Set entry point
        workflow.set_entry_point("greeting")

        # Add edges (linear flow)
        workflow.add_edge("greeting", "heart_rate")
        workflow.add_edge("heart_rate", "weight")
        workflow.add_edge("weight", "blood_pressure")
        workflow.add_edge("blood_pressure", "temperature")
        workflow.add_edge("temperature", "complete")
        workflow.add_edge("complete", END)

        return workflow.compile()

    def run(self):
        """Main conversation loop using LangGraph"""
        print("=" * 60)
        print("Health Monitoring Robot - LangGraph POC")
        print("=" * 60)
        print("(Type 'quit' or 'exit' to end the conversation)\n")

        # Initialize state
        state: ConversationState = {
            "current_stage": "greeting",
            "user_input": "",
            "robot_response": "",
            "readings": {},
            "should_continue": False
        }

        # Track which node we're at
        stages = ["greeting", "heart_rate", "weight", "blood_pressure", "temperature", "complete"]
        current_index = 0

        # Create network socket
        address = ('localhost', 6000)
        listener = Listener(address, authkey=b'secret password')
        print("Listening for connections...")
        connection = listener.accept()
        print('Connection accepted from', listener.last_accepted)

        # Run through the graph
        while current_index < len(stages):
            current_stage = stages[current_index]

            # Execute the current node
            if current_stage == "greeting":
                state = self.greeting_node(state)
            elif current_stage == "heart_rate":
                state = self.heart_rate_node(state)
            elif current_stage == "weight":
                state = self.weight_node(state)
            elif current_stage == "blood_pressure":
                state = self.blood_pressure_node(state)
            elif current_stage == "temperature":
                state = self.temperature_node(state)
            elif current_stage == "complete":
                state = self.complete_node(state)

            # Display robot's response
            print(f"Robot: {state['robot_response']}\n")

            # If complete, break
            if current_stage == "complete":
                break

            # Wait for user to be ready to proceed
            while True:
                # Text input
                # user_input = input("You: ").strip()
                # print()

                # Voice input
                print("Listening for messages...")
                user_input = connection.recv()
                print(f"Received: {user_input}")
                print()

                if user_input.lower() in ['quit', 'exit']:
                    print("Robot: Goodbye! Come back anytime to complete your readings.")
                    print("Closing connection")
                    connection.close()
                    print("Connection closed")
                    listener.close()
                    return

                if not user_input:
                    continue

                # Check if user wants to proceed
                if self.should_proceed(user_input):
                    # Move to next stage
                    current_index += 1
                    break
                else:
                    # Handle as general question
                    context = f"We're currently working on {current_stage.replace('_', ' ')} measurement."
                    response = self.handle_general_question(user_input, context)
                    print(f"Robot: {response}\n")

        print("Closing connection")
        connection.close()
        print("Connection closed")
        listener.close()

def main():
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set!")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return

    robot = HealthRobotGraph()
    robot.run()


if __name__ == "__main__":
    main()
