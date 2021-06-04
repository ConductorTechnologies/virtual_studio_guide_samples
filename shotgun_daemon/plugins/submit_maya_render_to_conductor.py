import datetime
import os
import sys

import conductor.__beta__.job.maya

import submit_to_conductor_base

    
class SubmitMayaToConductorPlugin(submit_to_conductor_base.SubmitToConductorSGDaemonPlugin):
    '''
    Shotgun daemon plugin to submit a Maya render whenever a lighting sceme is published    
    '''

    def main(self, sg, logger, event, args=None):
        
        self.sg = sg
        self.logger = logger
        
        published_file_fields = [ 'code',
                                  'created_by',
                                  'entity', 
                                  'id',                                  
                                  'name',
                                  'path', 
                                  'project',
                                  'sg_category',
                                  'task', 
                                  'downstream_published_files',                               
                                  'created_by.HumanUser.login', 
                                  'entity.Shot.sg_cut_in', 
                                  'entity.Shot.sg_cut_out',
                                  'published_file_type.PublishedFileType.code',
                                  'task.Task.step.Step.code',]
        
        logger.debug("Processing event {}: {}".format(event['id'], event))
        
        self.event_entity = self.sg.find_one( event['entity']['type'],
                                              [[ 'id', 'is', int(event['entity']['id']) ]],
                                              published_file_fields)
                
        # Get the extension, stripping out the leading period
        file_path = self.event_entity['path']['local_path_linux'] 
        extension = os.path.splitext(file_path)[-1][1:]

        # Maya Lighting files - submit to conductor
        if ( self.event_entity['published_file_type.PublishedFileType.code'] == 'Maya Scene' and
             extension in ("ma", "mb") and
             self.event_entity['task.Task.step.Step.code'] == 'Light'):            
        
            start_frame = self.event_entity['entity.Shot.sg_cut_in']
            end_frame = self.event_entity['entity.Shot.sg_cut_out']
            
            # Ensure that we know the frame range for this Shot
            if start_frame is None or end_frame is None:
                raise Exception("Unable to process {}, the Shot has no cut info ({})".format(self.event_entity['name'], self.event_entity))

            # The job title - as it would appear in Conductor
            self.job_title = self.event_entity['code']         
            
            self.s3_dest_path = "projects/renders/{}_{}_{}".format(self.job_title, self.event_entity['id'], datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            self.file_pattern = self.get_file_pattern()
                                
            logger.info("Submitting published file: {}".format(self.event_entity.keys()))            
            self.submit_to_conductor(start_frame, end_frame)      
        
        else:
            logger.info("Skipping. Extension is {}".format(extension))
            
    def get_file_pattern(self):
        '''
        Get the complete file pattern for render sequence
        
        :return: File patter for the render sequence
        :rtype: str
        '''
        
        # This is left as a simple and generic method to generate the paths where the renders will 
        # be published to.
        #
        # An SGTk tempalte could be used here but there's significant overhead and complications
        # to using it within the daemon when the file-system is not directly available.
        
        return "/{}/{}.%05d.{}".format(self.s3_dest_path, self.event_entity['code'], self.render_extension)

    def download_dependencies(self):
        '''
        Download the dependencies required to submit the job to Conductor
        '''
                
        file_path = self.event_entity['path']['local_path_linux']
        self.copy_from_s3(file_path)
        
        # Gather all the dependencies and copy them from cloud storage
        dependency_entities = self.get_dependency_entities(self.event_entity['downstream_published_files'])        
        self.logger.info("Found {} dependencies".format(len(dependency_entities)))

        for dependency in dependency_entities:
            self.copy_from_s3(dependency['path']['local_path_linux']) 
    
    def build_conductor_job(self, start_frame, end_frame):
        '''
        Construct a Conductor job object that contains all the parameters to
        submit the job
        
        :param start_frame: The starting frame to render
        :type start_frame: int
        
        :param end_frame: The last frame to render
        :type 
        '''                    

        # This is a convenience class that's included with the Conductor Client Tools. It's strongly
        # recommended to re-implement a similar class in your environment or use conductor.lib.api_client
        # directly. 
        conductor_job = conductor.__beta__.job.maya.MayaRenderJob(self.event_entity['path']['local_path'])
        
        # This will probably changed per your setup. It could be included as metadata as part of the publish
        conductor_job.render_layer = "defaultRenderLayer"
        
        # The path where Conductor expects the files to be rendered to
        conductor_job.output_path = os.path.dirname(self.file_pattern)
        
        # Don't rely on an uploader daemon
        conductor_job.local_upload = True
        
        # Set the start/end frames and stepping
        conductor_job.start_frame = start_frame
        conductor_job.end_frame = end_frame
        conductor_job.frame_step = 1 
        
        # Set the job title as it will appear in the Conductor dashboard
        conductor_job.job_title = "[SG Daemon] - {}".format(self.job_title)
        
        # Use the user that published the scene file
        conductor_job.user = self.event_entity['created_by.HumanUser.login']
        
        # Get the Conductor package ids for the job
        conductor_job.software_package_ids = self.get_package_ids()
        
        # Set the instance type for the Conductor job
        conductor_job.instance_type = self.get_instance_type(self.TARGET_INSTANCE)
        
        # Ensure the environment has all the information for scripts that will run on the instances
        conductor_job.environment = { 'CONDUCTOR_OUTPUT_PATH': conductor_job.output_path,
                                      'CONDUCTOR_S3_BUCKET': self.S3_BUCKET,
                                      'CONDUCTOR_S3_PATH': self.file_pattern[1:],
                                      'PYTHONPATH': '/shotgun',
                                      'MAYA_ENABLE_LEGACY_RENDER_LAYERS': 1 }
        
        # Ensure that all the dependencies get uploaded
        dependencies = self.get_dependency_entities([self.event_entity]) 
        conductor_job.upload_paths.extend( [dep['path']['local_path_linux'] for dep in dependencies ])       
        
        # Ensure that post/pre render scripts get uploaded
        conductor_job.upload_paths.append(self.POST_RENDER_SCRIPT_PATH)
        conductor_job.upload_paths.append(self.REGISTER_PUBLISH_SCRIPT_PATH)
        conductor_job.upload_paths.append("/tmp/published_file.json")

        conductor_job.post_task_cmd = "python {}".format(self.POST_RENDER_SCRIPT_PATH)
        conductor_job.post_job_cmd = "python {}".format(self.REGISTER_PUBLISH_SCRIPT_PATH)

        conductor_job._get_environment()
        
        return conductor_job

    def get_package_ids(self):
        '''
        Get the Conductor package ids for the render job. The packages tell Conductor what software
        to make available for a particular job. See the Conductor docs for more details.
        
        :return: The package ids
        :rtype: list of str
        '''
        
        package_ids = []
        
        # We're hard-coding the Conductor job to use Maya 2018 Update 1 with VRay 3.60.04
        # This can stay hard-coded, be queried from a CustomEntity in Shotgun or perhaps
        # be in the metadata of the scene file publish        

        host_package = conductor.lib.package_utils.get_host_package("maya-io", "Autodesk Maya 2018.1", strict=False)
        package_ids.append(host_package['package'])
        package_ids.append(host_package['v-ray-maya']['3.60.04'])     

        return package_ids
 
 
def registerCallbacks(reg):
    SubmitMayaToConductorPlugin.registerCallbacks(reg)


    
if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        event_id = sys.argv[1]

        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('sg_event_handler')
        logger.debug("Initialized logger")
        logger.setLevel(logging.DEBUG)
        
        sg = SubmitMayaToConductorPlugin.get_sg_instance()
        
        event = SubmitMayaToConductorPlugin.get_event(event_id)
        eventHandler = SubmitMayaToConductorPlugin()
        eventHandler.main(sg, logger, event)
        
    else:
        print "No event id given, exiting" 
    
