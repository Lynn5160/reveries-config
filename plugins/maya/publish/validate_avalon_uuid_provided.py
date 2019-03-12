
import pyblish.api
from reveries.maya.utils import Identifier, get_id_status
from reveries.maya.plugins import MayaSelectInvalidInstanceAction


class SelectMissing(MayaSelectInvalidInstanceAction):

    label = "Select ID Missing"
    symptom = "missing"


class SelectDuplicated(MayaSelectInvalidInstanceAction):

    label = "Select ID Duplicated"
    symptom = "duplicated"


class ValidateAvalonUUIDProvided(pyblish.api.InstancePlugin):
    """Ensure upstream nodes have Avalon UUID
    """

    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    label = "Avalon UUID Provided"
    families = [
        "reveries.look",
        "reveries.animation",
        "reveries.pointcache",
    ]
    actions = [
        pyblish.api.Category("Select"),
        SelectMissing,
        SelectDuplicated,
    ]

    @classmethod
    def get_invalid_missing(cls, instance):
        invalid = list()
        for node in instance.data["requireAvalonUUID"]:
            if get_id_status(node) == Identifier.Untracked:
                invalid.append(node)

        return invalid

    @classmethod
    def get_invalid_duplicated(cls, instance):
        invalid = list()
        for node in instance.data["requireAvalonUUID"]:
            if get_id_status(node) == Identifier.Duplicated:
                invalid.append(node)

        return invalid

    def process(self, instance):
        missing = self.get_invalid_missing(instance)
        duplicated = self.get_invalid_duplicated(instance)

        if missing:
            self.log.error("Found node that has no ID assigned.")

        if duplicated:
            self.log.error("Found node that has assigned with duplicated ID.")

        if missing or duplicated:
            raise Exception("Found invalid nodes, require upstream to fix.")