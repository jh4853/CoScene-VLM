from pipeline import Pipeline

pipe = Pipeline()
prompt = "Add a red cube next to a blue sphere"
score, hist = pipe.run(prompt)

print("Final score:", score)
print("History:", hist)
