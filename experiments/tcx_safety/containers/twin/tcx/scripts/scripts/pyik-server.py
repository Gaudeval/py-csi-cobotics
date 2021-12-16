import pathlib

import click
import kinpy as kp
from flask import Flask, request, jsonify
from typing import Optional, Dict

from werkzeug.exceptions import BadRequest

app = Flask(__name__)

arm: Optional[kp.chain.SerialChain] = None


@app.route("/ik", methods=["POST"])
def compute_ik():
    try:
        query: Dict = request.json
        print("REQUEST:", query)
    except BadRequest as e:
        print(e)
        raise e
    # Collect and convert IK request parameters
    target_pos = query.get("position", None)
    target_rot = query.get("rotation", None)
    state = query.get("state", None)
    #
    ik = arm.inverse_kinematics(kp.Transform(target_rot, target_pos), state)
    return jsonify(
        {
            "joints": list(arm.get_joint_parameter_names()),
            "targets": list(ik),
        }
    )


@click.command()
@click.argument("urdf", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option("--port", "-p", default=21000, help="IK server query port")
@click.option("--debug/--no-debug", default=False, help="Verbose server output")
@click.option(
    "--root-link", "-r", default="base_link", help="Selected arm base link name"
)
@click.option("--end-link", "-e", default="ee_link", help="Selected arm end link name")
def pyik_start_server(urdf, port, debug, root_link, end_link):
    """Start IK solver for a robot arm described by URDF

    URDF Description of the selected arm.
    """
    global arm
    with urdf.open() as urdf_file:
        arm = kp.build_serial_chain_from_urdf(
            urdf_file.read(),
            root_link_name="base_link",
            end_link_name="ee_link",
        )
    app.run(host="127.0.0.1", port=port, debug=debug)


if __name__ == "__main__":
    # TODO Add URDF, root and end link, as parameters
    pyik_start_server()
