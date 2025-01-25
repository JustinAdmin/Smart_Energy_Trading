import spade
import tensorflow as tf
import torch
import numpy as np

class PredictionAgent(spade.agent.Agent):
    def __init__(self, jid, password, model_path):
        super().__init__(jid, password)
        self.model = self.load_prediction_model(model_path)
    
    def load_prediction_model(self, model_path):
        # Load TensorFlow or PyTorch model
        try:
            model = tf.keras.models.load_model(model_path)
        except:
            model = torch.load(model_path)
        return model
    
    async def setup(self):
        # SPADE behavior for prediction agent
        prediction_template = spade.template.Template()
        prediction_template.set_metadata("performative", "predict")
        
        self.add_behaviour(self.PredictionBehaviour(), prediction_template)
    
    class PredictionBehaviour(spade.behaviour.CyclicBehaviour):
        async def run(self):
            # Receive energy history
            msg = await self.receive(timeout=10)
            if msg:
                energy_history = np.array(msg.body)
                
                # Predict energy use, generation, and status
                prediction = self.agent.model.predict(energy_history)
                
                # Prepare response message
                response = spade.message.Message(
                    to=msg.sender,
                    body=str(prediction)
                )
                await self.send(response)