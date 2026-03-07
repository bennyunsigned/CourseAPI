"""
  pip i bytez
"""

from bytez import Bytez

key = "3cf50d1e472150700f30c67e30421f15"
sdk = Bytez(key)

# choose sora-2
model = sdk.model("openai/sora-2")

# send input to model
results = model.run("Hulk doing pottery and crying.")

print({ "error": results.error, "output": results.output })