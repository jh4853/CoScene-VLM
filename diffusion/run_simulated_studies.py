from pipeline import Pipeline

pipe = Pipeline()

prompt = "Add a red cube next to a blue sphere and a green cylinder behind them"

ITER_SETTINGS = [1, 2, 3, 5]

for iters in ITER_SETTINGS:
    out_dir = f"sim_iters_{iters}"
    score, history = pipe.run(prompt, iters=iters, out_dir=out_dir)
    print(f"Iters={iters} | Final score={score} | History={history}")
