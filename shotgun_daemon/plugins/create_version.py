import os
import subprocess
import sys

import boto3

import shotgun_api3

import submit_to_conductor_base

    
class CreateVersionPlugin(submit_to_conductor_base.SubmitToConductorSGDaemonPlugin):
    '''
    Creates a new Shotgun Version and media for review purposes.
    
    Although this plugin doesn't submit anything to Conductor we inherit from 
    SubmitToConductorSGDaemonPlugin for convenience
    '''
    
    EVENT = {"Shotgun_PublishedFile_New": None}

    def main(self, sg, logger, event, args=None):
        
        self.sg = sg
        self.logger = logger
        
        published_file_fields = [ 'code', 
                                  'created_by',
                                  'id',
                                  'name',
                                  'entity',
                                  'path', 
                                  'project',
                                  'task',
                                  'upstream_published_files',                               
                                  'created_by.HumanUser.login', 
                                  'entity.Shot.sg_cut_in', 
                                  'entity.Shot.sg_cut_out',
                                  'published_file_type.PublishedFileType.code',
                                  'task.Task.step.Step.code',]
        
        logger.info("Processing event {}: {}".format(event['id'], event))
        
        self.event_entity = self.sg.find_one( event['entity']['type'],
                                              [[ 'id', 'is', int(event['entity']['id']) ]],
                                              published_file_fields)
        
        logger.debug("Event entity: {}".format(self.event_entity))
        
        file_path = self.event_entity['path']['local_path_linux']
        extension = os.path.splitext(file_path)[-1][1:]
        
        # Publish any rendered images
        if ( self.event_entity['published_file_type.PublishedFileType.code'] == 'Image' and 
             extension == "exr"):
            
            self.copy_from_s3(file_path)
            self.create_mp4(file_path)
            self.create_version()
             
        else:
            logger.info("Skipping. Extension is {}".format(extension))
            
    def create_mp4(self, input_file_seq):
        '''
        Generate an MP4 from the given file sequence
        
        :param input_file_seq: The path to the file sequence. Must use FFMEG compatible sequence
                               notation.
        :type input_file_seq: 
        '''
        
        filename = os.path.basename(self.event_entity['path']['local_path'])
        basename = ".".join(filename.split(".")[0:-2])
        self.movie_output_path = "/tmp/{}.mp4".format(basename)
        
        cmd = [ "ffmpeg",
                "-y", # Force overwrite
                "-start_number", str(self.event_entity['entity.Shot.sg_cut_in']),                
                "-i",
                input_file_seq,
                "-c:v", "libx264",
                "-vf", "fps=24",
                self.movie_output_path]
        
        self.logger.debug("Executing '{}'".format(cmd))
        ps = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        
        if ps.returncode != 0:
            raise Exception("FFmpeg failed with a return code of {}".format(ps.returncode))
        
        if not os.path.exists(self.movie_output_path) or os.path.getsize(self.movie_output_path) == 0:
            raise Exception("FFmpeg failed to create {}".format(self.movie_output_path))

        self.logger.info("Created {} from {}".format(self.movie_output_path, input_file_seq))
            
    def create_version(self):
        '''
        Create a Shotgun Version and upload the generated mp4
        '''
        
        version_data = {'code':self.event_entity['code'],
                        'project': self.event_entity['project'],
                        'sg_status_list': 'rev',
                        'entity': self.event_entity['entity'],                    
                        'sg_task': self.event_entity['task'],
                        'user': self.event_entity['created_by'],
                        'sg_path_to_frames': self.event_entity['path']['local_path'],
                        'published_files': [self.event_entity]}

        new_version = self.sg.create("Version", data=version_data)
      
        self.sg.upload("Version", new_version['id'], self.movie_output_path, 'sg_uploaded_movie')

 
def registerCallbacks(reg):
    CreateVersionPlugin.registerCallbacks(reg)
    
if __name__ == "__main__":
    
    if len(sys.argv) > 1:
        event_id = sys.argv[1]

        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger('sg_event_handler')
        logger.debug("Initialized logger")
        logger.setLevel(logging.DEBUG)
        
        sg = CreateVersion.get_sg_instance()
        event = CreateVersion.get_event(event_id)
    
        eventHandler = CreateVersion()
        eventHandler.main(sg, logger, event)
        
    else:
        print "No event id given, exiting" 
    
