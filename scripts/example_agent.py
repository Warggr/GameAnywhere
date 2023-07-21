import random

class Agent:
    def on_message(self, message):
        print('Python: Received message:', message)
    def get_2D_choice(self, dimensions):
        print(f"get2DChoice called with {dimensions=}")
        return (random.randint(0, dimensions[0]), random.randint(0, dimensions[1]))
