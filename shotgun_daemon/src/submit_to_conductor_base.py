import json
import os
import re

import boto3
import shotgun_api3
import conductor.lib


class SubmitToConductorSGDaemonPlugin(object):
    
    # All these variables should be modified to work in your setup
    SERVER = os.environ['SHOTGUN_SERVER']
    SCRIPT_NAME = os.environ['SHOTGUN_SCRIPT_NAME']
    SCRIPT_KEY = os.environ['SHOTGUN_SCRIPT_KEY']
    
    REGISTER_PUBLISH_SCRIPT_PATH = "/usr/local/shotgun/support_files/register_publish.py"
    POST_RENDER_SCRIPT_PATH = "/usr/local/shotgun/support_files/post_render_script.py"
    S3_BUCKET = os.environ['AWS_PROJECT_BUCKET']
    TARGET_INSTANCE = '2 core, 13GB Mem'
    
    EVENT = {"Shotgun_PublishedFile_New": None}    
    
    def __init__(self):
        
        self.sg = None
        self.logger = None
        self.event_id = None
        self.event_entity = None
        
        self.s3_dest_path = None
        self.file_pattern = None
        self.render_extension = "exr"        
        
    def copy_from_s3(self, file_path):
        '''
        Copies file_path from an S3 bucket to local storage, using the same path.
        
        :param file_path: The path on S3. A sequence using '%[0-9]d' notation is accepted.
        :type file_path: str
        
        :returns: The file paths on the local storage
        :rtype: list of str
        '''
        
        self.logger.debug("Copy from S3 {}".format(file_path))
        
        local_file_paths = []
                
        # Deal with file sequences
        match = re.search('%0[\d]d', file_path)
        
        if match:
            self.logger.debug("Querying sequence")
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(self.S3_BUCKET)
            prefix = file_path.split(match.group())[0]

            for file_obj in bucket.objects.filter(Prefix=prefix[1:]):
                local_file_paths.extend(self.copy_from_s3("/{}".format(file_obj.key)))
                
        # Don't download if the file already exists. The check is only being peformed based on the
        # filename. A more rigourous check is suggested.
        elif os.path.exists(file_path):
            filesize = os.path.getsize(file_path)
            self.logger.info("File {} exists ({}). Skipping".format(file_path, filesize))
            local_file_paths = [file_path]
            
        else:
        
            self.logger.info("Downloading {}".format(file_path))
            
            parent_dir = os.path.dirname(file_path)
            
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            
            s3 = boto3.client('s3')
            
            # Strip out the leading forward-slash
            s3.download_file(self.S3_BUCKET, file_path[1:], file_path)
            
            local_file_paths = [file_path]
        
        return local_file_paths
    
    def submit_to_conductor(self, start_frame, end_frame):
        '''
        Submit the render job to Conductor
        
        :param start_frame: The starting frame to render
        :type start_frame: int
        
        :param end_frame: The last frame to render
        :type end_frame: int       
        '''
        
        # Dump the data needed to publish the render into a json file to be uploaded
        self.dump_render_publish_data(self.event_entity)
        
        # Copy the scene file from cloud storage
        file_path = self.event_entity['path']['local_path_linux']
        self.copy_from_s3(file_path)
        
        self.download_dependencies()

        conductor_job = self.build_conductor_job(start_frame, end_frame)
        conductor_job.submit_job()
    
    def dump_render_publish_data(self, src_publish_file):
        '''
        Dump all the data needed to publish the render images once they've completed into a file
        that will be sent to Conductor
        
        :param src_publish_file: The scene file used for the render
        :type src_publish_file: dict (PublishedFile entity) 
        '''
        
        published_file_data = {"code": "{}_render".format(src_publish_file['code']),
                               'project': src_publish_file['project'],
                               'published_file_type': self.get_image_published_file_type(),
                               'path': {'local_path': self.file_pattern},
                               'downstream_published_files': [src_publish_file],
                               'created_by': src_publish_file['created_by'],
                               'task': src_publish_file['task'],
                               'entity': src_publish_file['entity'],
                               }
        
        with open("/tmp/published_file.json", 'w') as fh:
            json.dump(published_file_data, fh)
            
    def get_image_published_file_type(self):
        '''
        Get the Image PublishedFileType for the appropriate Project
        
        :return: The Image PublishedFileType for the project
        :rtype: dict (PublishedFileType entity)        
        '''

        published_file_type = self.sg.find_one("PublishedFileType",
                                               filters=[ [ 'code', 'is', "Image" ]]
                                              )
        
        if not published_file_type:
            raise Exception("Unable to find an 'Image' PublishedFileType for the project {}".format(self.event_entity['project']))
            
        return published_file_type            
            
    def get_dependency_entities(self, published_files):
        '''
        Recursively get all the dependencies entities for the given dependencies
        
        :param published_files: the list of published_files to search for dependents
        :type published_files: list of dict (PublishedFile entities)
        
        :return: All the dependencies of the given published_files
        :rtype: list of dicts (PublishedFile entities)
        '''
        
        if not published_files:
            return []
        
        fields = ['id', 'path', 'downstream_published_files']
        
        self.logger.debug("Finding dependencies for {}".format(published_files))
        
        ids = [ int(published_file['id']) for published_file in published_files ]

        dependency_entities = self.sg.find( "PublishedFile",
                                           [[ 'id', 'in', ids ]],
                                           fields)
        
        # For each dependency, get its dependencies and build a flat list
        for dependency in dependency_entities:
            if dependency['downstream_published_files']:
                dependency_entities.extend(self.get_dependency_entities(dependency['downstream_published_files']))
                
        return dependency_entities
    
    def get_package_ids(self):
        '''
        Get the Conductor package ids for the render job. The packages tell Conductor what software
        to make available for a particular job. See the Conductor docs for more details.
        
        :return: The package ids
        :rtype: list of str
        '''
        
        return []
    
    def get_instance_type(self, target_instance):
        '''
        Get the required instance type necessary for the job
        
        :param target_instance: The instance-type description to search for. This must conform to 
                                one of the available instance types available on Conductor.
        :type target_instance: str
        
        :return: The instance type to use for the job
        :rtype: str        
        '''
        
        instances = conductor.lib.api_client.request_instance_types(as_dict=True)
        
        instance = instances.get(target_instance)
        
        if instance is None:
            raise Exception("Unable to find an instance matching '{}'".format(self.TARGET_INSTANCE))
        
        return instance['name']

    @classmethod
    def get_event(cls, event_id):
                
        sg = cls.get_sg_instance()
        event_fields = ['attribute_name', 'event_type', 'created_at', 'entity', 'project', 'meta', 'type', 'user', 'session_uuid', 'user.HumanUser.login']
        
        return sg.find_one( "EventLogEntry", 
                            [[ 'id', 'is', int(event_id) ]],
                            event_fields)
        
    @classmethod
    def get_sg_instance(cls):
        
        return shotgun_api3.Shotgun(cls.SERVER,
                                    cls.SCRIPT_NAME,
                                    cls.SCRIPT_KEY)           
        
    @classmethod
    def registerCallbacks(cls, reg):
        """
        Register our callbacks.
        :param reg: A Registrar instance provided by the event loop handler.
        """

        reg.registerCallback(
            cls.SCRIPT_NAME,
            cls.SCRIPT_KEY,
            cls().main,
            cls.EVENT
        )
        reg.logger.debug("Registered callback")            
    