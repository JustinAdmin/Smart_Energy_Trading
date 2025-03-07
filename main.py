# Must use "spade run" command before running code

from agents.behavioralSegmentation import BehavioralSegmentationAgent
from agents.demandResponse import DemandResponseAgent
from agents.facilitating import FacilitatingAgent
from agents.negotiation import NegotiationAgent
from agents.prediction import PredictionAgent

from agents.gui import GUIAgent

from test_agents.grid import Grid
from test_agents.house import House
import asyncio

import streamlit as st


async def main():
    # Create agents
    gui = GUIAgent("gui@localhost", "password")
    house = House("house@localhost", "password")
    grid = Grid("grid@localhost", "password")
    behavioral_segmentation_agent = BehavioralSegmentationAgent("behavioralsegmentation@localhost", "password")
    demand_response_agent = DemandResponseAgent("demandResponse@localhost", "password")
    negotiation_agent = NegotiationAgent("negotiation@localhost", "password")
    prediction_agent = PredictionAgent("prediction@localhost", "password")
    facilitating_agent = FacilitatingAgent("facilitating@localhost", "password")
    

    # Start agents
    await gui.start()
    await house.start()
    await grid.start()
    await behavioral_segmentation_agent.start()
    await demand_response_agent.start()
    await negotiation_agent.start()
    await prediction_agent.start()
    await facilitating_agent.start()

    st.title("Multi-Agent System: Facilitating Agent Messages")
    st.write("Messages will update as the Facilitating Agent receives them.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the messages live
    st.write("Latest Messages:")
    for message in st.session_state.messages:
        st.write(message)


# Run the multi-agent system
if __name__ == "__main__":
    asyncio.run(main())