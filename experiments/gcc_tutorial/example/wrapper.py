from dataclasses import dataclass
from pathlib import Path
from shutil import copy
from subprocess import run, CalledProcessError

from csi import Experiment, ConfigurationManager
from configuration import Configuration


@dataclass
class GccRunnerConfiguration:
    build_root: Path
    run_configuration: Configuration


class GccRunner(Experiment):
    configuration: GccRunnerConfiguration

    def execute(self) -> None:
        assert self.configuration.build_root.is_absolute()
        # Configure build input/output paths
        assets_path = (
            self.configuration.build_root
            / "CSI Digital Twin_Data"
            / "StreamingAssets"
            / "CSI"
        )
        configuration_path = assets_path / "gcc-configuration.json"
        messages_path = assets_path / "gcc-messages.db"
        executable_path = self.configuration.build_root / "CSI Digital Twin.exe"
        # Prepare build files
        ConfigurationManager(Configuration).save(
            self.configuration.run_configuration, configuration_path
        )
        messages_path.unlink(missing_ok=True)
        # Run build
        try:
            run(executable_path, check=True)
        except CalledProcessError as e:
            # Process exception if required
            raise e
        # Save message log
        copy(messages_path, Path("./messages.db"))
