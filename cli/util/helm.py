#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

from util.system import execute_system_command
from util.k8s.k8s_info import delete_namespace
from util.logger import initialize_logger

log = initialize_logger(__name__)


def delete_user(username: str) -> bool:
    """
    Removes a user with all his/her objects

    :param username: name of a user to be deleted
    :return: True if a user has been deleted without any problems, False otherwise
    """
    try:
        delete_namespace(username)

        delete_helm_release(username)
    except Exception:
        log.exception("Problems during removal of a user {}".format(username))
        return False

    return True


def delete_helm_release(release_name: str) -> bool:
    """
    Deletes release of a helm's chart.

    :param release_name: name of a release to be removed
    In case of any problems it throws an exception
    """
    delete_release_command = ["helm", "delete", "--purge", release_name]

    output, err_code = execute_system_command(delete_release_command)

    if err_code or f"release \"{release_name}\" deleted" not in output:
        log.error(output)
        raise RuntimeError("Error during removal of helm release {}.".format(release_name))

    return True
