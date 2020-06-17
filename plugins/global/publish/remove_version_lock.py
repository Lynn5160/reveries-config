
import os
import pyblish.api


class RemoveVersionLock(pyblish.api.ContextPlugin):
    """Unlock version directory after subsets have been integrated
    """

    label = "Remove Lock"
    order = pyblish.api.IntegratorOrder + 0.1

    def process(self, context):

        for instance in context:
            if not instance.data.get("publish", True):
                continue

            if instance.data.get("_progressivePublishing", False):
                continue

            lockfile = instance.data["_versionlock"]
            os.remove(lockfile)
            # (TODO) If publish process stopped by user, version dir will
            #        remain locked since this plugin may not be executed.
            #        To solve this, may require pyblish/pyblish-base#352
            #        be implemented.
