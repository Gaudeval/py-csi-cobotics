import kinpy as kp
from flask import Flask, request, jsonify
from typing import Optional, Dict

from werkzeug.exceptions import BadRequest

app = Flask(__name__)

arm: Optional[kp.chain.SerialChain] = None


@app.route('/ik', methods=['POST'])
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
    return jsonify({
        "joints": list(arm.get_joint_parameter_names()),
        "targets": list(ik),
    })


if __name__ == '__main__':
    # TODO Add port as parameter
    # TODO Add debug as parameter
    # TODO Add URDF, root and end link, as parameters
    arm = kp.build_serial_chain_from_urdf(
        open("urdfs/UR10/robot_description.urdf").read(),
        root_link_name="base_link",
        end_link_name="ee_link",
    )
    app.run(host='127.0.0.1', port=21000, debug=True)