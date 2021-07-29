import pickle

from csi.experiment import Repository, Run
from wrapper.runner import SafecompControllerRunner

if __name__ == '__main__':
    x: Repository = Repository("runs")
    report = SafecompControllerRunner.merge_coverage(x)
    with open("runs.report.pkl", "wb") as report_file:
        pickle.dump(report, report_file)
