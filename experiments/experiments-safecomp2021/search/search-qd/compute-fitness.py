from tqdm import tqdm

from csi.experiment import Repository
from ..fitness import RunnerFitnessWrapper


def compute_fitness_bounds(repository_path):
    repository = Repository(repository_path)
    w = RunnerFitnessWrapper()
    best_score, best_exp = float("-inf"), None
    worst_score, worst_exp = float("inf"), None
    features = set()
    for experiment in tqdm(repository.experiments, desc="Experiment"):
        (score,), f = w.score_experiment(experiment)
        features.add(f)
        best_score = max(best_score, score)
        if best_score == score:
            best_exp = experiment
        worst_score = min(worst_score, score)
        if worst_score == score:
            worst_exp = experiment
    return (worst_score, worst_exp), (best_score, best_exp), features


if __name__ == "__main__":
    bounds = {}
    for runs in tqdm(
        [
            "../search-ran/runs",
            "./backup-5-crisp/runs",
            "./backup-4-stop in cell/runs",
            "./backup-3-no stop in cell/runs",
            "../search-ga/backup-1-minimise/runs",
            "../search-ga/backup-2-maximise/runs",
        ],
        desc="Runs",
    ):
        bounds[runs] = compute_fitness_bounds(runs)

    for r in bounds:
        (w, we), (b, be), f = bounds[r]
        print(r, w, b, len(f))
