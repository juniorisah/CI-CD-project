import os
import subprocess
import shutil
import docker
import docker.errors
import sys

from .util import ObjectFromDict, get_docker_image_name, get_artifacts, get_docker_client, read_config_dict, get_docker_image_by_commit,get_git_commit_id

from io import StringIO
from pybuilder.core import task, depends
from pybuilder.utils import assert_can_execute
from jinja2 import Template
from twine.commands import upload


if sys.version_info[0] < 3:
    from ConfigParser import ConfigParser
else:
    from configparser import ConfigParser


__all__ = ["docker_package", "docker_publish", "docker_tags", "kubernetes_deploy", "twine_upload"]


@task(description="Builds a Docker image containing the build.")
@depends("publish")
def docker_package(project, logger):
    client = get_docker_client()
    context_path = project.expand_path("$docker_context")
    docker_entry = project.get_property("docker_entry")
    docker_template = open(project.expand_path("$dir_source_main_docker/Dockerfile")).read()
    image_name = get_docker_image_name(project, logger)
    
    # Copy docker/ files to context
    if os.path.exists(context_path):
        shutil.rmtree(context_path)

    shutil.copytree(project.expand_path("$dir_source_main_docker"), context_path)

    # Copy artifact to context
    artifact = get_artifacts(project, logger)
    logger.info("Copying artifact %s to context.", artifact)
    shutil.copyfile(artifact, os.path.join(context_path, os.path.basename(artifact)))

    logger.info("Generating Dockerfile from template.")

    # Create Dockerfile in context
    template = Template(docker_template)
    with open(os.path.join(context_path, "Dockerfile"), "w") as f:
        docker_file = template.render(package_name=os.path.basename(artifact), docker_entry=docker_entry)
        f.write(docker_file)
        logger.debug("Docker file contents: %s", docker_file)

    logger.info("Creating Docker image '%s'", image_name)
    try:
        image, lines = client.images.build(path=context_path, tag=image_name)

        for decoded_line in lines:
            logger.debug("Docker Build: %s", decoded_line)
    except docker.errors.BuildError as error:
        logger.error("Docker build failed with error %s", error.msg)
        for decoded_line in error.build_log:
            logger.debug("Docker Build: %s", decoded_line)
        raise


@task(description="Publishes the built docker image to a remote repository.")
@depends("docker_package")
def docker_publish(project, logger):
    client = get_docker_client()
    image_name = get_docker_image_name(project, logger)
    commit_hash = project.get_property("git_commit_hash");
    logger.info("Checking if my version is being up %s",commit_hash)
    logger.info("Pushing Docker image %s to remote repository", image_name)

    for line in client.images.push(image_name, stream=True, decode=True):
        logger.debug("Docker Push: %s", line)

        if "error" in line:
            raise docker.errors.APIError(line["error"])

@task(description="Tags the docker images with commit id")
def docker_tags(project, logger):
    client = get_docker_client()
    image_name = get_docker_image_name(project, logger)
    commit_hash = get_git_commit_id()
    logger.info("Pyhton API Commit hash %s", commit_hash)
    logger.info("image_name %s and commit hash %s", image_name,commit_hash)
    try:
        image = client.images.get(image_name)
        logger.info("Getting the image %s",image)
        image.tag(image_name,tag=commit_hash,force=True)
        logger.info("Tagging the image")
        for line in client.images.push(image_name, tag=commit_hash,stream=True, decode=True):
            logger.debug("Docker Push with the new tag: %s", line)
            if "error" in line:
                raise docker.errors.APIError(line["error"])
    except docker.errors.APIError as error:
        logger.error("Docker tag failed with error %s", error.msg)
        raise


def kubernetes_deploy_config(config_name, config_path):
    parser = ConfigParser()
    parser.optionxform = str

    command = ["kubectl", "create", "configmap", config_name]

    with open(config_path) as config_file:
        parser.read_file(StringIO("[DEFAULT]\n" + config_file.read()))

    if parser.sections():
        raise Exception("Configuration file {0} contains multiple sections.".format(config_path))

    for key, value in parser.items("DEFAULT"):
        command += ["--from-literal={0}={1}".format(key, value)]

    subprocess.run(["kubectl", "delete", "configmap", config_name], check=False)
    subprocess.run(command, stdout=subprocess.PIPE, check=True)


@task(description="Deploys objects to Kubernetes cluster.")
def kubernetes_deploy(project, logger):
    logger.info("Deploying the artifact to Kubernetes")
    environment = project.get_mandatory_property("deployment_environment")
    user_config = project.get_property("deployment_user_config", "config.ini")
    assert_can_execute(["kubectl"], prerequisite="kubectl", caller="pybuilder-cdo")

    kube_namespace = project.expand(project.get_mandatory_property("kubernetes_namespace"))
    kube_services = project.get_property("kubernetes_services")
    kube_deployments = project.get_property("kubernetes_deployments")
    kube_configs = project.get_property("kubernetes_config_maps")

    # Create any necessary config maps
    if kube_configs:
        for name, path in kube_configs.items():
            split_name = os.path.splitext(path)
            name_with_env = "{0}_{1}{2}".format(split_name[0], environment, split_name[1])
            kubernetes_deploy_config(name, project.expand_path("src/main/resources/{0}".format(name_with_env)))

    # Read user configuration values
    base_values = read_config_dict(project.expand_path("src/main/kubernetes/{0}".format(user_config)))
    split_name = os.path.splitext(user_config)
    name_with_env = "{0}_{1}{2}".format(split_name[0], environment, split_name[1])
    env_values = read_config_dict(project.expand_path("src/main/kubernetes/{0}".format(name_with_env)))
    user_values = {}
    user_values.update(base_values)
    user_values.update(env_values)
    user_values = ObjectFromDict(user_values)

    # Values supplied to templates within "project" variable
    project_values = {
        "name": project.name,
        "version": project.version,
        "namespace": kube_namespace,
        "image_name": get_docker_image_by_commit(project, logger)
    }

    # Create services
    if kube_services:
        os.makedirs(project.expand_path("$dir_target/kubernetes/services/"), exist_ok=True)

        for name, path in kube_services.items():
            service_path = project.expand_path("src/main/kubernetes/" + path)
            with open(service_path) as template_stream:
                service_template = Template(template_stream.read())

            rendered = service_template.render(project=project_values, user=user_values)
            with open(project.expand_path("$dir_target/kubernetes/services/" + path), 'w') as output_stream:
                output_stream.write(rendered)

            subprocess.run(["kubectl", "apply", "-f", project.expand_path("$dir_target/kubernetes/services/" + path)],
                           check=True)

    # Create deployments
    if kube_deployments:
        os.makedirs(project.expand_path("$dir_target/kubernetes/deployments/"), exist_ok=True)

        for name, path in kube_deployments.items():
            deployment_path = project.expand_path("src/main/kubernetes/" + path)
            with open(deployment_path) as template_stream:
                deployment_template = Template(template_stream.read())

            rendered = deployment_template.render(project=project_values, user=user_values)
            with open(project.expand_path("$dir_target/kubernetes/deployments/" + path), 'w') as output_stream:
                output_stream.write(rendered)

            subprocess.run(["kubectl", "delete", "deployment", name], check=False)
            subprocess.run(["kubectl", "create", "-f", project.expand_path("$dir_target/kubernetes/deployments/" + path)], check=True)


@task(description="Uploads the published artifact to the specified PyPI repository.")
@depends("publish")
def twine_upload(project, logger):
    repo_key = project.get_property("twine_repo_key", "DockerCentral")

    artifact = get_artifacts(project, logger)
    logger.info("Uploading package %s to %s", artifact, repo_key)
    upload.main(["-r", repo_key, artifact])
