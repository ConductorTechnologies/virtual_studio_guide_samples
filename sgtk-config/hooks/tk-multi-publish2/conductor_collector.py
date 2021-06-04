import os
import sys

import maya.cmds as cmds
import sgtk

# Set this to the path for Conductor Client Tools here
CONDUCTOR_CLIENT_TOOLS_PATH = '/opt/conductor'

sys.path.append(CONDUCTOR_CLIENT_TOOLS_PATH)
sys.path.append(os.path.join(CONDUCTOR_CLIENT_TOOLS_PATH, "python", "lib", "python2.7", "site-packages") 

import conductor.lib
import conductor.lib.maya_utils

HookBaseClass = sgtk.get_hook_baseclass()


class MayaConductorSessionCollector(HookBaseClass):
    """
    Inherits from MayaSessionCollector. Leverages Conductor's scene dependency scraping.
    
    *WARNING*: The base class (MayaSessionCollector) searches for Alembic caches inside the current
    project's cache folder. Conductor's scraping searches the scene for alembic references. It's 
    possible that the same alembic can be found twice and will appear in the publisher app twice.
    """
    
    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Maya and parents a subtree of
        items under the parent_item passed in.
        
        Leverages Conductor's dependency scraping.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """
        
        super(MayaConductorSessionCollector, self).process_current_session(settings, parent_item)

        
        # Get the session item found in the base class so that we can create a proper publishing
        # tree
        session_item = None
        
        for child_item in parent_item._children:
            if child_item._type_display == "Maya Session":
                session_item = child_item
                
        if session_item is None:
            raise Exception("Unable to find the MayaSession Publish Item")

        resources = conductor.lib.common.load_resources_file()
        dependency_attrs = resources.get("maya_dependency_attrs") or {}
         
        deps = conductor.lib.maya_utils.collect_dependencies(dependency_attrs)
        scene_path = cmds.file(query=True, sn=True)
         
        for dep in deps:
            if dep and dep != scene_path:
                super(MayaConductorSessionCollector, self)._collect_file(session_item, dep)
