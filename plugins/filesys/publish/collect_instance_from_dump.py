
import os
import sys
import json
import pyblish.api


class CollectInstancesFromDump(pyblish.api.ContextPlugin):
    """Create instances from context/instance dump file

    Update context and create instances from a JSON format dump file which
    acquired from `sys.argv[1]`.

    """

    label = "Collect Instances From Dump"
    order = pyblish.api.CollectorOrder - 0.2

    def process(self, context):
        dump_path = sys.argv[1]
        dump_file = os.path.basename(dump_path)

        if not dump_file.endswith(".json"):
            raise Exception("Invalid file extension: %s" % dump_path)

        if dump_file.startswith(".instance."):
            self.parse_instance(context, dump_path)

        elif dump_file.startswith(".context."):
            self.parse_context(context, dump_path)

        else:
            raise Exception("Unknown type of file: %s" % dump_path)

    def parse_instance(self, context, dump_path):

        with open(dump_path, "r") as file:
            dump = json.load(file)
        context = self.parse_context(context, dump["contextDump"])

        instance = next(i for i in context if i.data["dumpId"] == dump["id"])
        children = instance.data["childInstances"]
        instance_to_keep = [instance] + children[:]

        for instance in list(context):
            if instance not in instance_to_keep:
                context.remove(instance)

    def parse_context(self, context, dump_path):

        with open(dump_path, "r") as file:
            context_dump = json.load(file)

            context.data.update({
                "user": context_dump["by"],
                "date": context_dump["date"],
                "currentMaking": context_dump["from"],
                "comment": context_dump["comment"],
            })

        instance_by_id = dict()

        for dump in context_dump["instances"]:
            with open(dump["dump"], "r") as file:
                dump.update(json.load(file))

                previous_id = dump.pop("id")
                child_ids = dump.pop("childInstances")
                version_num = dump.pop("version")

                instance = context.create_instance(dump["name"])
                instance_by_id[previous_id] = instance

                instance.data.update(dump)

                instance.data["versionPin"] = version_num
                instance.data["dumpId"] = previous_id
                instance.data["childIds"] = child_ids
                instance.data["childInstances"] = list()

        for instance in context:
            children = instance.data["childInstances"]
            for child_id in instance.data["childIds"]:
                children.append(instance_by_id[child_id])

        return context
