import os
import sys
import docker
import git

from io import StringIO

if sys.version_info[0] < 3:
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser


class ObjectFromDict(object):
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            self.__dict__[key] = value


def get_artifacts(project, logger):
    dist = project.expand_path("$dir_dist", "dist")
    artifacts = [os.path.join(dist, artifact) for artifact in list(os.walk(dist))[0][2]]

    if len(artifacts) != 1:
        raise Exception("Multiple artifacts found!")

    return artifacts[0]


def get_docker_image_name(project, logger):
    logger.info("comment search")
    docker_version = project.get_property("docker_version")
    tag_prefix = project.get_property("docker_tag_prefix") 
    git_commit_hash = project.get_property("git_commit_hash")
    #commit_hash = project.get_mandatory_property("commit_hash")
    logger.info("This is the git commit hash %s:",git_commit_hash)
    '''
	if commit_hash is not None:
        return "{0}/{1}:{2}".format(tag_prefix, project.name, commit_hash)
    else:
        return "{0}/{1}:{2}".format(tag_prefix, project.name, docker_version if docker_version else project.version)
    '''
    return "{0}/{1}:{2}".format(tag_prefix, project.name, docker_version if docker_version else project.version)


def get_docker_client():
    if "DOCKER_API_VERSION" in os.environ:
        return docker.from_env(version=os.environ["DOCKER_API_VERSION"])
    else:
        return docker.from_env()


def read_config_dict(path):
    parser = ConfigParser()
    parser.optionxform = str

    with open(path) as config_file:
        parser.read_file(StringIO("[DEFAULT]\n" + config_file.read()))

    if parser.sections():
        raise Exception("Configuration file {0} contains multiple sections.".format(path))

    return dict(parser.items("DEFAULT"))

def get_docker_image_by_commit(project,logger):
    tag_prefix = project.get_property("docker_tag_prefix")
    commit_hash = get_git_commit_id()
    logger.info("docker_image_by_commit_name %s","{0}/{1}:{2}".format(tag_prefix, project.name,commit_hash))
    return "{0}/{1}:{2}".format(tag_prefix, project.name,commit_hash)

def get_git_commit_id():
    repo = git.Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    return repo.git.rev_parse(sha, short=6)