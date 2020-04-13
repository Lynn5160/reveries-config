
import os
import pyblish.api
import avalon.api


def get_render_attr(attr, layer):
    from reveries.maya import lib

    return lib.query_by_renderlayer("defaultRenderGlobals",
                                    attr,
                                    layer)


class CollectRenderlayers(pyblish.api.ContextPlugin):
    """Create instances by active render layers

    Whenever a renderlayer has multiple renderable cameras then each
    camera will get its own instance. As such, the amount of instances
    will be "renderable cameras (in layer) x layers".

    """

    order = pyblish.api.CollectorOrder - 0.299
    hosts = ["maya"]
    label = "Render Layers"

    targets = ["deadline"]

    def process(self, context):
        from maya import cmds
        from reveries.maya import lib, utils

        asset = avalon.api.Session["AVALON_ASSET"]
        filepath = context.data["currentMaking"].replace("\\", "/")

        # Get render globals node
        try:
            render_globals = cmds.ls("renderglobalsDefault")[0]
        except IndexError:
            self.log.info("Skipping renderlayer collection, no "
                          "renderGlobalsDefault found..")
            return

        base = {
            "publish": True,
            "time": avalon.api.time(),
            "author": context.data["user"],
            "asset": asset,

            "family": "reveries.renderlayer",
            "families": [
                "reveries.renderlayer",
            ],
            # Add source to allow tracing back to the scene from
            # which was submitted originally
            "source": filepath,
        }

        # Get all valid renderlayers
        # This is how Maya populates the renderlayer display
        rlm_attribute = "renderLayerManager.renderLayerId"
        connected_layers = cmds.listConnections(rlm_attribute) or []
        valid_layers = set(connected_layers)

        # Context data
        workspace = context.data["workspaceDir"]
        outputdir = os.path.join(workspace, "renders").replace("\\", "/")
        context.data["outputDir"] = outputdir
        # Are there other renderlayer than defaultRenderLayer ?
        context.data["hasRenderLayers"] = len(valid_layers) > 1
        # Using Render Setup system ?
        context.data["usingRenderSetup"] = lib.is_using_renderSetup()

        # Get all renderable renderlayers (not referenced)
        renderlayers = sorted(lib.ls_renderable_layers(),
                              key=lambda l:  # By renderlayer displayOrder
                              cmds.getAttr("%s.displayOrder" % l))

        # Create instance by renderlayers
        for layer in renderlayers:

            # Check if layer is in valid (linked) layers
            if layer not in valid_layers:
                self.log.warning("%s is invalid, skipping" % layer)
                continue

            self.log.debug("Creating instance for renderlayer: %s" % layer)

            renderer = get_render_attr("currentRenderer", layer)
            name_preview = utils.compose_render_filename(layer)
            ext = os.path.splitext(name_preview)[-1]

            # Get layer specific settings, might be overrides
            data = {
                "renderlayer": layer,
                "startFrame": get_render_attr("startFrame", layer),
                "endFrame": get_render_attr("endFrame", layer),
                "step": get_render_attr("byFrameStep", layer),
                "renderer": renderer,
                "resolution": utils.get_render_resolution(layer),
                "fileNamePrefix": utils.get_render_filename_prefix(layer),
                "fileExt": ext,
            }
            overrides = self.parse_render_globals(layer, render_globals)
            data.update(**overrides)
            data.update(base)

            members = self.colllect_renderlayer_members(layer)
            if not members:
                self.log.warning("%s has no member." % layer)

            layername = lib.pretty_layer_name(layer)

            render_cams = lib.ls_renderable_cameras(layer)
            if not render_cams:
                self.log.warning("No renderable camera in %s, skipping.."
                                 "" % layer)

            # Keep track of the amount of all renderable cameras in the
            # layer so we can use this information elsewhere, however note
            # that we split instances per camera below as `data["camera"]`
            data["cameras"] = render_cams

            for camera in render_cams:

                # Define nice label
                label = "{0} ({1})".format(layername, data["asset"])
                if len(render_cams) > 1:
                    # If more than one camera, include camera name in label
                    cam_name = cmds.ls(cmds.listRelatives(camera,
                                                          parent=True,
                                                          fullPath=True))[0]
                    label += " - {0}".format(cam_name)

                    # Prefix the camera after the layername
                    nice_cam = cam_name.replace(":", "_").replace("|", "_")
                    subset = "{0}_{1}".format(layername, nice_cam)
                    self.log.info(subset)
                else:
                    subset = layername

                # Always end with start frame and end frame in label
                label += "  [{0}-{1}]".format(int(data["startFrame"]),
                                              int(data["endFrame"]))

                data["label"] = label
                data["subset"] = subset
                data["subsetGroup"] = "Renders"
                data["camera"] = camera

                data["dependencies"] = dict()
                data["futureDependencies"] = dict()

                data["category"] = "[{renderer}] {layer}".format(
                    renderer=data["renderer"], layer=layername)

                instance = context.create_instance(data["subset"])
                instance.data.update(data)
                instance[:] += members

    def parse_render_globals(self, layer, render_globals):
        from reveries.maya import lib

        overrides = dict()

        attributes = [
            "deadlinePriority",
            "deadlinePool",
            "deadlineFramesPerTask",
            "deadlineSuspendJob",
        ]

        for attr in attributes:
            value = lib.query_by_renderlayer(render_globals, attr, layer)
            overrides[attr] = value

        return overrides

    def colllect_renderlayer_members(self, name):
        """Return renerlayer members in short name

        This method is implemented with Maya API 1.0.

        (NOTE)
        `editRenderLayerMembers` can only return either full path or just
        node name. And using `listConnections` to list out the connection
        between renerlayer's `renderInfo` and node's `renderLayerInfo` to
        find members, doesn't work with defaultRenderLayer.

        """
        import maya.OpenMaya as om_v1
        import maya.OpenMayaRender as omrender_v1

        members = set()

        mobj = omrender_v1.MFnRenderLayer.findLayerByName(name)
        layer = omrender_v1.MFnRenderLayer(mobj)

        marray = om_v1.MObjectArray()
        layer.listMembers(marray)

        for index in range(marray.length()):
            mobj = marray[index]
            # Assume all member `hasFn(om_v1.MFn.kDagNode)`
            node = om_v1.MFnDagNode(mobj)
            members.add(node.partialPathName())

        return list(members)
