# Must use "spade run" command before running code

from agents.behavioralSegmentation import BehavioralSegmentationAgent
from agents.demandResponse import DemandResponseAgent
from agents.facilitating import FacilitatingAgent
from agents.negotiation import NegotiationAgent
from agents.prediction import PredictionAgent
import asyncio

# This is what our main file will look like (except with all our agents)
async def main():
    # Create agents
    behavioral_segmentation_agent = BehavioralSegmentationAgent("behavioralSegmentation@localhost", "password")
    demand_response_agent = DemandResponseAgent("demandResponse@localhost", "password")
    negotiation_agent = NegotiationAgent("negotiation@localhost", "password")
    prediction_agent = PredictionAgent("prediction@localhost", "password")
    facilitating_agent = FacilitatingAgent("facilitating@localhost", "password")

    # Start agents
    await behavioral_segmentation_agent.start()
    await demand_response_agent.start()
    await negotiation_agent.start()
    await prediction_agent.start()
    await facilitating_agent.start()


# Run the multi-agent system
if __name__ == "__main__":
    asyncio.run(main())