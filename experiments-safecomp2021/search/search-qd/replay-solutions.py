""""Processing script for qdpy pickled archive"""

import funcy
import pathlib
import pickle

from runner import RunnerFitnessWrapper

if __name__ == "__main__":
    # Load archive contents
    archive_path = pathlib.Path("final.p")
    with archive_path.open("rb") as archive_file:
        archive = pickle.load(archive_file)
    # Replay all solutions
    solutions = archive["container"].solutions
    for features in solutions:
        if len(solutions[features]) > 0:
            individual = funcy.first(solutions[features])
            run_output = pathlib.Path("solutions") / ".".join(map(str, features))
            # Run the solution
            w = RunnerFitnessWrapper("../../build_preview/", run_output, "zadeh")
            score = w(individual)
            # Register score
            with (run_output / "score.txt").open("w") as score_file:
                score_file.write(str(score))
